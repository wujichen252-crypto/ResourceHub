from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    id: int
    title: str
    content_preview: str
    category_id: int | None
    category_name: str | None
    tags: list[str]
    is_pinned: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

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
    content: str
    category_id: int | None
    category_name: str | None
    tags: list[str]
    is_pinned: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
