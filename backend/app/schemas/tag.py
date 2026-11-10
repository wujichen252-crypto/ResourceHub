from typing import Literal

from pydantic import BaseModel, Field

TagScope = Literal["note", "prompt"]


class TagRenameRequest(BaseModel):
    scope: TagScope
    old_name: str = Field(..., min_length=1, max_length=50)
    new_name: str = Field(..., min_length=1, max_length=50)


class TagMergeRequest(BaseModel):
    scope: TagScope
    sources: list[str] = Field(..., min_length=1, max_length=50)
    target: str = Field(..., min_length=1, max_length=50)


class TagCount(BaseModel):
    name: str
    count: int
