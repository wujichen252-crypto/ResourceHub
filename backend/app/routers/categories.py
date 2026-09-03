from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.response import success_response
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.services.category_service import CategoryService

router = APIRouter(tags=["分类"])
service = CategoryService()


@router.get("")
async def get_category_tree(
    type: str = Query(..., description="分类类型: note 或 prompt"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tree = await service.get_category_tree(db, current_user.id, type)
    return success_response(
        data=tree,
        msg="获取分类树成功",
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    category = await service.create_category(db, current_user.id, data)
    return success_response(
        data={
            "id": category.id,
            "name": category.name,
            "type": category.type,
            "parent_id": category.parent_id,
            "sort_order": category.sort_order,
            "created_at": category.created_at.isoformat() if category.created_at else None,
        },
        msg="创建分类成功",
        code=201,
    )


@router.put("/{category_id}")
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    category = await service.update_category(db, category_id, current_user.id, data)
    return success_response(
        data={
            "id": category.id,
            "name": category.name,
            "type": category.type,
            "parent_id": category.parent_id,
            "sort_order": category.sort_order,
        },
        msg="更新分类成功",
    )


@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.delete_category(db, category_id, current_user.id)
    return success_response(msg="删除分类成功")
