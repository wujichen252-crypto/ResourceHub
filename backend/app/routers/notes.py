import json
import re

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.category import Category
from app.schemas.note import NoteCreate, NoteUpdate, NoteListResponse, NoteDetailResponse
from app.services.note_service import NoteService

router = APIRouter(tags=["笔记"])
service = NoteService()


def _strip_html(text: str) -> str:
    """去除 HTML 标签，用于生成纯文本预览"""
    return re.sub(r"<[^>]+>", "", text)


def _format_note_list(note, category_name: str | None = None) -> dict:
    tags = json.loads(note.tags) if note.tags else []
    raw = note.content or ""
    content_preview = _strip_html(raw)[:200].replace("\n", " ")
    return {
        "id": note.id,
        "title": note.title,
        "content_preview": content_preview,
        "category_id": note.category_id,
        "category_name": category_name,
        "tags": tags,
        "is_pinned": note.is_pinned,
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
    }


def _format_note_detail(note, category_name: str | None = None) -> dict:
    tags = json.loads(note.tags) if note.tags else []
    return {
        "id": note.id,
        "title": note.title,
        "content": note.content or "",
        "category_id": note.category_id,
        "category_name": category_name,
        "tags": tags,
        "is_pinned": note.is_pinned,
        "created_at": note.created_at.isoformat() if note.created_at else None,
        "updated_at": note.updated_at.isoformat() if note.updated_at else None,
    }


@router.get("")
async def list_notes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    category_id: int | None = None,
    tag: str | None = None,
    is_pinned: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notes, total = await service.get_notes(
        db, current_user.id, page, page_size, search, category_id, tag, is_pinned
    )
    items = []
    for n in notes:
        cat_name = None
        if n.category_id:
            cat = await db.get(Category, n.category_id)
            cat_name = cat.name if cat else None
        items.append(_format_note_list(n, cat_name))

    return {"data": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{note_id}")
async def get_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await service.get_note(db, note_id, current_user.id)
    cat_name = None
    if note.category_id:
        cat = await db.get(Category, note.category_id)
        cat_name = cat.name if cat else None
    return {"data": _format_note_detail(note, cat_name)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_note(
    data: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await service.create_note(db, current_user.id, data)
    cat_name = None
    if note.category_id:
        cat = await db.get(Category, note.category_id)
        cat_name = cat.name if cat else None
    return {"data": _format_note_detail(note, cat_name)}


@router.put("/{note_id}")
async def update_note(
    note_id: int,
    data: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await service.update_note(db, note_id, current_user.id, data)
    cat_name = None
    if note.category_id:
        cat = await db.get(Category, note.category_id)
        cat_name = cat.name if cat else None
    return {"data": _format_note_detail(note, cat_name)}


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.delete_note(db, note_id, current_user.id)


@router.put("/{note_id}/pin")
async def toggle_pin(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await service.toggle_pin(db, note_id, current_user.id)
    return {"data": {"id": note.id, "is_pinned": note.is_pinned}}
