import json

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode
from app.models.note import NoteTemplate
from app.schemas.note_template import NoteTemplateCreate, NoteTemplateUpdate
from app.services.note_service import _ensure_block_ids
from app.services.tag_service import dump_tags


def _apply_track(
    template: NoteTemplate, content: str | None, content_json: dict | None
) -> None:
    """与笔记一致的双轨：有块文档时 JSON 权威，否则回落 markdown 单轨"""
    if content_json:
        template.content_format = "json"
        template.content_json = json.dumps(
            _ensure_block_ids(content_json), ensure_ascii=False
        )
        template.content = content
    else:
        template.content_format = "markdown"
        template.content_json = None
        template.content = content


class NoteTemplateService:
    async def list_templates(
        self, db: AsyncSession, user_id: int
    ) -> list[NoteTemplate]:
        result = await db.execute(
            select(NoteTemplate)
            .where(NoteTemplate.user_id == user_id)
            .order_by(NoteTemplate.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_template(
        self, db: AsyncSession, template_id: int, user_id: int
    ) -> NoteTemplate:
        result = await db.execute(
            select(NoteTemplate).where(
                NoteTemplate.id == template_id, NoteTemplate.user_id == user_id
            )
        )
        template = result.scalar_one_or_none()
        if not template:
            raise HTTPException(
                status_code=404,
                detail={"code": ErrorCode.NOT_FOUND, "message": "模板不存在"},
            )
        return template

    async def create_template(
        self, db: AsyncSession, user_id: int, data: NoteTemplateCreate
    ) -> NoteTemplate:
        template = NoteTemplate(
            user_id=user_id,
            name=data.name.strip(),
            category_id=data.category_id,
            tags=dump_tags([t.strip() for t in (data.tags or []) if t.strip()]),
        )
        _apply_track(template, data.content, data.content_json)
        db.add(template)
        await db.commit()
        await db.refresh(template)
        return template

    async def update_template(
        self,
        db: AsyncSession,
        template_id: int,
        user_id: int,
        data: NoteTemplateUpdate,
    ) -> NoteTemplate:
        template = await self.get_template(db, template_id, user_id)
        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data:
            template.name = data.name.strip()  # type: ignore[union-attr]
        if "tags" in update_data:
            template.tags = dump_tags([t.strip() for t in (data.tags or []) if t.strip()])
        if "category_id" in update_data:
            template.category_id = update_data["category_id"]
        if "content" in update_data or "content_json" in update_data:
            _apply_track(
                template,
                update_data.pop("content", template.content),
                update_data.pop("content_json", None),
            )
        await db.commit()
        await db.refresh(template)
        return template

    async def delete_template(
        self, db: AsyncSession, template_id: int, user_id: int
    ) -> None:
        template = await self.get_template(db, template_id, user_id)
        await db.delete(template)
        await db.commit()


note_template_service = NoteTemplateService()
