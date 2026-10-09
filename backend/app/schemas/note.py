from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import EmptyStr, JsonList, strip_html


class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str | None = None
    category_id: int | None = None
    tags: list[str] | None = None


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    category_id: int | None = None
    tags: list[str] | None = None


class NoteListResponse(BaseModel):
    """列表项：不返回全文，content_preview 由 content 列派生（剥 HTML→截断→换行替换）"""
    id: int
    title: str
    content_preview: str
    category_id: int | None
    category_name: str | None = None
    tags: JsonList
    is_pinned: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _derive_preview(cls, data: Any) -> Any:
        if isinstance(data, dict) and "content_preview" not in data and "content" in data:
            data = dict(data)
            data["content_preview"] = strip_html(data.get("content") or "")[:200].replace("\n", " ")
        return data

    @field_validator("content_preview", mode="before")
    @classmethod
    def generate_content_preview(cls, v: str | None) -> str:
        if not v:
            return ""
        preview = v[:200].replace("\n", " ").replace("\r", "")
        return preview


class NoteDetailResponse(BaseModel):
    id: int
    title: str
    content: EmptyStr
    category_id: int | None
    category_name: str | None = None
    tags: JsonList
    is_pinned: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
