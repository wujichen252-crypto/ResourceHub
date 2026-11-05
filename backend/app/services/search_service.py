"""全局统一搜索服务：跨笔记与提示词的聚合检索"""

import re
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note
from app.models.prompt import Prompt
from app.services.category_service import CategoryService

# snippet 命中点前后各保留的字符数
SNIPPET_CONTEXT = 80
# 多个连续空白压缩成一个空格（Markdown 正文换行多，直接放进面板会破坏排版）
_WHITESPACE_RE = re.compile(r"\s+")
# 摘要去掉的 Markdown 装饰符（标题井号、强调星号等），提升可读性
_MD_DECOR_RE = re.compile(r"^[#>*\-\s]+|[`*_]+")


class SearchService:
    """搜索当前用户自己的笔记与提示词，返回带摘要片段的聚合结果"""

    def __init__(self):
        self.category_service = CategoryService()

    async def search(self, db: AsyncSession, user_id: int, query: str, limit: int) -> dict:
        """聚合搜索入口，返回 {"query", "total", "items"}"""
        notes = await self._search_notes(db, user_id, query, limit)
        prompts = await self._search_prompts(db, user_id, query, limit)

        # 分类名批量查询，避免逐条 get 造成 N+1
        category_ids = {n.category_id for n in notes if n.category_id is not None} | {
            p.category_id for p in prompts if p.category_id is not None
        }
        name_map = await self.category_service.get_name_map(db, category_ids)

        items = [
            self._note_item(n, name_map.get(n.category_id), query) for n in notes
        ] + [
            self._prompt_item(p, name_map.get(p.category_id), query) for p in prompts
        ]

        return {"query": query, "total": len(items), "items": items}

    async def _search_notes(
        self, db: AsyncSession, user_id: int, query: str, limit: int
    ) -> list:
        pattern = f"%{query}%"
        result = await db.execute(
            select(Note)
            .where(
                Note.user_id == user_id,
                or_(Note.title.ilike(pattern), Note.content.ilike(pattern)),
            )
            # 置顶优先 → 标题命中优先 → 最近更新优先
            .order_by(
                Note.is_pinned.desc(), Note.title.ilike(pattern).desc(),
                Note.updated_at.desc(),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _search_prompts(
        self, db: AsyncSession, user_id: int, query: str, limit: int
    ) -> list:
        pattern = f"%{query}%"
        result = await db.execute(
            select(Prompt)
            .where(
                Prompt.user_id == user_id,
                or_(
                    Prompt.title.ilike(pattern),
                    Prompt.description.ilike(pattern),
                    Prompt.content.ilike(pattern),
                ),
            )
            .order_by(Prompt.title.ilike(pattern).desc(), Prompt.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    def _note_item(self, note: Note, category_name: str | None, query: str) -> dict:
        return {
            "type": "note",
            "id": note.id,
            "title": note.title,
            "snippet": self._make_snippet(note.content, query),
            "category_name": category_name,
            "tags": self._parse_tags(note.tags),
            "updated_at": self._format_time(note.updated_at),
        }

    def _prompt_item(self, prompt: Prompt, category_name: str | None, query: str) -> dict:
        # 摘要优先取简介（更接近"人话"），无简介再取正文
        text = prompt.description or prompt.content
        return {
            "type": "prompt",
            "id": prompt.id,
            "title": prompt.title,
            "snippet": self._make_snippet(text, query),
            "category_name": category_name,
            "tags": self._parse_tags(prompt.tags),
            "updated_at": self._format_time(prompt.updated_at),
        }

    def _make_snippet(self, text: str | None, query: str) -> str:
        """提取首个命中位置前后约 SNIPPET_CONTEXT 字符的摘要片段"""
        if not text:
            return ""
        cleaned = _MD_DECOR_RE.sub("", text)
        cleaned = _WHITESPACE_RE.sub(" ", cleaned).strip()
        if not cleaned:
            return ""

        pos = cleaned.lower().find(query.lower())
        if pos == -1:
            # 标题命中但正文未命中：直接取正文开头
            return cleaned[: SNIPPET_CONTEXT] + ("…" if len(cleaned) > SNIPPET_CONTEXT else "")

        start = max(0, pos - SNIPPET_CONTEXT)
        end = min(len(cleaned), pos + len(query) + SNIPPET_CONTEXT)
        snippet = cleaned[start:end]
        prefix = "…" if start > 0 else ""
        suffix = "…" if end < len(cleaned) else ""
        return prefix + snippet + suffix

    @staticmethod
    def _parse_tags(raw: str | None) -> list[str]:
        if not raw:
            return []
        try:
            import json
            tags = json.loads(raw)
            return tags if isinstance(tags, list) else []
        except (ValueError, TypeError):
            return []

    @staticmethod
    def _format_time(dt: datetime | None) -> str | None:
        return dt.isoformat() if dt else None
