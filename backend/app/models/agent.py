"""AI 智能体身份层 ORM 模型

包含三类数据：
1. 人格配置（agent_profiles）—— 智能体的名字、语气与边界
2. 长期记忆（agent_memories）—— 从对话中沉淀、可被检索与淘汰的事实
3. 主动消息（agent_proactive_messages）—— 智能体主动发起的回顾与提醒
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class AgentProfile(Base):
    """智能体人格：一个用户可有多条，MVP 只激活其中一条"""

    __tablename__ = "agent_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), default="知识助手", nullable=False)
    persona: Mapped[str] = mapped_column(
        Text, default="你的个人知识搭档，帮你梳理笔记与推进目标", nullable=False
    )
    tone: Mapped[str] = mapped_column(String(20), default="严谨", nullable=False)
    expertise: Mapped[str | None] = mapped_column(String(200), nullable=True)
    boundaries: Mapped[str | None] = mapped_column(Text, nullable=True)
    greeting: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_agent_profiles_user_default", "user_id", "is_default"),)


class AgentMemory(Base):
    """长期记忆：一条可独立删除、可检索、可衰减的事实

    source_conversation_id 故意不建外键：会话被清理后，记忆仍应作为用户资产保留。
    """

    __tablename__ = "agent_memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("agent_profiles.id", ondelete="SET NULL"), nullable=True
    )
    memory_type: Mapped[str] = mapped_column(String(20), default="fact", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 向量以 JSON 数组字符串存储：MySQL 5.7 无原生向量类型
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
    importance: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    source_conversation_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_agent_memories_user_type", "user_id", "memory_type"),
        Index("ix_agent_memories_user_importance", "user_id", "importance"),
    )


class AgentProactiveMessage(Base):
    """智能体主动消息：每日回顾、目标提醒等"""

    __tablename__ = "agent_proactive_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(30), default="daily_review", nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="unread", nullable=False)
    source_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("ix_agent_proactive_user_status", "user_id", "status", "created_at"),
    )
