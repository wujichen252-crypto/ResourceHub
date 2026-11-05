"""ROI 看板路由：AI 成本与效果的知识资产投入产出聚合

响应结构与 app/schemas 既有风格一致（success_response 包装 dict），
聚合字段定义见 app/services/roi_service.py 模块级注释。
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.response import success_response
from app.models.user import User
from app.services.roi_service import ROI_WINDOWS, RoiService

router = APIRouter(tags=["ROI 看板"])
service = RoiService()


def _window(days: int) -> int:
    """时间窗白名单校验，非法值回退 30 天"""
    return days if days in ROI_WINDOWS else 30


@router.get("/summary")
async def roi_summary(
    days: int = Query(30, description="统计窗口（天）：7/30/90"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """总览：token、折算金额、成功率、场景/模型分布、配额水位"""
    data = await service.get_summary(db, current_user.id, _window(days))
    return success_response(data=data, msg="获取 ROI 总览成功")


@router.get("/trend")
async def roi_trend(
    days: int = Query(30, description="趋势窗口（天）：7/30/90"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """逐日趋势：调用次数、token（按场景）、折算金额、失败数"""
    data = await service.get_trend(db, current_user.id, _window(days))
    return success_response(data=data, msg="获取 ROI 趋势成功")


@router.get("/notes")
async def roi_notes(
    days: int = Query(30, description="引用统计窗口（天）：7/30/90"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """笔记级 ROI：AI 引用次数 vs 索引成本，附健康度分级"""
    data = await service.get_notes_roi(db, current_user.id, _window(days))
    return success_response(data=data, msg="获取笔记 ROI 成功")


@router.get("/prompts")
async def roi_prompts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提示词级 ROI：使用频次、质量分、优化投入与性价比排行"""
    data = await service.get_prompts_roi(db, current_user.id)
    return success_response(data=data, msg="获取提示词 ROI 成功")


@router.get("/scenes")
async def roi_scenes(
    days: int = Query(30, description="统计窗口（天）：7/30/90"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """场景四象限：成本 × 频次散点"""
    window = _window(days)
    data = await service.get_scene_quadrant(db, current_user.id, window)
    costs = await service._scene_costs(db, current_user.id, window)
    data = [{**item, "cost": round(costs.get(item["scene"], 0.0), 4)} for item in data]
    return success_response(data=data, msg="获取场景象限成功")
