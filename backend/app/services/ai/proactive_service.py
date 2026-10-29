"""主动性服务：每日知识回顾与目标提醒

设计取舍：
- 每日回顾调用轻量模型，失败时退化为确定性模板，保证演示环境不会空窗。
- 目标提醒不调用模型，用模板生成，成本为零且文案稳定。
- 每条主动消息都可标记已读或忽略；扫描结果按 source_ref 去重。
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import ErrorCode
from app.core.response import APIError
from app.models.agent import AgentMemory, AgentProactiveMessage
from app.models.note import Note
from app.models.user import User
from app.schemas.agent import AgentProactiveScanResponse
from app.services.ai.chunking import html_to_text
from app.services.ai.provider import AIProviderError, get_chat_provider
from app.services.ai.usage import record_usage

logger = logging.getLogger(__name__)

_STALE_GOAL_COOLDOWN_DAYS = 7


def _local_now() -> datetime:
    """按配置时区取当前时间，Windows 缺少 tzdata 时退化为 UTC+8"""
    try:
        from zoneinfo import ZoneInfo

        zone = ZoneInfo(settings.AI_PROACTIVE_TIMEZONE)
    except Exception:  # tzdata 缺失或配置非法时退化
        zone = timezone(timedelta(hours=8))
    return datetime.now(zone).replace(tzinfo=None)


class ProactiveService:
    """每日回顾、目标提醒与消息管理"""

    async def daily_review(self, db: AsyncSession, user_id: int) -> bool:
        """生成今日知识回顾；当天已生成则跳过"""
        today = _local_now().replace(hour=0, minute=0, second=0, microsecond=0)
        existing = await db.execute(
            select(AgentProactiveMessage.id)
            .where(
                AgentProactiveMessage.user_id == user_id,
                AgentProactiveMessage.kind == "daily_review",
                AgentProactiveMessage.created_at >= today,
            )
            .limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            return False

        notes_result = await db.execute(
            select(Note)
            .where(Note.user_id == user_id)
            .order_by(Note.updated_at.desc())
            .limit(5)
        )
        notes = list(notes_result.scalars().all())
        goals_result = await db.execute(
            select(AgentMemory).where(
                AgentMemory.user_id == user_id, AgentMemory.memory_type == "goal"
            )
        )
        goals = list(goals_result.scalars().all())
        if not notes and not goals:
            return False

        content = await self._review_text(db, user_id, notes, goals)
        db.add(
            AgentProactiveMessage(
                user_id=user_id,
                kind="daily_review",
                title="今日知识回顾",
                content=content,
                source_ref=today.strftime("%Y-%m-%d"),
            )
        )
        await db.commit()
        return True

    async def scan_stale_goals(self, db: AsyncSession, user_id: int) -> AgentProactiveScanResponse:
        """扫描长期未推进的目标，生成提醒；同一目标 7 天内不重复"""
        cutoff = _local_now() - timedelta(days=settings.AI_STALE_GOAL_DAYS)
        result = await db.execute(
            select(AgentMemory)
            .where(
                AgentMemory.user_id == user_id,
                AgentMemory.memory_type == "goal",
                AgentMemory.importance >= 3,
                AgentMemory.created_at <= cutoff,
            )
            .order_by(AgentMemory.importance.desc(), AgentMemory.created_at.asc())
            .limit(5)
        )
        goals = list(result.scalars().all())
        created = 0
        skipped = 0
        cooldown = _local_now() - timedelta(days=_STALE_GOAL_COOLDOWN_DAYS)
        for goal in goals:
            source_ref = f"goal:{goal.id}"
            recent = await db.execute(
                select(AgentProactiveMessage.id)
                .where(
                    AgentProactiveMessage.user_id == user_id,
                    AgentProactiveMessage.source_ref == source_ref,
                    AgentProactiveMessage.created_at >= cooldown,
                )
                .limit(1)
            )
            if recent.scalar_one_or_none() is not None:
                skipped += 1
                continue

            days = max(settings.AI_STALE_GOAL_DAYS, (_local_now() - goal.created_at).days)
            db.add(
                AgentProactiveMessage(
                    user_id=user_id,
                    kind="stale_goal",
                    title="目标提醒",
                    content=(
                        f"你在 {goal.created_at.strftime('%Y-%m-%d')} 记下目标"
                        f"「{goal.content}」，已经过去 {days} 天。"
                        "今天要不要推进一小步？完成后可以告诉我，我帮你更新记忆。"
                    ),
                    source_ref=source_ref,
                )
            )
            created += 1
        await db.commit()
        return AgentProactiveScanResponse(created=created, skipped=skipped)

    async def scan(self, db: AsyncSession, user_id: int) -> AgentProactiveScanResponse:
        """手动触发一次完整扫描：目标提醒 + 今日回顾"""
        result = await self.scan_stale_goals(db, user_id)
        reviewed = await self.daily_review(db, user_id)
        return AgentProactiveScanResponse(
            created=result.created + (1 if reviewed else 0), skipped=result.skipped
        )

    async def list_messages(
        self,
        db: AsyncSession,
        user_id: int,
        status: str | None = None,
        limit: int = 20,
    ) -> list[AgentProactiveMessage]:
        """列出主动消息，未读优先、时间倒序"""
        query = select(AgentProactiveMessage).where(AgentProactiveMessage.user_id == user_id)
        if status:
            query = query.where(AgentProactiveMessage.status == status)
        else:
            # 忽略即从收件箱消失，但保留记录便于审计
            query = query.where(AgentProactiveMessage.status != "dismissed")
        result = await db.execute(
            query.order_by(
                case((AgentProactiveMessage.status == "unread", 0), else_=1),
                AgentProactiveMessage.created_at.desc(),
            ).limit(limit)
        )
        return list(result.scalars().all())

    async def mark_read(
        self, db: AsyncSession, user_id: int, message_id: int, status: str = "read"
    ) -> AgentProactiveMessage:
        """更新消息状态为已读或忽略"""
        message = await self._get(db, user_id, message_id)
        message.status = status
        await db.commit()
        await db.refresh(message)
        return message

    async def unread_count(self, db: AsyncSession, user_id: int) -> int:
        """未读主动消息数量"""
        result = await db.execute(
            select(func.count(AgentProactiveMessage.id)).where(
                AgentProactiveMessage.user_id == user_id,
                AgentProactiveMessage.status == "unread",
            )
        )
        return int(result.scalar() or 0)

    async def run_for_all_users(self, db: AsyncSession) -> int:
        """遍历有笔记的用户，生成今日回顾与目标提醒

        单用户失败不影响其他用户；每个用户独立提交。
        """
        if not settings.ai_configured or not settings.AI_PROACTIVE_ENABLED:
            return 0
        note_users = select(Note.user_id).distinct()
        memory_users = select(AgentMemory.user_id).distinct()
        result = await db.execute(
            select(User).where(User.id.in_(note_users.union(memory_users)))
        )
        users = list(result.scalars().all())
        generated = 0
        for user in users:
            try:
                reviewed = await self.daily_review(db, user.id)
                scanned = await self.scan_stale_goals(db, user.id)
                generated += (1 if reviewed else 0) + scanned.created
            except Exception:
                await db.rollback()
                logger.exception("主动消息生成失败 user_id=%s", user.id)
        return generated

    async def _review_text(
        self,
        db: AsyncSession,
        user_id: int,
        notes: list[Note],
        goals: list[AgentMemory],
    ) -> str:
        """调用轻量模型生成回顾；失败时使用模板"""
        note_lines = "\n".join(
            f"- 《{note.title}》：{html_to_text(note.content or '')[:160]}"
            for note in notes
        ) or "（最近没有更新笔记）"
        goal_lines = "\n".join(f"- {goal.content}" for goal in goals[:5]) or "（暂未记录目标）"
        prompt = (
            "请根据下面的资料，生成一段简短的「今日知识回顾」。\n"
            f"最近更新的笔记：\n{note_lines}\n\n"
            f"已记录的目标：\n{goal_lines}\n\n"
            "要求：简体中文，3-5 句；先回顾最近在学什么或写什么，"
            "再提醒一个最值得推进的目标；不要编造资料里没有的内容；"
            "不要使用 Markdown 标题。"
        )
        try:
            provider = get_chat_provider()
            result = await provider.chat(
                [{"role": "user", "content": prompt}],
                settings.AI_FAST_MODEL,
                temperature=0.4,
                max_tokens=400,
            )
            await record_usage(
                db, user_id, "proactive", settings.AI_FAST_MODEL, result.usage, result.latency_ms
            )
            content = (result.content or "").strip()
            if content:
                return content
        except AIProviderError as exc:
            logger.warning("今日回顾模型不可用，使用模板：%s", exc)
        return self._fallback_review(notes, goals)

    @staticmethod
    def _fallback_review(notes: list[Note], goals: list[AgentMemory]) -> str:
        """模型不可用时的确定性回顾文案"""
        if notes:
            titles = "、".join(f"《{note.title}》" for note in notes[:3])
            head = f"你最近更新了 {titles}，看起来在持续推进自己的知识整理。"
        else:
            head = "你最近还没有更新笔记，可以先记录一点今天学到的东西。"
        if goals:
            tail = f"别忘了你的目标「{goals[0].content}」，今天可以推进一小步。"
        else:
            tail = "如果正在推进某个目标，可以把它记成一条目标记忆，我会定期提醒你。"
        return f"{head}{tail}"

    async def _get(
        self, db: AsyncSession, user_id: int, message_id: int
    ) -> AgentProactiveMessage:
        """按归属加载主动消息"""
        result = await db.execute(
            select(AgentProactiveMessage).where(
                AgentProactiveMessage.id == message_id,
                AgentProactiveMessage.user_id == user_id,
            )
        )
        message = result.scalar_one_or_none()
        if message is None:
            raise APIError(ErrorCode.PROACTIVE_MESSAGE_NOT_FOUND, "主动消息不存在")
        return message
