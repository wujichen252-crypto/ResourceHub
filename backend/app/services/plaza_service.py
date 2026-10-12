"""资源广场服务：发布/取消发布/广场浏览/fork 副本"""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, get_error_message
from app.models.note import Note
from app.models.prompt import Prompt
from app.models.user import User

VALID_TYPES = ("note", "prompt")


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": ErrorCode.PLAZA_ITEM_NOT_FOUND,
            "message": get_error_message(ErrorCode.PLAZA_ITEM_NOT_FOUND),
        },
    )


def _bad_type() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "code": ErrorCode.INVALID_CONTENT_TYPE,
            "message": get_error_message(ErrorCode.INVALID_CONTENT_TYPE),
        },
    )


class PlazaService:
    def _model(self, content_type: str):
        """按类型选择 ORM 模型，非法类型抛 5002"""
        if content_type == "note":
            return Note
        if content_type == "prompt":
            return Prompt
        raise _bad_type()

    async def _get_owned(self, db: AsyncSession, content_type: str, item_id: int, user_id: int):
        """获取属于当前用户的内容（发布/取消发布用），不存在或非本人 → 404"""
        model = self._model(content_type)
        result = await db.execute(
            select(model).where(model.id == item_id, model.user_id == user_id)
        )
        obj = result.scalar_one_or_none()
        if obj is None:
            raise _not_found()
        return obj

    async def publish(self, db: AsyncSession, content_type: str, item_id: int, user_id: int):
        """发布到广场：置 visibility=public 并记录发布时间"""
        obj = await self._get_owned(db, content_type, item_id, user_id)
        obj.visibility = "public"
        obj.published_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
        await db.refresh(obj)
        return obj

    async def unpublish(self, db: AsyncSession, content_type: str, item_id: int, user_id: int):
        """取消发布：置回 private 并清空发布时间"""
        obj = await self._get_owned(db, content_type, item_id, user_id)
        obj.visibility = "private"
        obj.published_at = None
        await db.commit()
        await db.refresh(obj)
        return obj

    async def list_items(
        self, db: AsyncSession, content_type: str,
        page: int = 1, page_size: int = 20,
        search: str | None = None, tag: str | None = None,
    ):
        """广场列表：join User 取作者信息，仅 public 内容"""
        model = self._model(content_type)
        query = (
            select(model, User.username, User.avatar)
            .join(User, User.id == model.user_id)
            .where(model.visibility == "public")
        )
        if search:
            query = query.where(
                or_(model.title.ilike(f"%{search}%"), model.content.ilike(f"%{search}%"))
            )
        if tag:
            query = query.where(model.tags.ilike(f"%{tag}%"))

        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar() or 0

        query = query.order_by(model.published_at.desc(), model.updated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(query)).all()
        return rows, total

    async def get_public_item(self, db: AsyncSession, content_type: str, item_id: int):
        """广场详情：仅 public 可读，否则 404（不泄露私有内容存在性）"""
        model = self._model(content_type)
        result = await db.execute(
            select(model, User.username, User.avatar)
            .join(User, User.id == model.user_id)
            .where(model.id == item_id, model.visibility == "public")
        )
        row = result.one_or_none()
        if row is None:
            raise _not_found()
        return row

    async def fork(self, db: AsyncSession, content_type: str, item_id: int, user_id: int):
        """复制一份 public 内容为当前用户的私有副本（保留署名溯源）"""
        row = await self.get_public_item(db, content_type, item_id)
        source = row[0]

        if content_type == "note":
            copy = Note(
                user_id=user_id,
                title=source.title,
                content=source.content,
                category_id=None,
                tags=source.tags,
                is_pinned=False,
                visibility="private",
                source_user_id=source.user_id,
                source_content_id=source.id,
                source_username=row[1],
            )
        else:
            copy = Prompt(
                user_id=user_id,
                title=source.title,
                description=source.description,
                content=source.content,
                category_id=None,
                variables=source.variables,
                tags=source.tags,
                is_favorite=False,
                usage_count=0,
                visibility="private",
                source_user_id=source.user_id,
                source_content_id=source.id,
                source_username=row[1],
            )
        db.add(copy)
        await db.commit()
        await db.refresh(copy)
        return copy

    async def list_mine(self, db: AsyncSession, user_id: int, content_type: str | None = None):
        """我发布到广场的内容（管理用）"""
        items: list[tuple] = []
        types = [content_type] if content_type else list(VALID_TYPES)
        for t in types:
            model = self._model(t)
            result = await db.execute(
                select(model).where(
                    model.user_id == user_id, model.visibility == "public"
                ).order_by(model.published_at.desc())
            )
            for obj in result.scalars().all():
                items.append((t, obj))
        return items
