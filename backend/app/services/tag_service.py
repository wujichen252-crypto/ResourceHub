"""
标签管理：笔记与提示词的标签都存于 JSON 数组字符串列，没有独立标签表。
重命名 / 合并 / 删除只能全量扫描当前用户的行后改数组，数据量在个人工具量级可接受。
"""

import json
from collections.abc import Callable

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode
from app.models.note import Note
from app.models.prompt import Prompt

_SCOPE_MODELS = {"note": Note, "prompt": Prompt}


def parse_tags(raw: str | None) -> list[str]:
    """解析标签 JSON 列，坏数据按空标签处理，避免单个损坏行阻断整个列表"""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    return [str(tag).strip() for tag in data if str(tag).strip()]


def dump_tags(tags: list[str]) -> str | None:
    return json.dumps(tags, ensure_ascii=False) if tags else None


def _dedupe(tags: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            result.append(tag)
    return result


class TagService:
    def _model(self, scope: str):
        model = _SCOPE_MODELS.get(scope)
        if model is None:
            raise HTTPException(
                status_code=400,
                detail={"code": ErrorCode.VALIDATION_ERROR, "message": "标签范围无效"},
            )
        return model

    async def list_tags(
        self, db: AsyncSession, user_id: int, scope: str
    ) -> list[dict]:
        model = self._model(scope)
        result = await db.execute(
            select(model.tags).where(model.user_id == user_id)
        )
        counter: dict[str, int] = {}
        for raw in result.scalars().all():
            for tag in set(parse_tags(raw)):
                counter[tag] = counter.get(tag, 0) + 1
        return [
            {"name": name, "count": count}
            for name, count in sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))
        ]

    async def _remap(
        self,
        db: AsyncSession,
        user_id: int,
        scope: str,
        mapper: Callable[[list[str]], list[str]],
    ) -> int:
        model = self._model(scope)
        result = await db.execute(
            select(model).where(model.user_id == user_id)
        )
        updated = 0
        for row in result.scalars().all():
            tags = parse_tags(row.tags)
            mapped = _dedupe(mapper(tags))
            if mapped != tags:
                row.tags = dump_tags(mapped)
                updated += 1
        if updated:
            await db.commit()
        return updated

    async def rename_tag(
        self, db: AsyncSession, user_id: int, scope: str, old_name: str, new_name: str
    ) -> int:
        old_name, new_name = old_name.strip(), new_name.strip()
        if not old_name or not new_name:
            raise HTTPException(
                status_code=400,
                detail={"code": ErrorCode.VALIDATION_ERROR, "message": "标签名不能为空"},
            )
        return await self._remap(
            db, user_id, scope,
            lambda tags: [new_name if tag == old_name else tag for tag in tags],
        )

    async def merge_tags(
        self, db: AsyncSession, user_id: int, scope: str, sources: list[str], target: str
    ) -> int:
        target = target.strip()
        source_set = {name.strip() for name in sources if name.strip()}
        if not target or not source_set:
            raise HTTPException(
                status_code=400,
                detail={"code": ErrorCode.VALIDATION_ERROR, "message": "标签名不能为空"},
            )
        return await self._remap(
            db, user_id, scope,
            lambda tags: [target if tag in source_set else tag for tag in tags],
        )

    async def delete_tag(
        self, db: AsyncSession, user_id: int, scope: str, name: str
    ) -> int:
        name = name.strip()
        if not name:
            raise HTTPException(
                status_code=400,
                detail={"code": ErrorCode.VALIDATION_ERROR, "message": "标签名不能为空"},
            )
        return await self._remap(
            db, user_id, scope,
            lambda tags: [tag for tag in tags if tag != name],
        )


tag_service = TagService()
