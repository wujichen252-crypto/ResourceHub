"""
笔记数据访问层
"""

from sqlalchemy import select, or_, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note
from app.repositories.base import BaseRepository


class NoteRepository(BaseRepository[Note]):
    """笔记数据访问类"""

    def __init__(self):
        super().__init__(Note)

    async def get_notes(
        self,
        db: AsyncSession,
        user_id: int,
        page: int,
        page_size: int,
        search: str | None = None,
        category_id: int | None = None,
        tag: str | None = None,
        is_pinned: bool | None = None,
    ) -> tuple[list[Note], int]:
        """
        分页获取用户笔记列表

        Args:
            db: 数据库会话
            user_id: 用户 ID
            page: 页码
            page_size: 每页数量
            search: 搜索关键词
            category_id: 分类 ID
            tag: 标签
            is_pinned: 是否置顶

        Returns:
            (笔记列表, 总数)
        """
        query = select(Note).where(Note.user_id == user_id)

        if category_id is not None:
            query = query.where(Note.category_id == category_id)

        if is_pinned is not None:
            query = query.where(Note.is_pinned == is_pinned)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Note.title.like(search_pattern),
                    Note.content.like(search_pattern),
                )
            )

        if tag:
            tag_pattern = f'%"{tag}"%'
            query = query.where(Note.tags.like(tag_pattern))

        count_query = select(Note).where(Note.user_id == user_id)
        if category_id is not None:
            count_query = count_query.where(Note.category_id == category_id)
        if is_pinned is not None:
            count_query = count_query.where(Note.is_pinned == is_pinned)
        if search:
            search_pattern = f"%{search}%"
            count_query = count_query.where(
                or_(
                    Note.title.like(search_pattern),
                    Note.content.like(search_pattern),
                )
            )
        if tag:
            tag_pattern = f'%"{tag}"%'
            count_query = count_query.where(Note.tags.like(tag_pattern))

        from sqlalchemy import func
        total_result = await db.execute(
            select(func.count()).select_from(count_query.subquery())
        )
        total = total_result.scalar_one()

        query = query.order_by(desc(Note.is_pinned), desc(Note.updated_at))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        notes = list(result.scalars().all())

        return notes, total

    async def get_note_by_id(
        self, db: AsyncSession, note_id: int, user_id: int
    ) -> Note | None:
        """根据 ID 获取用户笔记"""
        result = await db.execute(
            select(Note).where(
                and_(Note.id == note_id, Note.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()
