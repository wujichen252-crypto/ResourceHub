import json
from sqlalchemy import select, func, or_, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.note import Note
from app.models.category import Category
from app.schemas.note import NoteCreate, NoteUpdate


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
            query = query.where(
                or_(Note.title.ilike(f"%{search}%"), Note.content.ilike(f"%{search}%"))
            )
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
            raise HTTPException(status_code=404, detail={"code": 404, "message": "笔记不存在"})
        return note

    async def create_note(self, db: AsyncSession, user_id: int, data: NoteCreate) -> Note:
        note = Note(
            user_id=user_id,
            title=data.title,
            content=data.content,
            category_id=data.category_id,
            tags=json.dumps(data.tags, ensure_ascii=False) if data.tags else None,
        )
        db.add(note)
        await db.commit()
        await db.refresh(note)
        return note

    async def update_note(
        self, db: AsyncSession, note_id: int, user_id: int, data: NoteUpdate
    ) -> Note:
        note = await self.get_note(db, note_id, user_id)
        update_data = data.model_dump(exclude_unset=True)
        if "tags" in update_data:
            update_data["tags"] = (
                json.dumps(data.tags, ensure_ascii=False) if data.tags else None
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
