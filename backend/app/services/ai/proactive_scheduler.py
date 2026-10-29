"""主动消息定时调度

使用 lifespan 内的 asyncio 循环，不引入额外依赖：
- 每天 `AI_PROACTIVE_HOUR` 触发一次
- 单用户失败只记日志，不影响其他用户
- `ENV=test` 或未配置 AI 时不启动

注意：多 worker 部署会重复执行，需要改为独立调度进程或加数据库锁。
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.ai.proactive_service import ProactiveService

logger = logging.getLogger(__name__)


def _local_now() -> datetime:
    """按配置时区取当前时间，Windows 缺少 tzdata 时退化为 UTC+8"""
    try:
        from zoneinfo import ZoneInfo

        zone = ZoneInfo(settings.AI_PROACTIVE_TIMEZONE)
    except Exception:
        zone = timezone(timedelta(hours=8))
    return datetime.now(zone)


def _seconds_until_next_run() -> float:
    """计算距离下一次触发还有多少秒"""
    now = _local_now()
    target = now.replace(
        hour=min(23, max(0, settings.AI_PROACTIVE_HOUR)),
        minute=0,
        second=0,
        microsecond=0,
    )
    if target <= now:
        target += timedelta(days=1)
    return max(1.0, (target - now).total_seconds())


async def run_once() -> int:
    """执行一轮主动消息生成，返回生成条数"""
    async with SessionLocal() as db:
        try:
            return await ProactiveService().run_for_all_users(db)
        except Exception:
            await db.rollback()
            logger.exception("主动消息定时任务失败")
            return 0


async def scheduler_loop() -> None:
    """常驻协程：每天固定时刻触发一次"""
    if not settings.AI_PROACTIVE_ENABLED or not settings.ai_configured:
        logger.info("主动消息调度未启用")
        return
    logger.info("主动消息调度已启动，每天 %s 点执行", settings.AI_PROACTIVE_HOUR)
    while True:
        await asyncio.sleep(_seconds_until_next_run())
        generated = await run_once()
        logger.info("主动消息生成完成：%s 条", generated)
