from sqlalchemy import select, delete as sqla_delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.category import Category
from app.models.note import Note
from app.models.prompt import Prompt
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryService:
    async def get_category_tree(
        self, db: AsyncSession, user_id: int, type: str
    ) -> list[Category]:
        result = await db.execute(
            select(Category)
            .where(Category.user_id == user_id, Category.type == type)
            .order_by(Category.sort_order)
        )
        categories = result.scalars().all()
        return self._build_tree(categories)

    def _build_tree(
        self, categories: list[Category], parent_id: int | None = None
    ) -> list[dict]:
        tree = []
        for cat in categories:
            if cat.parent_id == parent_id:
                children = self._build_tree(categories, cat.id)
                tree.append({
                    "id": cat.id,
                    "name": cat.name,
                    "type": cat.type,
                    "parent_id": cat.parent_id,
                    "sort_order": cat.sort_order,
                    "children": children,
                })
        return tree

    async def create_category(
        self, db: AsyncSession, user_id: int, data: CategoryCreate
    ) -> Category:
        category = Category(
            user_id=user_id,
            name=data.name,
            type=data.type,
            parent_id=data.parent_id,
            sort_order=data.sort_order,
        )
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category

    async def update_category(
        self, db: AsyncSession, category_id: int, user_id: int, data: CategoryUpdate
    ) -> Category:
        result = await db.execute(
            select(Category).where(
                Category.id == category_id, Category.user_id == user_id
            )
        )
        category = result.scalar_one_or_none()
        if not category:
            raise HTTPException(
                status_code=404, detail={"code": 404, "message": "分类不存在"}
            )
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(category, key, value)
        await db.commit()
        await db.refresh(category)
        return category

    async def _delete_category_and_children(
        self, db: AsyncSession, user_id: int, category_id: int, type: str
    ) -> None:
        """递归删除目录及其所有子目录与内容"""
        table = Note if type == "note" else Prompt

        # 先删子目录（递归）
        child_result = await db.execute(
            select(Category).where(
                Category.parent_id == category_id, Category.user_id == user_id
            )
        )
        children = child_result.scalars().all()
        for child in children:
            await self._delete_category_and_children(db, user_id, child.id, type)

        # 删本目录下的笔记/提示词
        await db.execute(
            sqla_delete(table).where(table.category_id == category_id, table.user_id == user_id)
        )
        # 删本目录
        await db.execute(
            sqla_delete(Category).where(Category.id == category_id, Category.user_id == user_id)
        )

    async def delete_category(
        self, db: AsyncSession, category_id: int, user_id: int
    ) -> None:
        # 检查是否存在
        result = await db.execute(
            select(Category).where(
                Category.id == category_id, Category.user_id == user_id
            )
        )
        category = result.scalar_one_or_none()
        if not category:
            raise HTTPException(
                status_code=404, detail={"code": 404, "message": "分类不存在"}
            )
        await self._delete_category_and_children(db, user_id, category_id, category.type)
        await db.commit()
