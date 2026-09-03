"""
数据访问层基类
提供通用的 CRUD 操作封装
"""

from typing import Any, Generic, Type, TypeVar

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

ModelType = TypeVar("ModelType", bound=DeclarativeBase)


class BaseRepository(Generic[ModelType]):
    """
    数据访问层基类
    封装通用的 CRUD 操作，Service 层通过 Repository 访问数据库
    """

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get_by_id(self, db: AsyncSession, id: Any) -> ModelType | None:
        """根据 ID 获取单条记录"""
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, obj_in: dict[str, Any]) -> ModelType:
        """创建新记录"""
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self, db: AsyncSession, db_obj: ModelType, obj_in: dict[str, Any]
    ) -> ModelType:
        """更新记录"""
        for field, value in obj_in.items():
            if value is not None:
                setattr(db_obj, field, value)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, db_obj: ModelType) -> None:
        """删除记录"""
        await db.delete(db_obj)
        await db.commit()

    async def count(self, db: AsyncSession, **filters) -> int:
        """统计符合条件的记录数"""
        query = select(func.count()).select_from(self.model)
        for field, value in filters.items():
            if value is not None:
                query = query.where(getattr(self.model, field) == value)
        result = await db.execute(query)
        return result.scalar_one()
