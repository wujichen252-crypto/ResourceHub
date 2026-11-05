"""AI 能力层请求/响应模式"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatTurn(BaseModel):
    """历史对话单轮消息"""

    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    """RAG 问答请求"""

    message: str = Field(min_length=1, max_length=8000, description="用户问题")
    conversation_id: int | None = Field(default=None, description="续聊的会话 ID")
    model: str | None = Field(default=None, description="覆盖默认对话模型")
    use_rag: bool = Field(default=True, description="是否启用笔记检索增强")
    top_k: int = Field(default=4, ge=1, le=10, description="引用片段数量")
    temperature: float = Field(default=0.3, ge=0, le=2)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class AgentRunRequest(BaseModel):
    """Agent 任务请求"""

    goal: str = Field(min_length=1, max_length=4000, description="要完成的目标")
    conversation_id: int | None = None
    model: str | None = None
    confirm_write: bool = Field(
        default=False, description="是否已授权执行写操作（新建/更新笔记）"
    )
    max_steps: int = Field(default=6, ge=1, le=12)


class AgentResumeRequest(BaseModel):
    """确认并继续挂起的 Agent 运行"""

    run_id: int
    approve: bool = Field(default=True, description="是否批准待确认的写操作")


class CitationOut(BaseModel):
    """检索引用片段"""

    chunk_id: int
    note_id: int
    note_title: str
    snippet: str
    score: float
    vector_score: float = 0.0
    bm25_score: float = 0.0


class IndexRebuildRequest(BaseModel):
    """索引重建请求"""

    note_ids: list[int] | None = Field(
        default=None, description="为空则重建当前用户全部笔记的索引"
    )


class IndexRebuildResponse(BaseModel):
    """索引重建结果"""

    indexed_notes: int
    indexed_chunks: int
    skipped_notes: int
    embedding_ok: bool
    message: str


class AIStatusResponse(BaseModel):
    """AI 能力层状态"""

    configured: bool
    chat_model: str
    embedding_model: str
    note_count: int
    chunk_count: int
    indexed_note_count: int


class ConversationOut(BaseModel):
    """会话摘要"""

    id: int
    title: str
    model: str | None = None
    message_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentRunOut(BaseModel):
    """Agent 运行摘要"""

    id: int
    goal: str
    status: str
    step_count: int
    created_at: datetime
    finished_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class EvalCaseIn(BaseModel):
    """评测用例输入：变量取值 + 期望输出 + 评分要点"""

    variables: dict[str, str] = Field(default_factory=dict, description="提示词变量取值")
    expected_output: str | None = Field(default=None, max_length=4000)
    rubric: str | None = Field(default=None, max_length=2000, description="评分要点")


class EvalSuiteCreate(BaseModel):
    """创建评测集：一次提交评测标准与用例"""

    prompt_id: int
    name: str = Field(min_length=1, max_length=191)
    description: str | None = Field(default=None, max_length=500)
    judge_model: str | None = Field(default=None, max_length=64, description="评委模型，默认与生成模型一致")
    cases: list[EvalCaseIn] = Field(min_length=1, max_length=10)


class EvalRunRequest(BaseModel):
    """执行一次评测"""

    model: str | None = Field(default=None, max_length=64, description="覆盖默认对话模型")
    prompt_version_id: int | None = Field(default=None, description="指定历史版本做 A/B 对比")
    temperature: float = Field(default=0.3, ge=0, le=2)


class OptimizationStartRequest(BaseModel):
    """启动提示词自动优化会话"""

    prompt_id: int
    suite_id: int
    prompt_version_id: int | None = Field(
        default=None, description="作为基线的历史版本，缺省用当前正文"
    )
    max_rounds: int = Field(default=3, ge=1, le=5, description="最大优化轮数")
    score_threshold: float = Field(
        default=80.0, ge=0, le=100, description="低于该分的用例才参与诊断"
    )
    temperature: float = Field(default=0.3, ge=0, le=2)


class InlineAction(str, Enum):
    """笔记内联 AI 动作类型"""

    EXPLAIN = "explain"  # 解释选中文本
    REWRITE = "rewrite"  # 改写选中文本
    ASK = "ask"  # 以选中文本为上下文提问


class InlineAIRequest(BaseModel):
    """笔记内联 AI 请求（选中文本 + 上下文）"""

    action: InlineAction = Field(description="动作类型")
    text: str = Field(min_length=1, max_length=2000, description="选中的原文（纯文本）")
    instruction: str = Field(
        default="", max_length=500, description="改写附加要求 / 提问的问题"
    )
    note_title: str = Field(default="", max_length=255, description="笔记标题，供模型理解语境")
    context_before: str = Field(default="", max_length=600, description="选区前文（纯文本截断）")
    context_after: str = Field(default="", max_length=600, description="选区后文（纯文本截断）")


class InlineAIResponse(BaseModel):
    """笔记内联 AI 响应"""

    action: InlineAction
    result: str = Field(description="AI 输出（Markdown 纯文本）")
    model: str = Field(description="实际使用的模型名")
    tokens: int = Field(description="本次消耗总 token")

