"""AI 智能体身份层请求/响应模式"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MemoryType = Literal["fact", "preference", "goal", "event"]
ToneType = Literal["严谨", "轻松", "激励"]


class AgentProfileCreate(BaseModel):
    """创建人格"""

    name: str = Field(min_length=1, max_length=50, description="智能体名字")
    persona: str = Field(min_length=1, max_length=2000, description="角色定位")
    tone: ToneType = Field(default="严谨", description="语气风格")
    expertise: str | None = Field(default=None, max_length=200)
    boundaries: str | None = Field(default=None, max_length=2000, description="禁区")
    greeting: str | None = Field(default=None, max_length=200, description="空态问候语")
    is_default: bool = Field(default=False, description="是否设为当前激活人格")


class AgentProfileUpdate(BaseModel):
    """更新人格；未传字段保持不变"""

    name: str | None = Field(default=None, min_length=1, max_length=50)
    persona: str | None = Field(default=None, min_length=1, max_length=2000)
    tone: ToneType | None = None
    expertise: str | None = Field(default=None, max_length=200)
    boundaries: str | None = Field(default=None, max_length=2000)
    greeting: str | None = Field(default=None, max_length=200)
    is_default: bool | None = None


class AgentProfileOut(BaseModel):
    """人格响应"""

    id: int
    name: str
    persona: str
    tone: str
    expertise: str | None = None
    boundaries: str | None = None
    greeting: str | None = None
    is_default: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentMemoryCreate(BaseModel):
    """手动新增记忆"""

    content: str = Field(min_length=1, max_length=2000)
    memory_type: MemoryType = Field(default="fact")
    importance: int = Field(default=3, ge=1, le=5)
    profile_id: int | None = None
    expires_at: datetime | None = None


class AgentMemoryUpdate(BaseModel):
    """更新记忆；未传字段保持不变"""

    content: str | None = Field(default=None, min_length=1, max_length=2000)
    memory_type: MemoryType | None = None
    importance: int | None = Field(default=None, ge=1, le=5)
    expires_at: datetime | None = None


class AgentMemoryOut(BaseModel):
    """记忆响应；不暴露向量本身"""

    id: int
    profile_id: int | None = None
    memory_type: str
    content: str
    importance: int
    source: str
    use_count: int
    last_used_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentMemoryExtractResponse(BaseModel):
    """记忆抽取结果"""

    extracted: int
    skipped_duplicates: int
    total: int


class AgentMemoryExtractRequest(BaseModel):
    """手动触发记忆抽取"""

    conversation_id: int = Field(description="要抽取记忆的会话 ID")


class AgentProactiveMessageOut(BaseModel):
    """主动消息响应"""

    id: int
    kind: str
    title: str
    content: str
    status: str
    source_ref: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentProactiveScanResponse(BaseModel):
    """主动扫描结果"""

    created: int
    skipped: int
