import json
import re
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.prompt import Prompt
from app.schemas.prompt import (
    PromptCreate, PromptUpdate, RenderResponse
)


class PromptService:
    async def get_prompts(
        self, db: AsyncSession, user_id: int,
        page: int = 1, page_size: int = 20,
        category_id: int | None = None,
        is_favorite: bool | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
    ):
        query = select(Prompt).where(Prompt.user_id == user_id)

        if category_id is not None:
            query = query.where(Prompt.category_id == category_id)
        if is_favorite is not None:
            query = query.where(Prompt.is_favorite == is_favorite)
        if search:
            query = query.where(
                or_(
                    Prompt.title.ilike(f"%{search}%"),
                    Prompt.description.ilike(f"%{search}%"),
                )
            )

        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar() or 0

        if sort_by == "usage_count":
            query = query.order_by(Prompt.usage_count.desc())
        else:
            query = query.order_by(Prompt.updated_at.desc())

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        prompts = result.scalars().all()
        return prompts, total

    async def get_prompt(self, db: AsyncSession, prompt_id: int, user_id: int) -> Prompt:
        result = await db.execute(
            select(Prompt).where(Prompt.id == prompt_id, Prompt.user_id == user_id)
        )
        prompt = result.scalar_one_or_none()
        if not prompt:
            raise HTTPException(status_code=404, detail={"code": 404, "message": "提示词不存在"})
        return prompt

    async def create_prompt(
        self, db: AsyncSession, user_id: int, data: PromptCreate
    ) -> Prompt:
        prompt = Prompt(
            user_id=user_id,
            title=data.title,
            description=data.description,
            content=data.content,
            category_id=data.category_id,
            variables=json.dumps(data.variables, ensure_ascii=False) if data.variables else None,
        )
        db.add(prompt)
        await db.commit()
        await db.refresh(prompt)
        return prompt

    async def update_prompt(
        self, db: AsyncSession, prompt_id: int, user_id: int, data: PromptUpdate
    ) -> Prompt:
        prompt = await self.get_prompt(db, prompt_id, user_id)
        update_data = data.model_dump(exclude_unset=True)
        if "variables" in update_data:
            update_data["variables"] = (
                json.dumps(data.variables, ensure_ascii=False) if data.variables else None
            )
        for key, value in update_data.items():
            setattr(prompt, key, value)
        await db.commit()
        await db.refresh(prompt)
        return prompt

    async def delete_prompt(self, db: AsyncSession, prompt_id: int, user_id: int) -> None:
        prompt = await self.get_prompt(db, prompt_id, user_id)
        await db.delete(prompt)
        await db.commit()

    async def render_prompt(
        self, db: AsyncSession, prompt_id: int, user_id: int, variables: dict[str, str]
    ) -> RenderResponse:
        prompt = await self.get_prompt(db, prompt_id, user_id)
        rendered = self._render_template(prompt.content, variables)
        return RenderResponse(
            id=prompt.id,
            title=prompt.title,
            original_content=prompt.content,
            rendered_content=rendered,
            variables=variables,
        )

    async def record_usage(
        self, db: AsyncSession, prompt_id: int, user_id: int
    ) -> Prompt:
        prompt = await self.get_prompt(db, prompt_id, user_id)
        prompt.usage_count += 1
        await db.commit()
        await db.refresh(prompt)
        return prompt

    async def toggle_favorite(
        self, db: AsyncSession, prompt_id: int, user_id: int
    ) -> Prompt:
        prompt = await self.get_prompt(db, prompt_id, user_id)
        prompt.is_favorite = not prompt.is_favorite
        await db.commit()
        await db.refresh(prompt)
        return prompt

    def _render_template(self, template: str, variables: dict[str, str]) -> str:
        def replace_var(match):
            var_name = match.group(1).strip()
            return variables.get(var_name, match.group(0))
        return re.sub(r'\{\{(\w+)\}\}', replace_var, template)
