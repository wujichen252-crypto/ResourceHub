from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
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
    return {"data": tree}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    category = await service.create_category(db, current_user.id, data)
    return {
        "data": {
            "id": category.id,
            "name": category.name,
            "type": category.type,
            "parent_id": category.parent_id,
            "sort_order": category.sort_order,
            "created_at": category.created_at.isoformat() if category.created_at else None,
        }
    }


@router.put("/{category_id}")
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    category = await service.update_category(db, category_id, current_user.id, data)
    return {
        "data": {
            "id": category.id,
            "name": category.name,
            "type": category.type,
            "parent_id": category.parent_id,
            "sort_order": category.sort_order,
        }
    }


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.delete_category(db, category_id, current_user.id)
