"""资源广场（分享）请求/响应模式"""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import EmptyStr, JsonList, strip_html

ContentType = Literal["note", "prompt"]


class PlazaActionRequest(BaseModel):
    """发布/取消发布/fork 的通用请求体"""
    type: ContentType
    id: int


class PlazaItemResponse(BaseModel):
    """广场列表项：不返回全文，content_preview 由 content 列派生"""
    id: int
    type: str
    title: str
    content_preview: str
    tags: JsonList
    author_username: str
    author_avatar: str | None = None
    published_at: datetime | None = None
    updated_at: datetime
    forked_from: str | None = None  # 来自 @xxx（若本身是 fork 副本）
    # ── 笔记互动（prompt 类型保持默认值）──
    like_count: int = 0
    favorite_count: int = 0
    liked: bool = False
    favorited: bool = False

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def _derive_preview(cls, data: Any) -> Any:
        if isinstance(data, dict) and "content_preview" not in data and "content" in data:
            data = dict(data)
            data["content_preview"] = strip_html(data.get("content") or "")[:200].replace("\n", " ")
        return data


class PlazaDetailResponse(BaseModel):
    """广场详情：返回全文（只读）"""
    id: int
    type: str
    title: str
    description: str | None = None
    content: EmptyStr
    tags: JsonList
    variables: JsonList = []
    author_id: int
    author_username: str
    author_avatar: str | None = None
    usage_count: int | None = None
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    forked_from: str | None = None
    # ── 笔记互动（prompt 类型保持默认值）──
    like_count: int = 0
    favorite_count: int = 0
    liked: bool = False
    favorited: bool = False

    model_config = ConfigDict(from_attributes=True)
