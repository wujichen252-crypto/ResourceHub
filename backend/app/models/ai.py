"""
AI 能力层 ORM 模型

包含五类数据：
1. 笔记分块与向量索引（note_chunks）—— RAG 检索底座
2. 对话与消息（ai_conversations / ai_messages）—— 多轮问答留痕
3. Agent 运行轨迹（ai_runs）—— 工具调用可回放、人在环挂起状态
4. 调用计量（ai_usage_logs）—— token 成本、成功率、限流依据
5. 提示词评测（prompt_eval_suites / cases / results）—— Prompt 实验室
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class NoteChunk(Base):
    """笔记分块：RAG 的最小检索单元"""

    __tablename__ = "note_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    note_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 文内序号，从 0 开始
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 增量更新判重
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # 向量以 JSON 数组字符串存储：MySQL 5.7 无原生向量类型，万级 chunk 用 Python 余弦即可
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    note = relationship("Note")

    __table_args__ = (
        UniqueConstraint("note_id", "chunk_index", name="uq_note_chunks_note_index"),
        Index("ix_note_chunks_user_note", "user_id", "note_id"),
    )


class AIConversation(Base):
    """AI 会话"""

    __tablename__ = "ai_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), default="新对话", nullable=False)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    messages = relationship(
        "AIMessage", back_populates="conversation", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_ai_conversations_user_updated", "user_id", "updated_at"),)


class AIMessage(Base):
    """AI 会话消息，检索引用与工具调用以 JSON 字符串留档"""

    __tablename__ = "ai_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user / assistant / tool
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组
    tool_calls: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 数组
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    conversation = relationship("AIConversation", back_populates="messages")

    __table_args__ = (Index("ix_ai_messages_conversation_id", "conversation_id", "id"),)


class AIRun(Base):
    """Agent 运行轨迹：steps 存完整事件序列，pending_action 存待确认写操作"""

    __tablename__ = "ai_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    conversation_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("ai_conversations.id", ondelete="SET NULL"), nullable=True
    )
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default="running", nullable=False
    )  # running / waiting_confirmation / succeeded / failed / cancelled
    steps: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # JSON 数组
    step_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pending_action: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON：待确认工具调用
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_ai_runs_user_created", "user_id", "created_at"),
        Index("ix_ai_runs_status", "status"),
    )


class AIUsageLog(Base):
    """模型调用计量：成本核算、配额限制与评测数据来源"""

    __tablename__ = "ai_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    scene: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # chat / agent / embedding / eval / optimize
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_ai_usage_user_created", "user_id", "created_at"),
        Index("ix_ai_usage_scene_created", "scene", "created_at"),
    )


class PromptEvalSuite(Base):
    """提示词评测集：一个提示词可拥有多套评测标准"""

    __tablename__ = "prompt_eval_suites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    prompt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(191), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    judge_model: Mapped[str | None] = mapped_column(String(64), nullable=True)  # LLM 评委模型
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    cases = relationship(
        "PromptEvalCase", back_populates="suite", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_prompt_eval_suites_user_prompt", "user_id", "prompt_id"),)


class PromptEvalCase(Base):
    """单条评测用例：变量取值 + 期望输出 + 评分要点"""

    __tablename__ = "prompt_eval_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    suite_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prompt_eval_suites.id", ondelete="CASCADE"), nullable=False
    )
    variables: Mapped[str] = mapped_column(Text, default="{}", nullable=False)  # JSON 对象
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    rubric: Mapped[str | None] = mapped_column(Text, nullable=True)  # 评分要点
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    suite = relationship("PromptEvalSuite", back_populates="cases")

    __table_args__ = (Index("ix_prompt_eval_cases_suite", "suite_id"),)


class PromptEvalResult(Base):
    """一次评测运行的结果：按版本聚合即可做 A/B 对比"""

    __tablename__ = "prompt_eval_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    suite_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prompt_eval_suites.id", ondelete="CASCADE"), nullable=False
    )
    case_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prompt_eval_cases.id", ondelete="CASCADE"), nullable=False
    )
    prompt_version_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True
    )
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    output: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)  # 0-100
    judge_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_prompt_eval_results_suite_created", "suite_id", "created_at"),
        Index("ix_prompt_eval_results_case", "case_id"),
    )
