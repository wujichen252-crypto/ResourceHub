from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt import Prompt, PromptUsageLog


class PromptAnalyticsService:
    async def get_summary(self, db: AsyncSession, user_id: int) -> dict:
        # 总使用次数
        total_result = await db.execute(
            select(func.count()).select_from(PromptUsageLog).where(
                PromptUsageLog.user_id == user_id
            )
        )
        total_uses = total_result.scalar() or 0

        # TOP 10 最常用提示词
        top_query = (
            select(
                PromptUsageLog.prompt_id,
                Prompt.title,
                func.count().label("count"),
            )
            .join(Prompt, PromptUsageLog.prompt_id == Prompt.id)
            .where(PromptUsageLog.user_id == user_id)
            .group_by(PromptUsageLog.prompt_id, Prompt.title)
            .order_by(func.count().desc())
            .limit(10)
        )
        top_result = await db.execute(top_query)
        most_used = [
            {"prompt_id": row.prompt_id, "title": row.title, "count": row.count}
            for row in top_result
        ]

        # 近 30 天每日趋势
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        daily_query = (
            select(
                func.date(PromptUsageLog.used_at).label("date"),
                func.count().label("count"),
            )
            .where(
                PromptUsageLog.user_id == user_id,
                PromptUsageLog.used_at >= thirty_days_ago,
            )
            .group_by(func.date(PromptUsageLog.used_at))
            .order_by(func.date(PromptUsageLog.used_at))
        )
        daily_result = await db.execute(daily_query)
        daily_usage = [
            {"date": row.date, "count": row.count}
            for row in daily_result
        ]

        return {
            "total_uses": total_uses,
            "most_used": most_used,
            "daily_usage": daily_usage,
        }
