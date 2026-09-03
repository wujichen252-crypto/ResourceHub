import json
import re
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.prompt import Prompt, PromptVersion, PromptPreset, PromptUsageLog
import difflib
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
        tag: str | None = None,
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
        if tag:
            query = query.where(Prompt.tags.ilike(f"%{tag}%"))

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
            tags=json.dumps(data.tags, ensure_ascii=False) if data.tags else None,
        )
        db.add(prompt)
        await db.commit()
        await db.refresh(prompt)
        # 创建初始版本 v1
        await self._create_version_snapshot(db, prompt, message=data.message or "初始版本")
        await db.commit()
        return prompt

    async def update_prompt(
        self, db: AsyncSession, prompt_id: int, user_id: int, data: PromptUpdate
    ) -> Prompt:
        prompt = await self.get_prompt(db, prompt_id, user_id)
        update_data = data.model_dump(exclude_unset=True)
        msg = update_data.pop("message", None)  # 提取 message，不写入 prompt 本身
        # 内容变更时自动快照版本
        content_changed = "content" in update_data and data.content != prompt.content
        if content_changed:
            await self._create_version_snapshot(db, prompt, message=msg or "更新内容")
        elif msg:
            # 即使内容没变，如果有 commit message 也快照
            await self._create_version_snapshot(db, prompt, message=msg)
        if "variables" in update_data:
            update_data["variables"] = (
                json.dumps(data.variables, ensure_ascii=False) if data.variables else None
            )
        if "tags" in update_data:
            update_data["tags"] = (
                json.dumps(data.tags, ensure_ascii=False) if data.tags else None
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
        # 记录使用日志（用于用量分析）
        log = PromptUsageLog(prompt_id=prompt_id, user_id=user_id)
        db.add(log)
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

    # ── Version History ──

    async def _create_version_snapshot(self, db: AsyncSession, prompt: Prompt, message: str | None = None) -> None:
        """保存当前 prompt 的快照"""
        max_ver = await db.execute(
            select(func.max(PromptVersion.version_number)).where(
                PromptVersion.prompt_id == prompt.id
            )
        )
        next_ver = (max_ver.scalar() or 0) + 1
        version = PromptVersion(
            prompt_id=prompt.id,
            version_number=next_ver,
            title=prompt.title,
            description=prompt.description,
            content=prompt.content,
            variables=prompt.variables,
            tags=prompt.tags,
            message=message,
            branch_name="main",
        )
        db.add(version)

    async def get_versions(
        self, db: AsyncSession, prompt_id: int, user_id: int
    ) -> list[PromptVersion]:
        prompt = await self.get_prompt(db, prompt_id, user_id)
        result = await db.execute(
            select(PromptVersion)
            .where(PromptVersion.prompt_id == prompt_id)
            .order_by(PromptVersion.version_number.desc())
        )
        return result.scalars().all()

    async def get_version(
        self, db: AsyncSession, prompt_id: int, version_id: int, user_id: int
    ) -> PromptVersion:
        prompt = await self.get_prompt(db, prompt_id, user_id)
        result = await db.execute(
            select(PromptVersion).where(
                PromptVersion.id == version_id,
                PromptVersion.prompt_id == prompt_id,
            )
        )
        version = result.scalar_one_or_none()
        if not version:
            raise HTTPException(status_code=404, detail={"code": 404, "message": "版本不存在"})
        return version

    async def restore_version(
        self, db: AsyncSession, prompt_id: int, version_id: int, user_id: int
    ) -> Prompt:
        prompt = await self.get_prompt(db, prompt_id, user_id)
        version = await self.get_version(db, prompt_id, version_id, user_id)
        # 先快照当前状态（防止误操作丢数据）
        await self._create_version_snapshot(db, prompt)
        # 恢复版本数据
        prompt.title = version.title
        prompt.description = version.description
        prompt.content = version.content
        prompt.variables = version.variables
        prompt.tags = version.tags
        await db.commit()
        await db.refresh(prompt)
        return prompt

    # ── Diff ──

    def _version_to_dict(self, version) -> dict:
        return {
            "id": version.id,
            "prompt_id": version.prompt_id,
            "version_number": version.version_number,
            "title": version.title,
            "description": version.description or "",
            "content": version.content,
            "variables": json.loads(version.variables) if version.variables else [],
            "tags": json.loads(version.tags) if version.tags else [],
            "message": version.message or "",
            "labels": json.loads(version.labels) if version.labels else [],
            "branch_name": version.branch_name,
            "created_at": version.created_at.isoformat() if version.created_at else None,
        }

    async def diff_versions(
        self, db: AsyncSession, prompt_id: int, version_id_1: int, version_id_2: int, user_id: int
    ) -> dict:
        v1 = await self.get_version(db, prompt_id, version_id_1, user_id)
        v2 = await self.get_version(db, prompt_id, version_id_2, user_id)

        lines1 = (v1.content or "").splitlines(keepends=True)
        lines2 = (v2.content or "").splitlines(keepends=True)
        diff_result = []
        for line in difflib.unified_diff(lines1, lines2, n=9999):
            if line.startswith("---") or line.startswith("+++"):
                continue
            if line.startswith("@@"):
                continue
            if line.startswith("-"):
                diff_result.append({"type": "delete", "value": line[1:].rstrip("\n")})
            elif line.startswith("+"):
                diff_result.append({"type": "insert", "value": line[1:].rstrip("\n")})
            else:
                diff_result.append({"type": "equal", "value": line.rstrip("\n")})

        return {
            "v1": self._version_to_dict(v1),
            "v2": self._version_to_dict(v2),
            "diffs": diff_result,
        }

    # ── Labels ──

    async def update_labels(
        self, db: AsyncSession, prompt_id: int, version_id: int, user_id: int, labels: list[str]
    ) -> PromptVersion:
        version = await self.get_version(db, prompt_id, version_id, user_id)
        version.labels = json.dumps(labels, ensure_ascii=False) if labels else None
        await db.commit()
        await db.refresh(version)
        return version

    # ── Presets ──

    async def get_presets(
        self, db: AsyncSession, prompt_id: int, user_id: int
    ) -> list[PromptPreset]:
        await self.get_prompt(db, prompt_id, user_id)
        result = await db.execute(
            select(PromptPreset).where(PromptPreset.prompt_id == prompt_id)
            .order_by(PromptPreset.created_at)
        )
        return result.scalars().all()

    async def create_preset(
        self, db: AsyncSession, prompt_id: int, user_id: int, name: str, values: dict[str, str]
    ) -> PromptPreset:
        await self.get_prompt(db, prompt_id, user_id)
        preset = PromptPreset(
            prompt_id=prompt_id,
            name=name,
            values=json.dumps(values, ensure_ascii=False),
        )
        db.add(preset)
        await db.commit()
        await db.refresh(preset)
        return preset

    async def delete_preset(
        self, db: AsyncSession, preset_id: int, user_id: int
    ) -> None:
        result = await db.execute(
            select(PromptPreset).where(PromptPreset.id == preset_id)
        )
        preset = result.scalar_one_or_none()
        if not preset:
            raise HTTPException(status_code=404, detail={"code": 404, "message": "预设不存在"})
        # Verify ownership through the prompt
        await self.get_prompt(db, preset.prompt_id, user_id)
        await db.delete(preset)
        await db.commit()

    def _render_template(self, template: str, variables: dict[str, str]) -> str:
        def replace_var(match):
            var_name = match.group(1).strip()
            return variables.get(var_name, match.group(0))
        return re.sub(r'\{\{(\w+)\}\}', replace_var, template)
