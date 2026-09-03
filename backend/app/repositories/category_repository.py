"""
分类数据访问层
"""

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.repositories.base import BaseRepository


class CategoryRepository(BaseRepository[Category]):
    """分类数据访问类"""

    def __init__(self):
        super().__init__(Category)

    async def get_categories_by_type(
        self, db: AsyncSession, user_id: int, type: str
    ) -> list[Category]:
        """
        获取用户指定类型的所有分类

        Args:
            db: 数据库会话
            user_id: 用户 ID
            type: 分类类型 (note 或 prompt)

        Returns:
            分类列表
        """
        result = await db.execute(
            select(Category)
            .where(and_(Category.user_id == user_id, Category.type == type))
            .order_by(Category.sort_order, Category.id)
        )
        return list(result.scalars().all())

    async def get_category_by_id(
        self, db: AsyncSession, category_id: int, user_id: int
    ) -> Category | None:
        """根据 ID 获取用户分类"""
        result = await db.execute(
            select(Category).where(
                and_(Category.id == category_id, Category.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_children(
        self, db: AsyncSession, parent_id: int, user_id: int
    ) -> list[Category]:
        """获取子分类列表"""
        result = await db.execute(
            select(Category).where(
                and_(
                    Category.parent_id == parent_id,
                    Category.user_id == user_id,
                )
            ).order_by(Category.sort_order, Category.id)
        )
        return list(result.scalars().all())
