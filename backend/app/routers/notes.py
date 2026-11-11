import json
from datetime import date

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.errors import ErrorCode
from app.core.response import orm_to_dict, success_response
from app.models.user import User
from app.schemas.note import (
    NoteBatchRequest,
    NoteCreate,
    NoteDetailResponse,
    NoteListResponse,
    NoteUpdate,
)
from app.services import note_markdown_service
from app.services.ai.index_service import index_note_in_background
from app.services.category_service import CategoryService
from app.services.note_service import NoteService
from app.services.search_service import remove_note_from_search, sync_note_to_search

router = APIRouter(tags=["笔记"])
service = NoteService()
category_service = CategoryService()


def _note_list_out(note, category_name: str | None = None, owner_username: str | None = None) -> dict:
    return NoteListResponse.model_validate(
        {**orm_to_dict(note), "category_name": category_name, "owner_username": owner_username}
    ).model_dump()


def _note_detail_out(note, category_name: str | None = None, owner_username: str | None = None) -> dict:
    return NoteDetailResponse.model_validate(
        {**orm_to_dict(note), "category_name": category_name, "owner_username": owner_username}
    ).model_dump()


async def _owner_name_map(db: AsyncSession, user_ids: set[int]) -> dict[int, str]:
    """批量查询作者用户名，供团队空间列表展示，避免逐条查询"""
    if not user_ids:
        return {}
    result = await db.execute(select(User.id, User.username).where(User.id.in_(user_ids)))
    return dict(result.all())


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
    team_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notes, total = await service.get_notes(
        db, current_user.id, page, page_size, search, category_id, tag, is_pinned, team_id
    )
    # 一次批量查询分类名，避免逐条 get 造成 N+1
    names = await category_service.get_name_map(
        db, {n.category_id for n in notes if n.category_id is not None}
    )
    # 团队空间展示作者，个人空间无需额外查询
    owners = (
        await _owner_name_map(db, {n.user_id for n in notes})
        if team_id is not None
        else {}
    )
    items = [
        _note_list_out(n, names.get(n.category_id), owners.get(n.user_id)) for n in notes
    ]

    return success_response(
        data={
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        },
        msg="获取笔记列表成功",
    )


@router.get("/export/markdown")
async def export_notes_markdown(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量导出全部笔记：zip 内每篇一个 .md，带 title/tags 等 frontmatter"""
    notes = await service.get_all_notes(db, current_user.id)
    payload = note_markdown_service.notes_to_markdown_zip(notes)
    filename = f"resourcehub-notes-{date.today():%Y%m%d}.zip"
    return Response(
        content=payload,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/json")
async def export_notes_json(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量导出全部笔记全文为 JSON"""
    notes = await service.get_all_notes(db, current_user.id)
    items = [
        NoteDetailResponse.model_validate(orm_to_dict(note)).model_dump(mode="json")
        for note in notes
    ]
    filename = f"resourcehub-notes-{date.today():%Y%m%d}.json"
    return Response(
        content=json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8"),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/import/markdown")
async def import_notes_markdown(
    background: BackgroundTasks,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量导入 Markdown：.md/.markdown 单文件或包含它们的 .zip；同目录同名笔记覆盖"""
    if not files:
        raise HTTPException(
            status_code=400,
            detail={"code": ErrorCode.VALIDATION_ERROR, "message": "没有选择文件"},
        )
    if len(files) > note_markdown_service.MAX_IMPORT_FILES:
        raise HTTPException(
            status_code=400,
            detail={"code": ErrorCode.VALIDATION_ERROR, "message": "单次最多导入 200 个文件"},
        )

    entries: list[tuple[str, str]] = []
    skipped: list[dict] = []
    for upload in files:
        filename = upload.filename or "note.md"
        raw = await upload.read(note_markdown_service.MAX_FILE_BYTES + 1)
        if len(raw) > note_markdown_service.MAX_FILE_BYTES:
            skipped.append({"file": filename, "reason": "文件超过 2MB"})
            continue
        try:
            extracted = note_markdown_service.extract_markdown_files(filename, raw)
        except ValueError as exc:
            skipped.append({"file": filename, "reason": str(exc)})
            continue
        if not extracted:
            skipped.append({"file": filename, "reason": "未找到 Markdown 文件"})
            continue
        entries.extend(extracted)

    if len(entries) > note_markdown_service.MAX_IMPORT_FILES:
        skipped.extend(
            {"file": name, "reason": "超过单次 200 篇上限"}
            for name, _ in entries[note_markdown_service.MAX_IMPORT_FILES:]
        )
        entries = entries[: note_markdown_service.MAX_IMPORT_FILES]

    created = 0
    replaced = 0
    for name, text in entries:
        parsed = note_markdown_service.parse_markdown(name, text)
        if not parsed["content"].strip():
            skipped.append({"file": name, "reason": "内容为空"})
            continue
        try:
            note, was_replaced = await service.import_or_replace_note(
                db, current_user.id, NoteCreate(**parsed)
            )
        except Exception:
            skipped.append({"file": name, "reason": "写入失败"})
            continue
        background.add_task(index_note_in_background, current_user.id, note.id)
        background.add_task(sync_note_to_search, current_user.id, note.id)
        if was_replaced:
            replaced += 1
        else:
            created += 1

    return success_response(
        data={
            "created": created,
            "replaced": replaced,
            "skipped": skipped,
            "total": len(entries),
        },
        msg=f"导入完成：新增 {created} 篇，覆盖 {replaced} 篇",
    )


@router.post("/batch")
async def batch_notes(
    data: NoteBatchRequest,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量操作：移动目录 / 追加标签 / 删除（仅限本人笔记）"""
    notes = await service.batch_notes(
        db, current_user.id, data.ids, data.action, data.category_id, data.tags
    )
    if data.action == "delete":
        for note in notes:
            background.add_task(remove_note_from_search, note.id)
    else:
        # 标签可能进入搜索索引，移动不影响正文本但仍整篇重建，逻辑简单且幂等
        for note in notes:
            background.add_task(index_note_in_background, current_user.id, note.id)
            background.add_task(sync_note_to_search, current_user.id, note.id)
    return success_response(
        data={"affected": len(notes)}, msg=f"已处理 {len(notes)} 篇笔记"
    )


@router.get("/{note_id}")
async def get_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await service.get_note(db, note_id, current_user.id)
    owners = (
        await _owner_name_map(db, {note.user_id}) if note.team_id is not None else {}
    )
    return success_response(
        data=_note_detail_out(
            note,
            await _single_category_name(db, note.category_id),
            owners.get(note.user_id),
        ),
        msg="获取笔记详情成功",
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_note(
    data: NoteCreate,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await service.create_note(db, current_user.id, data)
    # 增量索引放到响应之后执行：向量化耗时不应阻塞保存
    background.add_task(index_note_in_background, current_user.id, note.id)
    # 搜索索引与 RAG 索引同点位，走轻量整篇重建
    background.add_task(sync_note_to_search, current_user.id, note.id)
    return success_response(
        data=_note_detail_out(note, await _single_category_name(db, note.category_id)),
        msg="创建笔记成功",
        code=201,
    )


@router.post("/import")
async def import_or_replace_note(
    data: NoteCreate,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note, replaced = await service.import_or_replace_note(db, current_user.id, data)
    background.add_task(index_note_in_background, current_user.id, note.id)
    background.add_task(sync_note_to_search, current_user.id, note.id)
    return success_response(
        data=_note_detail_out(note, await _single_category_name(db, note.category_id)),
        msg="已替换同目录同名笔记" if replaced else "导入笔记成功",
    )


@router.put("/{note_id}")
async def update_note(
    note_id: int,
    data: NoteUpdate,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await service.update_note(db, note_id, current_user.id, data)
    # 自动保存会高频触发，索引任务内部做整篇重建，天然幂等
    background.add_task(index_note_in_background, current_user.id, note.id)
    background.add_task(sync_note_to_search, current_user.id, note.id)
    return success_response(
        data=_note_detail_out(note, await _single_category_name(db, note.category_id)),
        msg="更新笔记成功",
    )


@router.delete("/{note_id}")
async def delete_note(
    note_id: int,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.delete_note(db, note_id, current_user.id)
    # 索引侧同步清理，避免已删笔记仍出现在搜索结果
    background.add_task(remove_note_from_search, note_id)
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
