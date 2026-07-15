from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.category import Category
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

    async def delete_category(
        self, db: AsyncSession, category_id: int, user_id: int
    ) -> None:
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
        await db.delete(category)
        await db.commit()
