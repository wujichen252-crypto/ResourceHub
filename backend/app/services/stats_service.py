"""工作台统计聚合 — 标签云 / 创作趋势 / 分类分布 / 使用热力图

全部基于现有列的只读聚合，无 schema 变更。
日期分桶在 Python 端完成，保证 SQLite（开发/测试）与 MySQL（生产）行为一致。
"""
from collections import Counter
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.note import Note
from app.models.prompt import Prompt, PromptUsageLog
from app.schemas.common import decode_json_list

TREND_DAYS = 30        # 创作趋势窗口
HEATMAP_DAYS = 120     # 使用热力图窗口
TAG_LIMIT = 60         # 标签云最多展示词数


def _as_date(value: datetime | date | None) -> date | None:
    """DateTime/date 统一转为 date（SQLite 返回 datetime，个别驱动可能返回 date）"""
    if value is None:
        return None
    return value.date() if isinstance(value, datetime) else value


class StatsService:
    async def get_overview(self, db: AsyncSession, user_id: int) -> dict:
        """一次返回 Dashboard 四个可视化模块所需的全部聚合数据"""
        notes_rows = (await db.execute(
            select(Note.tags, Note.created_at, Note.category_id).where(Note.user_id == user_id)
        )).all()
        prompts_rows = (await db.execute(
            select(Prompt.tags, Prompt.created_at).where(Prompt.user_id == user_id)
        )).all()

        return {
            "tag_cloud": self._tag_cloud(notes_rows, prompts_rows),
            "creation_trend": self._creation_trend(notes_rows, prompts_rows),
            "category_distribution": await self._category_distribution(db, user_id, notes_rows),
            "usage_heatmap": await self._usage_heatmap(db, user_id),
        }

    def _tag_cloud(self, notes_rows, prompts_rows) -> list[dict]:
        """笔记 + 提示词的 tags（JSON 数组字符串）合并计数，按频次降序截断"""
        counter: Counter[str] = Counter()
        for row in list(notes_rows) + list(prompts_rows):
            raw = row[0]
            try:
                tags = decode_json_list(raw)
            except (ValueError, TypeError):
                continue  # 脏数据跳过，不影响整体统计
            for tag in tags:
                name = str(tag).strip()
                if name:
                    counter[name] += 1
        return [
            {"name": name, "value": value}
            for name, value in counter.most_common(TAG_LIMIT)
        ]

    def _creation_trend(self, notes_rows, prompts_rows) -> list[dict]:
        """近 TREND_DAYS 天逐日新增笔记/提示词数（缺失日补 0）"""
        today = date.today()
        start = today - timedelta(days=TREND_DAYS - 1)
        note_days: Counter[date] = Counter()
        prompt_days: Counter[date] = Counter()
        for row in notes_rows:
            d = _as_date(row[1])
            if d and d >= start:
                note_days[d] += 1
        for row in prompts_rows:
            d = _as_date(row[1])
            if d and d >= start:
                prompt_days[d] += 1
        return [
            {
                "date": (start + timedelta(days=i)).isoformat(),
                "notes": note_days.get(start + timedelta(days=i), 0),
                "prompts": prompt_days.get(start + timedelta(days=i), 0),
            }
            for i in range(TREND_DAYS)
        ]

    async def _category_distribution(
        self, db: AsyncSession, user_id: int, notes_rows
    ) -> list[dict]:
        """笔记按一级分类（回溯 parent_id 到根祖先）聚合数量"""
        categories = (await db.execute(
            select(Category.id, Category.name, Category.parent_id)
            .where(Category.user_id == user_id, Category.type == "note")
        )).all()
        info = {row[0]: (row[1], row[2]) for row in categories}

        def root_of(category_id: int) -> str:
            """回溯到一级分类名称；断链（分类已删）或环则归入未分类"""
            seen: set[int] = set()
            current = category_id
            while current in info:
                if current in seen:  # 防御环
                    break
                seen.add(current)
                name, parent_id = info[current]
                if parent_id is None:
                    return name
                current = parent_id
            return "未分类"

        counter: Counter[str] = Counter()
        for row in notes_rows:
            cid = row[2]
            counter[root_of(cid) if cid is not None else "未分类"] += 1
        return [
            {"name": name, "value": value}
            for name, value in counter.most_common()
        ]

    async def _usage_heatmap(self, db: AsyncSession, user_id: int) -> list[dict]:
        """近 HEATMAP_DAYS 天提示词使用次数按日计数（仅返回有使用的日期）"""
        start = date.today() - timedelta(days=HEATMAP_DAYS - 1)
        rows = (await db.execute(
            select(PromptUsageLog.used_at).where(
                PromptUsageLog.user_id == user_id,
                PromptUsageLog.used_at >= datetime.combine(start, datetime.min.time()),
            )
        )).scalars().all()
        counter: Counter[date] = Counter()
        for used_at in rows:
            d = _as_date(used_at)
            if d:
                counter[d] += 1
        return [
            {"date": d.isoformat(), "count": c}
            for d, c in sorted(counter.items())
        ]
