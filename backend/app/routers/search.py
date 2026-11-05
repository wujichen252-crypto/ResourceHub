from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.response import success_response
from app.models.user import User
from app.services.global_search_service import GlobalSearchService

router = APIRouter(tags=["全局搜索"])
service = GlobalSearchService()


@router.get("")
async def global_search(
    q: str = Query(..., min_length=1, max_length=100, description="搜索关键词"),
    limit: int = Query(5, ge=1, le=10, description="每种内容类型返回的最多条数"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """跨笔记与提示词的聚合搜索，供前端全局命令面板（Ctrl/Cmd + K）使用"""
    data = await service.search(db, current_user.id, q.strip(), limit)
    return success_response(data=data, msg="搜索成功")
