from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.response import orm_to_dict, success_response
from app.models.user import User
from app.schemas.note import NoteCreate, NoteDetailResponse, NoteListResponse, NoteUpdate
from app.services.category_service import CategoryService
from app.services.note_service import NoteService

router = APIRouter(tags=["笔记"])
service = NoteService()
category_service = CategoryService()


def _note_list_out(note, category_name: str | None = None) -> dict:
    return NoteListResponse.model_validate(
        {**orm_to_dict(note), "category_name": category_name}
    ).model_dump()


def _note_detail_out(note, category_name: str | None = None) -> dict:
    return NoteDetailResponse.model_validate(
        {**orm_to_dict(note), "category_name": category_name}
    ).model_dump()


async def _single_category_name(db: AsyncSession, category_id: int | None) -> str | None:
    if category_id is None:
        return None
    names = await category_service.get_name_map(db, {category_id})
    return names.get(category_id)


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
    # 一次批量查询分类名，避免逐条 get 造成 N+1
    names = await category_service.get_name_map(
        db, {n.category_id for n in notes if n.category_id is not None}
    )
    items = [_note_list_out(n, names.get(n.category_id)) for n in notes]

    return success_response(
        data={
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        },
        msg="获取笔记列表成功",
    )


@router.get("/{note_id}")
async def get_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await service.get_note(db, note_id, current_user.id)
    return success_response(
        data=_note_detail_out(note, await _single_category_name(db, note.category_id)),
        msg="获取笔记详情成功",
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_note(
    data: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await service.create_note(db, current_user.id, data)
    return success_response(
        data=_note_detail_out(note, await _single_category_name(db, note.category_id)),
        msg="创建笔记成功",
        code=201,
    )


@router.post("/import")
async def import_or_replace_note(
    data: NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note, replaced = await service.import_or_replace_note(db, current_user.id, data)
    return success_response(
        data=_note_detail_out(note, await _single_category_name(db, note.category_id)),
        msg="已替换同目录同名笔记" if replaced else "导入笔记成功",
    )


@router.put("/{note_id}")
async def update_note(
    note_id: int,
    data: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await service.update_note(db, note_id, current_user.id, data)
    return success_response(
        data=_note_detail_out(note, await _single_category_name(db, note.category_id)),
        msg="更新笔记成功",
    )


@router.delete("/{note_id}")
async def delete_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.delete_note(db, note_id, current_user.id)
    return success_response(msg="删除笔记成功")


@router.put("/{note_id}/pin")
async def toggle_pin(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await service.toggle_pin(db, note_id, current_user.id)
    return success_response(
        data={"id": note.id, "is_pinned": note.is_pinned},
        msg="切换置顶状态成功",
    )
