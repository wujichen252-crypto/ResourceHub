from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.response import success_response
from app.models.user import User
from app.schemas.tag import TagMergeRequest, TagRenameRequest, TagScope
from app.services.tag_service import tag_service

router = APIRouter(tags=["标签"])


@router.get("")
async def list_tags(
    scope: TagScope = "note",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = await tag_service.list_tags(db, current_user.id, scope)
    return success_response(data={"items": items}, msg="获取标签列表成功")


@router.post("/rename")
async def rename_tag(
    data: TagRenameRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated = await tag_service.rename_tag(
        db, current_user.id, data.scope, data.old_name, data.new_name
    )
    return success_response(data={"updated": updated}, msg=f"已更新 {updated} 条记录")


@router.post("/merge")
async def merge_tags(
    data: TagMergeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated = await tag_service.merge_tags(
        db, current_user.id, data.scope, data.sources, data.target
    )
    return success_response(data={"updated": updated}, msg=f"已合并 {updated} 条记录")


@router.delete("")
async def delete_tag(
    name: str = Query(..., min_length=1, max_length=50),
    scope: TagScope = "note",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updated = await tag_service.delete_tag(db, current_user.id, scope, name)
    return success_response(data={"updated": updated}, msg=f"已清理 {updated} 条记录")
