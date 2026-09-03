from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PromptCreate(BaseModel):
    title: str
    description: str | None = None
    content: str
    category_id: int | None = None
    variables: list[str] | None = None
    tags: list[str] | None = None
    message: str | None = None


class PromptUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    content: str | None = None
    category_id: int | None = None
    variables: list[str] | None = None
    tags: list[str] | None = None
    is_favorite: bool | None = None
    message: str | None = None


class PromptListResponse(BaseModel):
    id: int
    title: str
    description: str | None
    category_id: int | None
    category_name: str | None
    variables: list[str]
    tags: list[str] = []
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
    tags: list[str] = []
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


class PresetCreate(BaseModel):
    name: str
    values: dict[str, str]


class PresetResponse(BaseModel):
    id: int
    prompt_id: int
    name: str
    values: dict[str, str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PresetUpdate(BaseModel):
    name: str | None = None
    values: dict[str, str] | None = None


class PromptVersionResponse(BaseModel):
    id: int
    prompt_id: int
    version_number: int
    title: str
    description: str | None
    content: str
    variables: list[str] = []
    tags: list[str] = []
    message: str | None = None
    labels: list[str] = []
    branch_name: str = "main"
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiffSegment(BaseModel):
    type: str  # "equal" | "insert" | "delete"
    value: str


class DiffResponse(BaseModel):
    v1: PromptVersionResponse
    v2: PromptVersionResponse
    diffs: list[DiffSegment]


class LabelUpdateRequest(BaseModel):
    labels: list[str]
