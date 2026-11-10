import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field
from typing_extensions import Annotated

from app.schemas.common import EmptyStr, JsonList


def _decode_block_doc(value: Any) -> Any:
    """ORM 上的块文档是 JSON 字符串；坏数据回落 None，不让单条模板拖挂整个列表"""
    if value is None or value == "":
        return None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            return None
    return value if isinstance(value, dict) else None


class NoteTemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    content: str | None = None
    content_json: dict[str, Any] | None = None
    tags: list[str] | None = None
    category_id: int | None = None


class NoteTemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    content: str | None = None
    content_json: dict[str, Any] | None = None
    tags: list[str] | None = None
    category_id: int | None = None


class NoteTemplateResponse(BaseModel):
    id: int
    name: str
    content: EmptyStr
    content_format: str = "markdown"
    content_json: Annotated[dict[str, Any] | None, BeforeValidator(_decode_block_doc)] = None
    tags: JsonList
    category_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
