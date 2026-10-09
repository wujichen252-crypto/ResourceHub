from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.response import orm_to_dict, success_response
from app.models.user import User
from app.schemas.prompt import (
    PromptCreate,
    PromptDetailResponse,
    PromptListResponse,
    PromptUpdate,
    PromptVersionResponse,
    PresetCreate,
    PresetResponse,
    RenderRequest,
    LabelUpdateRequest,
)
from app.services.category_service import CategoryService
from app.services.prompt_service import PromptService
from app.services.prompt_analytics_service import PromptAnalyticsService

router = APIRouter(tags=["提示词"])
service = PromptService()
analytics_service = PromptAnalyticsService()
category_service = CategoryService()


def _prompt_list_out(prompt, category_name: str | None = None) -> dict:
    return PromptListResponse.model_validate(
        {**orm_to_dict(prompt), "category_name": category_name}
    ).model_dump()


def _prompt_detail_out(prompt, category_name: str | None = None) -> dict:
    return PromptDetailResponse.model_validate(
        {**orm_to_dict(prompt), "category_name": category_name}
    ).model_dump()


def _version_out(version) -> dict:
    return PromptVersionResponse.model_validate(orm_to_dict(version)).model_dump()


def _preset_out(preset) -> dict:
    return PresetResponse.model_validate(orm_to_dict(preset)).model_dump()


async def _single_category_name(db: AsyncSession, category_id: int | None) -> str | None:
    if category_id is None:
        return None
    names = await category_service.get_name_map(db, {category_id})
    return names.get(category_id)


@router.get("")
async def list_prompts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: int | None = None,
    is_favorite: bool | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    tag: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prompts, total = await service.get_prompts(
        db, current_user.id, page, page_size,
        category_id, is_favorite, search, sort_by, tag,
    )
    # 一次批量查询分类名，避免逐条 get 造成 N+1
    names = await category_service.get_name_map(
        db, {p.category_id for p in prompts if p.category_id is not None}
    )
    items = [_prompt_list_out(p, names.get(p.category_id)) for p in prompts]

    return success_response(
        data={
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        },
        msg="获取提示词列表成功",
    )


@router.get("/analytics/usage")
async def get_usage_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    summary = await analytics_service.get_summary(db, current_user.id)
    return success_response(
        data=summary,
        msg="获取使用统计成功",
    )


@router.get("/{prompt_id}")
async def get_prompt(
    prompt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prompt = await service.get_prompt(db, prompt_id, current_user.id)
    return success_response(
        data=_prompt_detail_out(prompt, await _single_category_name(db, prompt.category_id)),
        msg="获取提示词详情成功",
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_prompt(
    data: PromptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prompt = await service.create_prompt(db, current_user.id, data)
    return success_response(
        data=_prompt_detail_out(prompt, await _single_category_name(db, prompt.category_id)),
        msg="创建提示词成功",
        code=201,
    )


@router.put("/{prompt_id}")
async def update_prompt(
    prompt_id: int,
    data: PromptUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prompt = await service.update_prompt(db, prompt_id, current_user.id, data)
    return success_response(
        data=_prompt_detail_out(prompt, await _single_category_name(db, prompt.category_id)),
        msg="更新提示词成功",
    )


# ── Presets ──


@router.get("/{prompt_id}/presets")
async def list_presets(
    prompt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    presets = await service.get_presets(db, prompt_id, current_user.id)
    return success_response(
        data=[_preset_out(p) for p in presets],
        msg="获取预设列表成功",
    )


@router.post("/{prompt_id}/presets", status_code=status.HTTP_201_CREATED)
async def create_preset(
    prompt_id: int,
    data: PresetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    preset = await service.create_preset(db, prompt_id, current_user.id, data.name, data.values)
    return success_response(
        data=_preset_out(preset),
        msg="创建预设成功",
        code=201,
    )


@router.delete("/presets/{preset_id}")
async def delete_preset(
    preset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.delete_preset(db, preset_id, current_user.id)
    return success_response(msg="删除预设成功")


@router.delete("/{prompt_id}")
async def delete_prompt(
    prompt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.delete_prompt(db, prompt_id, current_user.id)
    return success_response(msg="删除提示词成功")


@router.post("/{prompt_id}/render")
async def render_prompt(
    prompt_id: int,
    data: RenderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await service.render_prompt(db, prompt_id, current_user.id, data.variables)
    return success_response(
        data=result.model_dump(),
        msg="渲染提示词成功",
    )


@router.post("/{prompt_id}/use")
async def record_usage(
    prompt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prompt = await service.record_usage(db, prompt_id, current_user.id)
    return success_response(
        data={"id": prompt.id, "usage_count": prompt.usage_count},
        msg="记录使用成功",
    )


@router.put("/{prompt_id}/favorite")
async def toggle_favorite(
    prompt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prompt = await service.toggle_favorite(db, prompt_id, current_user.id)
    return success_response(
        data={"id": prompt.id, "is_favorite": prompt.is_favorite},
        msg="切换收藏状态成功",
    )


# ── Version History ──


@router.get("/{prompt_id}/versions")
async def list_versions(
    prompt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    versions = await service.get_versions(db, prompt_id, current_user.id)
    return success_response(
        data=[_version_out(v) for v in versions],
        msg="获取版本列表成功",
    )


@router.get("/{prompt_id}/versions/{version_id}")
async def get_version(
    prompt_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    version = await service.get_version(db, prompt_id, version_id, current_user.id)
    return success_response(
        data=_version_out(version),
        msg="获取版本详情成功",
    )


@router.post("/{prompt_id}/versions/{version_id}/restore")
async def restore_version(
    prompt_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prompt = await service.restore_version(db, prompt_id, version_id, current_user.id)
    return success_response(
        data=_prompt_detail_out(prompt, await _single_category_name(db, prompt.category_id)),
        msg="恢复版本成功",
    )


@router.get("/{prompt_id}/versions/{version_id}/diff")
async def diff_versions(
    prompt_id: int,
    version_id: int,
    target_version_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await service.diff_versions(
        db, prompt_id, version_id, target_version_id, current_user.id
    )
    return success_response(data=result, msg="获取差异成功")


@router.put("/{prompt_id}/versions/{version_id}/labels")
async def update_labels(
    prompt_id: int,
    version_id: int,
    data: LabelUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    version = await service.update_labels(
        db, prompt_id, version_id, current_user.id, data.labels
    )
    return success_response(data=_version_out(version), msg="更新标签成功")
