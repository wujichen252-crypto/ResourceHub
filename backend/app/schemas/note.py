import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import EmptyStr, JsonList, strip_html


class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    content: str | None = None
    # 块编辑器双轨载荷：content_json 为 TipTap JSON 文档；不传则按 markdown 单轨保存
    content_json: dict[str, Any] | None = None
    category_id: int | None = None
    tags: list[str] | None = None


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    # 显式传 None 表示切回 markdown 单轨并清空块文档；不传表示保持不变
    content_json: dict[str, Any] | None = None
    category_id: int | None = None
    tags: list[str] | None = None


class NoteBatchRequest(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=200)
    action: Literal["move", "tag", "delete"]
    # move：目标目录，null 表示移出目录
    category_id: int | None = None
    # tag：追加到现有标签之后（自动去重）
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
    visibility: str = "private"
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
    content_format: str = "markdown"
    content_json: dict[str, Any] | None = None
    category_id: int | None
    category_name: str | None = None
    tags: JsonList
    is_pinned: bool
    visibility: str = "private"
    source_username: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _decode_content_json(cls, data: Any) -> Any:
        """ORM 中 content_json 为 JSON 字符串，响应前反序列化为对象"""
        if isinstance(data, dict) and isinstance(data.get("content_json"), str):
            data = dict(data)
            try:
                data["content_json"] = json.loads(data["content_json"])
            except (ValueError, TypeError):
                data["content_json"] = None
        return data
