import json

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.category import Category
from app.schemas.prompt import (
    PromptCreate,
    PromptUpdate,
    RenderRequest,
    RenderResponse,
)
from app.services.prompt_service import PromptService

router = APIRouter(tags=["提示词"])
service = PromptService()


def _format_prompt(prompt, category_name: str | None = None, include_content: bool = False) -> dict:
    variables = json.loads(prompt.variables) if prompt.variables else []
    result = {
        "id": prompt.id,
        "title": prompt.title,
        "description": prompt.description or "",
        "category_id": prompt.category_id,
        "category_name": category_name,
        "variables": variables,
        "is_favorite": prompt.is_favorite,
        "usage_count": prompt.usage_count,
        "created_at": prompt.created_at.isoformat() if prompt.created_at else None,
        "updated_at": prompt.updated_at.isoformat() if prompt.updated_at else None,
    }
    if include_content:
        result["content"] = prompt.content
    return result


@router.get("")
async def list_prompts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_id: int | None = None,
    is_favorite: bool | None = None,
    search: str | None = None,
    sort_by: str = "created_at",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prompts, total = await service.get_prompts(
        db, current_user.id, page, page_size,
        category_id, is_favorite, search, sort_by,
    )
    items = []
    for p in prompts:
        cat_name = None
        if p.category_id:
            cat = await db.get(Category, p.category_id)
            cat_name = cat.name if cat else None
        items.append(_format_prompt(p, cat_name))

    return {"data": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{prompt_id}")
async def get_prompt(
    prompt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prompt = await service.get_prompt(db, prompt_id, current_user.id)
    cat_name = None
    if prompt.category_id:
        cat = await db.get(Category, prompt.category_id)
        cat_name = cat.name if cat else None
    return {"data": _format_prompt(prompt, cat_name, include_content=True)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_prompt(
    data: PromptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prompt = await service.create_prompt(db, current_user.id, data)
    cat_name = None
    if prompt.category_id:
        cat = await db.get(Category, prompt.category_id)
        cat_name = cat.name if cat else None
    return {"data": _format_prompt(prompt, cat_name, include_content=True)}


@router.put("/{prompt_id}")
async def update_prompt(
    prompt_id: int,
    data: PromptUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prompt = await service.update_prompt(db, prompt_id, current_user.id, data)
    cat_name = None
    if prompt.category_id:
        cat = await db.get(Category, prompt.category_id)
        cat_name = cat.name if cat else None
    return {"data": _format_prompt(prompt, cat_name, include_content=True)}


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.delete_prompt(db, prompt_id, current_user.id)


@router.post("/{prompt_id}/render")
async def render_prompt(
    prompt_id: int,
    data: RenderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await service.render_prompt(db, prompt_id, current_user.id, data.variables)
    return {"data": result.model_dump()}


@router.post("/{prompt_id}/use")
async def record_usage(
    prompt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prompt = await service.record_usage(db, prompt_id, current_user.id)
    return {"data": {"id": prompt.id, "usage_count": prompt.usage_count}}


@router.put("/{prompt_id}/favorite")
async def toggle_favorite(
    prompt_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prompt = await service.toggle_favorite(db, prompt_id, current_user.id)
    return {"data": {"id": prompt.id, "is_favorite": prompt.is_favorite}}
