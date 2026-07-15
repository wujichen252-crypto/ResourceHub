from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PromptCreate(BaseModel):
    title: str
    description: str | None = None
    content: str
    category_id: int | None = None
    variables: list[str] | None = None


class PromptUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    content: str | None = None
    category_id: int | None = None
    variables: list[str] | None = None
    is_favorite: bool | None = None


class PromptListResponse(BaseModel):
    id: int
    title: str
    description: str | None
    category_id: int | None
    category_name: str | None
    variables: list[str]
    is_favorite: bool
    usage_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptDetailResponse(BaseModel):
    id: int
    title: str
    description: str | None
    content: str
    category_id: int | None
    category_name: str | None
    variables: list[str]
    is_favorite: bool
    usage_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RenderRequest(BaseModel):
    variables: dict[str, str]


class RenderResponse(BaseModel):
    id: int
    title: str
    original_content: str
    rendered_content: str
    variables: dict[str, str]

    model_config = ConfigDict(from_attributes=True)


class PinResponse(BaseModel):
    id: int
    is_pinned: bool


class FavoriteResponse(BaseModel):
    id: int
    is_favorite: bool


class UsageResponse(BaseModel):
    id: int
    usage_count: int
