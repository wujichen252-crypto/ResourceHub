from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.core.response import success_response
from app.models.user import User
from app.schemas.note_template import (
    NoteTemplateCreate,
    NoteTemplateResponse,
    NoteTemplateUpdate,
)
from app.services.note_template_service import note_template_service

router = APIRouter(tags=["笔记模板"])


def _out(template) -> dict:
    return NoteTemplateResponse.model_validate(template).model_dump()


@router.get("")
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    templates = await note_template_service.list_templates(db, current_user.id)
    return success_response(
        data={"items": [_out(t) for t in templates]}, msg="获取模板列表成功"
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_template(
    data: NoteTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = await note_template_service.create_template(db, current_user.id, data)
    return success_response(data=_out(template), msg="创建模板成功", code=201)


@router.put("/{template_id}")
async def update_template(
    template_id: int,
    data: NoteTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = await note_template_service.update_template(
        db, template_id, current_user.id, data
    )
    return success_response(data=_out(template), msg="更新模板成功")


@router.delete("/{template_id}")
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await note_template_service.delete_template(db, template_id, current_user.id)
    return success_response(msg="删除模板成功")
