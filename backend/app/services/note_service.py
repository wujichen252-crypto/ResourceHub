import json
import uuid

from sqlalchemy import select, func, or_, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.errors import ErrorCode
from app.models.note import Note
from app.models.category import Category
from app.schemas.note import NoteCreate, NoteUpdate
from app.services.search_service import search_service


def _ensure_block_ids(content_json: dict) -> dict:
    """顶层块缺失稳定 id 时补充 uuid 短码（反链 / 引用锚点的前提），已有 id 原样保留"""
    for block in content_json.get("content") or []:
        if not isinstance(block, dict):
            continue
        attrs = block.setdefault("attrs", {})
        if not attrs.get("id"):
            attrs["id"] = uuid.uuid4().hex[:12]
    return content_json


def _apply_dual_track(note: Note, content: str | None, content_json: dict | None) -> None:
    """存储双轨：content_json 有效时以块文档为权威并同步 HTML 快照；否则回落 markdown 单轨"""
    if content_json:
        note.content_format = "json"
        note.content_json = json.dumps(
            _ensure_block_ids(content_json), ensure_ascii=False
        )
        note.content = content  # 前端 getHTML() 兼容快照
    else:
        note.content_format = "markdown"
        note.content_json = None
        note.content = content


class NoteService:
    async def _get_category_subtree_ids(
        self, db: AsyncSession, user_id: int, category_id: int
    ) -> list[int]:
        """递归获取分类及其所有子分类的 ID 列表（用于语雀式目录树查询）"""
        result = await db.execute(
            select(Category).where(Category.user_id == user_id, Category.type == "note")
        )
        all_cats = result.scalars().all()
        ids: list[int] = [category_id]

        def collect(parent_id: int) -> None:
            for cat in all_cats:
                if cat.parent_id == parent_id:
                    ids.append(cat.id)
                    collect(cat.id)

        collect(category_id)
        return ids

    async def get_notes(
        self, db: AsyncSession, user_id: int,
        page: int = 1, page_size: int = 20,
        search: str | None = None,
        category_id: int | None = None,
        tag: str | None = None,
        is_pinned: bool | None = None,
    ):
        query = select(Note).where(Note.user_id == user_id)

        if search:
            # 优先走 Meilisearch（容错 + 中文分词）；服务不可用或索引为空（存量笔记未回填）时降级 LIKE
            hit_ids = await search_service.search_note_ids(user_id, search)
            if not hit_ids:
                query = query.where(
                    or_(Note.title.ilike(f"%{search}%"), Note.content.ilike(f"%{search}%"))
                )
            else:
                query = query.where(Note.id.in_(hit_ids))
        if category_id is not None:
            query = query.where(Note.category_id == category_id)
        if tag:
            query = query.where(Note.tags.ilike(f"%{tag}%"))
        if is_pinned is not None:
            query = query.where(Note.is_pinned == is_pinned)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # Order and paginate
        query = query.order_by(Note.is_pinned.desc(), Note.updated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        notes = result.scalars().all()

        return notes, total

    async def get_note(self, db: AsyncSession, note_id: int, user_id: int) -> Note:
        result = await db.execute(
            select(Note).where(Note.id == note_id, Note.user_id == user_id)
        )
        note = result.scalar_one_or_none()
        if not note:
            raise HTTPException(status_code=404, detail={"code": ErrorCode.NOTE_NOT_FOUND, "message": "笔记不存在"})
        return note

    async def create_note(self, db: AsyncSession, user_id: int, data: NoteCreate) -> Note:
        note = Note(
            user_id=user_id,
            title=data.title,
            category_id=data.category_id,
            tags=json.dumps(data.tags, ensure_ascii=False) if data.tags else None,
        )
        _apply_dual_track(note, data.content, data.content_json)
        db.add(note)
        await db.commit()
        await db.refresh(note)
        return note

    async def import_or_replace_note(
        self, db: AsyncSession, user_id: int, data: NoteCreate
    ) -> tuple[Note, bool]:
        """导入笔记：同一目录下同名笔记覆盖旧内容，不同目录允许同名。"""
        result = await db.execute(
            select(Note).where(
                Note.user_id == user_id,
                Note.category_id == data.category_id,
                Note.title == data.title,
            )
        )
        note = result.scalar_one_or_none()
        if note:
            note.tags = json.dumps(data.tags, ensure_ascii=False) if data.tags else None
            _apply_dual_track(note, data.content, data.content_json)
            await db.commit()
            await db.refresh(note)
            return note, True

        return await self.create_note(db, user_id, data), False

    async def update_note(
        self, db: AsyncSession, note_id: int, user_id: int, data: NoteUpdate
    ) -> Note:
        note = await self.get_note(db, note_id, user_id)
        update_data = data.model_dump(exclude_unset=True)
        if "tags" in update_data:
            update_data["tags"] = (
                json.dumps(data.tags, ensure_ascii=False) if data.tags else None
            )
        # 双轨字段单独走 _apply_dual_track（含 JSON 序列化与块 id 校验），不走 setattr
        if "content" in update_data or "content_json" in update_data:
            _apply_dual_track(
                note, update_data.pop("content", note.content), update_data.pop("content_json", None)
            )
        for key, value in update_data.items():
            setattr(note, key, value)
        await db.commit()
        await db.refresh(note)
        return note

    async def delete_note(self, db: AsyncSession, note_id: int, user_id: int) -> None:
        note = await self.get_note(db, note_id, user_id)
        await db.delete(note)
        await db.commit()

    async def toggle_pin(self, db: AsyncSession, note_id: int, user_id: int) -> Note:
        note = await self.get_note(db, note_id, user_id)
        note.is_pinned = not note.is_pinned
        await db.commit()
        await db.refresh(note)
        return note
