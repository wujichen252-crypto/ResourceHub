"""
提示词数据访问层
"""

from sqlalchemy import select, or_, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.prompt import Prompt, PromptVersion, PromptPreset
from app.repositories.base import BaseRepository


class PromptRepository(BaseRepository[Prompt]):
    """提示词数据访问类"""

    def __init__(self):
        super().__init__(Prompt)

    async def get_prompts(
        self,
        db: AsyncSession,
        user_id: int,
        page: int,
        page_size: int,
        category_id: int | None = None,
        is_favorite: bool | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        tag: str | None = None,
    ) -> tuple[list[Prompt], int]:
        """
        分页获取用户提示词列表

        Args:
            db: 数据库会话
            user_id: 用户 ID
            page: 页码
            page_size: 每页数量
            category_id: 分类 ID
            is_favorite: 是否收藏
            search: 搜索关键词
            sort_by: 排序字段
            tag: 标签

        Returns:
            (提示词列表, 总数)
        """
        query = select(Prompt).where(Prompt.user_id == user_id)

        if category_id is not None:
            query = query.where(Prompt.category_id == category_id)

        if is_favorite is not None:
            query = query.where(Prompt.is_favorite == is_favorite)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Prompt.title.like(search_pattern),
                    Prompt.description.like(search_pattern),
                    Prompt.content.like(search_pattern),
                )
            )

        if tag:
            tag_pattern = f'%"{tag}"%'
            query = query.where(Prompt.tags.like(tag_pattern))

        from sqlalchemy import func
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        sort_column = getattr(Prompt, sort_by, Prompt.created_at)
        query = query.order_by(desc(sort_column))
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        prompts = list(result.scalars().all())

        return prompts, total

    async def get_prompt_by_id(
        self, db: AsyncSession, prompt_id: int, user_id: int
    ) -> Prompt | None:
        """根据 ID 获取用户提示词"""
        result = await db.execute(
            select(Prompt).where(
                and_(Prompt.id == prompt_id, Prompt.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()


class PromptVersionRepository(BaseRepository[PromptVersion]):
    """提示词版本数据访问类"""

    def __init__(self):
        super().__init__(PromptVersion)

    async def get_versions_by_prompt_id(
        self, db: AsyncSession, prompt_id: int, user_id: int
    ) -> list[PromptVersion]:
        """获取提示词的所有版本"""
        result = await db.execute(
            select(PromptVersion)
            .join(Prompt, PromptVersion.prompt_id == Prompt.id)
            .where(
                and_(
                    PromptVersion.prompt_id == prompt_id,
                    Prompt.user_id == user_id,
                )
            )
            .order_by(desc(PromptVersion.version_number))
        )
        return list(result.scalars().all())

    async def get_version_by_id(
        self, db: AsyncSession, version_id: int, prompt_id: int, user_id: int
    ) -> PromptVersion | None:
        """根据 ID 获取提示词版本"""
        result = await db.execute(
            select(PromptVersion)
            .join(Prompt, PromptVersion.prompt_id == Prompt.id)
            .where(
                and_(
                    PromptVersion.id == version_id,
                    PromptVersion.prompt_id == prompt_id,
                    Prompt.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_version_number(
        self, db: AsyncSession, prompt_id: int
    ) -> int:
        """获取最新版本号"""
        from sqlalchemy import func
        result = await db.execute(
            select(func.max(PromptVersion.version_number)).where(
                PromptVersion.prompt_id == prompt_id
            )
        )
        return result.scalar_one() or 0


class PromptPresetRepository(BaseRepository[PromptPreset]):
    """提示词预设数据访问类"""

    def __init__(self):
        super().__init__(PromptPreset)

    async def get_presets_by_prompt_id(
        self, db: AsyncSession, prompt_id: int, user_id: int
    ) -> list[PromptPreset]:
        """获取提示词的所有预设"""
        result = await db.execute(
            select(PromptPreset)
            .join(Prompt, PromptPreset.prompt_id == Prompt.id)
            .where(
                and_(
                    PromptPreset.prompt_id == prompt_id,
                    Prompt.user_id == user_id,
                )
            )
            .order_by(PromptPreset.created_at)
        )
        return list(result.scalars().all())

    async def get_preset_by_id(
        self, db: AsyncSession, preset_id: int, user_id: int
    ) -> PromptPreset | None:
        """根据 ID 获取预设"""
        result = await db.execute(
            select(PromptPreset)
            .join(Prompt, PromptPreset.prompt_id == Prompt.id)
            .where(
                and_(
                    PromptPreset.id == preset_id,
                    Prompt.user_id == user_id,
                )
            )
        )
        return result.scalar_one_or_none()
