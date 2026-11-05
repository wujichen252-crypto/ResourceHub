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
    __table_args__ = (
        Index("ix_agent_profiles_user_default", "user_id", "is_default"),
        {"comment": "智能体人格配置表：一个用户可有多条，MVP 只激活其中一条"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="人格配置 ID，主键自增"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户 ID（级联删除）"
    )
    name: Mapped[str] = mapped_column(
        String(50), default="知识助手", nullable=False, comment="智能体名称"
    )
    persona: Mapped[str] = mapped_column(
        Text, default="你的个人知识搭档，帮你梳理笔记与推进目标", nullable=False, comment="人设描述（写进系统提示词）"
    )
    tone: Mapped[str] = mapped_column(
        String(20), default="严谨", nullable=False, comment="语气风格，如：严谨 / 轻松"
    )
    expertise: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="专长领域，可空"
    )
    boundaries: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="行为边界约束（禁止事项），可空"
    )
    greeting: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="开场问候语，可空"
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否为默认激活的人格"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )


class AgentMemory(Base):
    """长期记忆：一条可独立删除、可检索、可衰减的事实

    source_conversation_id 故意不建外键：会话被清理后，记忆仍应作为用户资产保留。
    """

    __tablename__ = "agent_memories"
    __table_args__ = (
        Index("ix_agent_memories_user_type", "user_id", "memory_type"),
        Index("ix_agent_memories_user_importance", "user_id", "importance"),
        {"comment": "智能体长期记忆表：从对话沉淀、可检索可衰减，一条一条独立管理"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="记忆 ID，主键自增"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户 ID（级联删除）"
    )
    profile_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("agent_profiles.id", ondelete="SET NULL"), nullable=True, comment="关联人格 ID（人格删除后置空，记忆仍保留）"
    )
    memory_type: Mapped[str] = mapped_column(
        String(20), default="fact", nullable=False, comment="记忆类型：fact=事实 / preference=偏好 / goal=目标 / event=事件"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="记忆内容（一句完整的中文陈述）"
    )
    # 向量以 JSON 数组字符串存储：MySQL 5.7 无原生向量类型
    embedding: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="记忆向量（JSON 数组字符串，MySQL 无原生向量类型）"
    )
    importance: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False, comment="重要度 1-5，默认 3；决定检索优先级与淘汰顺序"
    )
    source: Mapped[str] = mapped_column(
        String(20), default="manual", nullable=False, comment="来源：manual=用户手动添加 / auto=对话自动沉淀"
    )
    source_conversation_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="来源会话 ID（故意无外键，会话清理后记忆仍保留）"
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="最近一次被检索使用的时间，未使用为 NULL"
    )
    use_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="累计被使用次数"
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="过期时间，NULL 为永久有效"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )


class AgentProactiveMessage(Base):
    """智能体主动消息：每日回顾、目标提醒等"""

    __tablename__ = "agent_proactive_messages"
    __table_args__ = (
        Index("ix_agent_proactive_user_status", "user_id", "status", "created_at"),
        {"comment": "智能体主动消息表：每日回顾、目标提醒等智能体主动发起的通知"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="消息 ID，主键自增"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户 ID（级联删除）"
    )
    kind: Mapped[str] = mapped_column(
        String(30), default="daily_review", nullable=False, comment="消息类型：daily_review=每日回顾 / stale_goal=目标久未推进"
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="消息标题"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="消息正文"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="unread", nullable=False, comment="状态：unread=未读 / read=已读 / dismissed=已忽略"
    )
    source_ref: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="来源引用（如关联的笔记/记忆 ID），可空"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
