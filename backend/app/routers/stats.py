from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.response import success_response
from app.models.user import User
from app.services.stats_service import StatsService

router = APIRouter(tags=["统计"])
service = StatsService()


@router.get("/overview")
async def get_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """工作台统计总览：标签云 / 创作趋势 / 分类分布 / 使用热力图"""
    data = await service.get_overview(db, current_user.id)
    return success_response(data=data, msg="获取统计成功")
