"""工作台统计聚合 — 标签云 / 创作趋势 / 分类分布 / 使用热力图

全部基于现有列的只读聚合，无 schema 变更。
日期分桶在 Python 端完成，保证 SQLite（开发/测试）与 MySQL（生产）行为一致。
"""
from collections import Counter
from datetime import date, datetime, timedelta
import json
import re

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.note import Note
from app.models.prompt import Prompt, PromptUsageLog
from app.schemas.common import decode_json_list

TREND_DAYS = 30        # 创作趋势窗口
HEATMAP_DAYS = 120     # 使用热力图窗口
TAG_LIMIT = 60         # 标签云最多展示词数
REVIEW_ON_THIS_DAY_LIMIT = 6   # 每日回顾「往年今日」最多条数
REVIEW_STREAK_WINDOW = 365     # 连续记录天数的统计窗口
REVIEW_TASK_LIMIT = 5          # 每日回顾「昨日遗留任务」最多条数

_UNCHECKED_TASK_MD = re.compile(r"^\s*[-*]\s+\[\s?\]\s+(.+)$", re.M)


def _as_date(value: datetime | date | None) -> date | None:
    """DateTime/date 统一转为 date（SQLite 返回 datetime，个别驱动可能返回 date）"""
    if value is None:
        return None
    return value.date() if isinstance(value, datetime) else value


def _extract_unchecked_tasks(
    content: str | None, content_format: str, content_json: str | None
) -> list[str]:
    """从笔记内容提取未勾选任务：json 轨遍历 taskList 节点，markdown 轨走正则"""
    tasks: list[str] = []

    if content_format == "json" and content_json:
        try:
            doc = json.loads(content_json)
        except (ValueError, TypeError):
            doc = None

        def walk(node) -> None:
            if isinstance(node, list):
                for child in node:
                    walk(child)
                return
            if not isinstance(node, dict):
                return
            if node.get("type") == "taskItem":
                checked = (node.get("attrs") or {}).get("checked")
                if checked in (False, "false"):
                    text = " ".join(
                        child.get("text") or ""
                        for child in node.get("content") or []
                        if child.get("type") == "paragraph"
                    ).strip()
                    if text:
                        tasks.append(text[:80])
            walk(node.get("content"))

        if isinstance(doc, dict):
            walk(doc)
            return tasks

    if content:
        tasks.extend(match.strip()[:80] for match in _UNCHECKED_TASK_MD.findall(content))
    return tasks


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

    async def get_daily_review(self, db: AsyncSession, user_id: int) -> dict:
        """每日回顾：往年今日的笔记 + 近 7 天沉淀数 + 连续记录天数 + 昨日遗留任务"""
        today = date.today()
        rows = (await db.execute(
            select(Note.id, Note.title, Note.created_at)
            .where(Note.user_id == user_id, Note.team_id.is_(None))
        )).all()

        # 往年今日：只取历史年份，按时间倒序，最多 6 条
        on_this_day = [
            row for row in rows
            if row[2] is not None
            and row[2].date().year < today.year
            and (row[2].date().month, row[2].date().day) == (today.month, today.day)
        ]
        on_this_day.sort(key=lambda row: row[2], reverse=True)

        # 连续记录天数：从今天（或昨天）往回数每天至少写过一篇的日子
        active_days = {row[2].date() for row in rows if row[2] is not None}
        streak = 0
        cursor = today if today in active_days else today - timedelta(days=1)
        while cursor in active_days and streak <= REVIEW_STREAK_WINDOW:
            streak += 1
            cursor -= timedelta(days=1)

        # 昨日遗留：昨天创建或更新的笔记中未勾选的任务项（借鉴 SideNotes "yesterday's loose ends"）
        yesterday = today - timedelta(days=1)
        y_start = datetime.combine(yesterday, datetime.min.time())
        y_end = y_start + timedelta(days=1)
        task_rows = (await db.execute(
            select(Note.id, Note.title, Note.content, Note.content_format, Note.content_json)
            .where(
                Note.user_id == user_id,
                Note.team_id.is_(None),
                or_(Note.created_at >= y_start, Note.updated_at >= y_start),
                Note.created_at < y_end,
            )
            .order_by(Note.updated_at.desc())
            .limit(20)
        )).all()
        pending_tasks: list[dict] = []
        for note_id, title, content, content_format, content_json in task_rows:
            for task in _extract_unchecked_tasks(content, content_format, content_json):
                if len(pending_tasks) >= REVIEW_TASK_LIMIT:
                    break
                pending_tasks.append({"note_id": note_id, "note_title": title, "task": task})
            if len(pending_tasks) >= REVIEW_TASK_LIMIT:
                break

        return {
            "on_this_day": [
                {
                    "id": row[0],
                    "title": row[1],
                    "years_ago": today.year - row[2].date().year,
                    "created_at": row[2].isoformat(timespec="seconds"),
                }
                for row in on_this_day[:REVIEW_ON_THIS_DAY_LIMIT]
            ],
            "on_this_day_total": len(on_this_day),
            "this_week": sum(
                1 for row in rows
                if row[2] is not None and row[2].date() >= today - timedelta(days=6)
            ),
            "streak": streak,
            "pending_tasks": pending_tasks,
        }

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
