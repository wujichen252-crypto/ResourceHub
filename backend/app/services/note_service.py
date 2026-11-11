import json
import uuid

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode
from app.models.category import Category
from app.models.note import Note
from app.schemas.note import NoteCreate, NoteUpdate
from app.services.search_service import search_service
from app.services.tag_service import dump_tags, parse_tags
from app.services.team_service import TeamService

team_service = TeamService()


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
        team_id: int | None = None,
    ):
        """列表查询：team_id 为空查个人空间，有值查团队空间（需成员身份）"""
        if team_id is not None:
            if not await team_service.is_member(db, team_id, user_id):
                raise HTTPException(
                    status_code=403,
                    detail={"code": ErrorCode.TEAM_FORBIDDEN, "message": "仅团队成员可以访问该团队资源"},
                )
            query = select(Note).where(Note.team_id == team_id)
        else:
            # 个人空间：排除已归属团队的笔记，避免团队资源混入个人列表
            query = select(Note).where(Note.user_id == user_id, Note.team_id.is_(None))

        if search:
            if team_id is None:
                # 优先走 Meilisearch（容错 + 中文分词）；服务不可用或索引为空（存量笔记未回填）时降级 LIKE
                hit_ids = await search_service.search_note_ids(user_id, search)
                if not hit_ids:
                    query = query.where(
                        or_(Note.title.ilike(f"%{search}%"), Note.content.ilike(f"%{search}%"))
                    )
                else:
                    query = query.where(Note.id.in_(hit_ids))
            else:
                # 团队空间包含其他成员创建的笔记，不在个人搜索索引范围内，统一走 LIKE
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

    async def get_all_notes(self, db: AsyncSession, user_id: int) -> list[Note]:
        """导出用：不分页取当前用户个人笔记（团队共享笔记不参与个人导出）"""
        result = await db.execute(
            select(Note)
            .where(Note.user_id == user_id, Note.team_id.is_(None))
            .order_by(Note.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_note(
        self, db: AsyncSession, note_id: int, user_id: int, for_write: bool = False
    ) -> Note:
        """读取笔记：本人 → 团队成员（写操作另需作者或团队管理员身份）"""
        note = await db.scalar(select(Note).where(Note.id == note_id))
        if note is None:
            raise HTTPException(status_code=404, detail={"code": ErrorCode.NOTE_NOT_FOUND, "message": "笔记不存在"})
        if note.user_id == user_id:
            return note
        if note.team_id is not None:
            if for_write:
                if await team_service.can_manage(db, note.team_id, user_id):
                    return note
                if await team_service.is_member(db, note.team_id, user_id):
                    raise HTTPException(
                        status_code=403,
                        detail={"code": ErrorCode.TEAM_FORBIDDEN, "message": "只有作者或团队管理员可以修改该笔记"},
                    )
            elif await team_service.is_member(db, note.team_id, user_id):
                return note
        # 非本人且非团队成员：按不存在处理，避免泄露资源是否存在
        raise HTTPException(status_code=404, detail={"code": ErrorCode.NOTE_NOT_FOUND, "message": "笔记不存在"})

    async def create_note(self, db: AsyncSession, user_id: int, data: NoteCreate) -> Note:
        await team_service.assert_can_write_team_resource(db, data.team_id, user_id)
        note = Note(
            user_id=user_id,
            team_id=data.team_id,
            title=data.title,
            # 团队空间不使用个人分类树，避免把作者的个人目录暴露给团队成员
            category_id=None if data.team_id is not None else data.category_id,
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
        await team_service.assert_can_write_team_resource(db, data.team_id, user_id)
        result = await db.execute(
            select(Note).where(
                Note.user_id == user_id,
                Note.team_id == data.team_id,
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
        note = await self.get_note(db, note_id, user_id, for_write=True)
        update_data = data.model_dump(exclude_unset=True)
        # 资源归属变更（个人 ↔ 团队）只允许作者本人操作，且需目标团队身份校验
        if "team_id" in update_data and update_data["team_id"] != note.team_id:
            if note.user_id != user_id:
                raise HTTPException(
                    status_code=403,
                    detail={"code": ErrorCode.TEAM_FORBIDDEN, "message": "只有作者可以调整资源归属"},
                )
            await team_service.assert_can_write_team_resource(db, update_data["team_id"], user_id)
            if update_data["team_id"] is not None:
                update_data["category_id"] = None
        # 团队资源始终不挂个人分类，防止把作者的个人目录带进团队空间
        if note.team_id is not None and "category_id" in update_data:
            update_data["category_id"] = None
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
        note = await self.get_note(db, note_id, user_id, for_write=True)
        await db.delete(note)
        await db.commit()

    async def batch_notes(
        self,
        db: AsyncSession,
        user_id: int,
        ids: list[int],
        action: str,
        category_id: int | None = None,
        tags: list[str] | None = None,
    ) -> list[Note]:
        """批量移动 / 追加标签 / 删除；只处理属于当前用户的笔记，返回命中的笔记"""
        result = await db.execute(
            select(Note).where(Note.user_id == user_id, Note.id.in_(ids))
        )
        notes = list(result.scalars().all())
        if not notes:
            return []

        if action == "move":
            if category_id is not None:
                category = await db.execute(
                    select(Category).where(
                        Category.id == category_id,
                        Category.user_id == user_id,
                        Category.type == "note",
                    )
                )
                if not category.scalar_one_or_none():
                    raise HTTPException(
                        status_code=404,
                        detail={"code": ErrorCode.CATEGORY_NOT_FOUND, "message": "目录不存在"},
                    )
            for note in notes:
                note.category_id = category_id
        elif action == "tag":
            incoming = [tag.strip() for tag in (tags or []) if tag.strip()]
            if not incoming:
                raise HTTPException(
                    status_code=400,
                    detail={"code": ErrorCode.VALIDATION_ERROR, "message": "请选择要添加的标签"},
                )
            for note in notes:
                merged = parse_tags(note.tags)
                merged.extend(tag for tag in incoming if tag not in merged)
                note.tags = dump_tags(merged)
        elif action == "delete":
            for note in notes:
                await db.delete(note)

        await db.commit()
        return notes

    async def toggle_pin(self, db: AsyncSession, note_id: int, user_id: int) -> Note:
        note = await self.get_note(db, note_id, user_id, for_write=True)
        note.is_pinned = not note.is_pinned
        await db.commit()
        await db.refresh(note)
        return note
