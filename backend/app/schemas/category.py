from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CategoryCreate(BaseModel):
    name: str
    type: str
    parent_id: int | None = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = None
    parent_id: int | None = None
    sort_order: int | None = None


class CategoryResponse(BaseModel):
    id: int
    name: str
    type: str
    parent_id: int | None
    sort_order: int
    children: list[CategoryResponse] = []

    model_config = ConfigDict(from_attributes=True)
