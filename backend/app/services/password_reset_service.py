"""
密码重置服务

流程：
1. request_code：用户名 + 邮箱匹配 → 限流 → 生成 6 位验证码（只存哈希）→ 发邮件
2. confirm：常数时间比对验证码 → 改密 → 作废该用户全部未失效验证码

防枚举：账号不存在、邮箱未绑定、冷却中、达到日限，一律返回同一句文案；
只有 SMTP 未配置 / 发送失败才报错，因为那属于全局故障而非账号状态。
"""

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ErrorCode
from app.core.security import hash_password
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.schemas.auth import PasswordResetCodeRequest, PasswordResetConfirmRequest
from app.services.email_service import email_service

logger = logging.getLogger(__name__)

RESET_CODE_SENT_MESSAGE = "如果该账号存在且已绑定邮箱，验证码已发送，请注意查收"


class PasswordResetService:
    async def request_code(self, db: AsyncSession, data: PasswordResetCodeRequest) -> None:
        if not email_service.is_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": ErrorCode.EMAIL_NOT_CONFIGURED,
                    "message": "邮件服务未配置，暂时无法发送验证码",
                },
            )

        user = await self._find_user(db, data.username, data.email)
        if not user or not user.email:
            return

        now = datetime.now()
        latest = (
            await db.execute(
                select(PasswordResetToken)
                .where(PasswordResetToken.user_id == user.id)
                .order_by(PasswordResetToken.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if (
            latest
            and (now - latest.created_at).total_seconds()
            < settings.RESET_CODE_RESEND_COOLDOWN_SECONDS
        ):
            logger.info("密码重置验证码请求命中冷却 user_id=%s", user.id)
            return

        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = (
            await db.execute(
                select(func.count())
                .select_from(PasswordResetToken)
                .where(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.created_at >= day_start,
                )
            )
        ).scalar_one()
        if today_count >= settings.RESET_CODE_DAILY_LIMIT:
            logger.warning("密码重置验证码请求达到日限 user_id=%s", user.id)
            return

        # 旧码全部作废，保证任一时刻只有一个可用验证码
        await db.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=now)
        )

        code = f"{secrets.randbelow(1_000_000):06d}"
        db.add(
            PasswordResetToken(
                user_id=user.id,
                code_hash=self._hash_code(user.id, code),
                expires_at=now + timedelta(minutes=settings.RESET_CODE_TTL_MINUTES),
                created_at=now,
            )
        )
        await db.commit()

        try:
            # 等发送结果再响应：失败必须让用户看见；SMTP 故障通常是全局配置问题
            await email_service.send_password_reset_code(
                user.email, user.username, code, settings.RESET_CODE_TTL_MINUTES
            )
        except Exception as exc:
            logger.exception("密码重置验证码发送失败 user_id=%s", user.id)
            await db.execute(
                update(PasswordResetToken)
                .where(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.used_at.is_(None),
                )
                .values(used_at=datetime.now())
            )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": ErrorCode.EMAIL_SEND_FAILED,
                    "message": "验证码发送失败，请稍后再试",
                },
            ) from exc

    async def confirm(self, db: AsyncSession, data: PasswordResetConfirmRequest) -> None:
        user = await self._find_user(db, data.username, data.email)
        if not user:
            raise self._invalid_code()

        token = (
            await db.execute(
                select(PasswordResetToken)
                .where(
                    PasswordResetToken.user_id == user.id,
                    PasswordResetToken.used_at.is_(None),
                )
                .order_by(PasswordResetToken.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if not token:
            raise self._invalid_code()

        now = datetime.now()
        if token.expires_at <= now:
            token.used_at = now
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": ErrorCode.RESET_CODE_EXPIRED,
                    "message": "验证码已过期，请重新获取",
                },
            )

        if not hmac.compare_digest(token.code_hash, self._hash_code(user.id, data.code)):
            token.attempts += 1
            if token.attempts >= settings.RESET_CODE_MAX_ATTEMPTS:
                token.used_at = now
                await db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": ErrorCode.RESET_CODE_ATTEMPTS_EXCEEDED,
                        "message": "验证码错误次数过多，请重新获取",
                    },
                )
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": ErrorCode.RESET_CODE_INVALID,
                    "message": "验证码不正确",
                },
            )

        token.used_at = now
        user.password_hash = hash_password(data.new_password)
        await db.flush()
        await db.execute(
            update(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
            .values(used_at=now)
        )
        await db.commit()

    @staticmethod
    def _invalid_code() -> HTTPException:
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": ErrorCode.RESET_CODE_INVALID,
                "message": "验证码无效或已过期",
            },
        )

    async def _find_user(self, db: AsyncSession, username: str, email: str) -> User | None:
        result = await db.execute(
            select(User).where(
                User.username == username.strip(),
                func.lower(User.email) == email.strip().lower(),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _hash_code(user_id: int, code: str) -> str:
        # SECRET_KEY 作为 pepper：即使库被拖走，6 位数字也无法离线穷举
        return hmac.new(
            settings.SECRET_KEY.encode("utf-8"),
            f"{user_id}:{code}".encode("ascii"),
            hashlib.sha256,
        ).hexdigest()
