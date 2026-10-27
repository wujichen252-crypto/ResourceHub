"""调用计量：统一写入 ai_usage_logs，供成本看板与配额限制使用"""

import logging
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai import AIUsageLog

logger = logging.getLogger(__name__)


async def record_usage(
    db: AsyncSession,
    user_id: int,
    scene: str,
    model: str | None,
    usage: dict[str, int] | None,
    latency_ms: int = 0,
    success: bool = True,
    error_code: str | None = None,
) -> None:
    """写入一条调用记录；失败不影响主流程"""
    usage = usage or {}
    entry = AIUsageLog(
        user_id=user_id,
        scene=scene,
        model=model,
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        total_tokens=usage.get("total_tokens", 0),
        latency_ms=latency_ms,
        success=success,
        error_code=error_code,
    )
    db.add(entry)
    try:
        await db.flush()
    except Exception:  # 计量失败不应中断用户请求
        logger.exception("写入 AI 调用计量失败")


async def today_tokens(db: AsyncSession, user_id: int) -> int:
    """统计用户当日已消耗 token，用于配额校验"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.coalesce(func.sum(AIUsageLog.total_tokens), 0)).where(
            AIUsageLog.user_id == user_id,
            AIUsageLog.created_at >= today,
        )
    )
    return int(result.scalar() or 0)


async def ensure_quota(db: AsyncSession, user_id: int) -> None:
    """配额不足时抛业务异常（由路由层转换为标准错误响应）"""
    from app.core.errors import ErrorCode
    from app.core.response import APIError

    used = await today_tokens(db, user_id)
    if settings.AI_DAILY_TOKEN_QUOTA > 0 and used >= settings.AI_DAILY_TOKEN_QUOTA:
        raise APIError(ErrorCode.AI_QUOTA_EXCEEDED, "今天的 AI 使用次数已用完，请明天再试")
