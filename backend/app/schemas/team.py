from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TeamCreate(BaseModel):
    """创建团队：名称必填，简介可选"""

    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class TeamUpdate(BaseModel):
    """更新团队：仅传需要修改的字段"""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class TeamJoinRequest(BaseModel):
    """凭邀请码加入团队"""

    invite_code: str = Field(..., min_length=4, max_length=16)


class TeamMemberRoleUpdate(BaseModel):
    """调整成员角色，owner 角色不可通过该接口转移"""

    role: str = Field(..., pattern="^(admin|member)$")


class TeamOut(BaseModel):
    """团队概要：附带当前用户角色与资源计数"""

    id: int
    name: str
    description: str | None = None
    owner_id: int
    invite_code: str
    role: str
    member_count: int = 0
    note_count: int = 0
    prompt_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TeamMemberOut(BaseModel):
    """团队成员视图：附带用户名与头像，便于前端直接展示"""

    id: int
    user_id: int
    username: str
    avatar: str | None = None
    role: str
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TeamInviteOut(BaseModel):
    """邀请码响应"""

    invite_code: str
