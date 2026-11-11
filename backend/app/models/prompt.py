from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Prompt(Base):
    __tablename__ = "prompts"
    __table_args__ = (
        Index("ix_prompts_visibility_updated", "visibility", "updated_at"),
        {"comment": "提示词表：AI 提示词正文、变量定义与广场分享状态"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="提示词 ID，主键自增"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户 ID（用户删除时级联删除）"
    )
    # 团队知识库：为空表示个人提示词；团队解散后置空，回落为作者个人资源
    team_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("teams.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="所属团队 ID（NULL=个人提示词）",
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="提示词标题"
    )
    description: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="提示词简介，可空"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="提示词正文（支持 {{变量}} 占位符）"
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, comment="所属分类 ID（分类删除后置空）"
    )
    variables: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="变量定义，JSON 数组字符串"
    )
    tags: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="标签，JSON 数组字符串"
    )
    is_favorite: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否收藏"
    )
    usage_count: Mapped[int] = mapped_column(
        Integer, default=0, comment="累计使用次数"
    )
    # ── 资源广场（分享）字段 ──
    visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="private", default="private",
        comment="可见性：private=私有 / public=广场公开",
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="公开发布时间，未发布为 NULL"
    )
    # fork 溯源：故意不建外键，原作者删号不影响副本
    source_user_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="fork 来源用户 ID（无外键，作者删号不影响副本）"
    )
    source_content_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="fork 来源提示词 ID（无外键）"
    )
    source_username: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="fork 来源用户名快照（冗余存储用于展示）"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    # Relationships
    owner = relationship("User", back_populates="prompts")
    category = relationship("Category", back_populates="prompts")
    versions = relationship("PromptVersion", back_populates="prompt", cascade="all, delete-orphan")
    presets = relationship("PromptPreset", back_populates="prompt", cascade="all, delete-orphan")
    usage_logs = relationship("PromptUsageLog", back_populates="prompt", cascade="all, delete-orphan")


class PromptVersion(Base):
    __tablename__ = "prompt_versions"
    __table_args__ = {"comment": "提示词版本历史表：类 Git 的版本快照（支持标签与分支）"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="版本 ID，主键自增"
    )
    prompt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False, comment="所属提示词 ID（级联删除）"
    )
    version_number: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="版本号，提示词内自增"
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="该版本的标题快照"
    )
    description: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="该版本的简介快照"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="该版本的正文快照"
    )
    variables: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="该版本的变量定义，JSON 数组字符串"
    )
    tags: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="该版本的标签，JSON 数组字符串"
    )
    message: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="提交说明（类似 Git commit message）"
    )
    labels: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="版本标签，JSON 数组：如 [\"production\", \"staging\"]"
    )
    branch_name: Mapped[str] = mapped_column(
        String(100), nullable=False, default="main", comment="所属分支名，默认 main"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )

    prompt = relationship("Prompt", back_populates="versions")


class PromptPreset(Base):
    __tablename__ = "prompt_presets"
    __table_args__ = {"comment": "提示词变量预设表：保存一套变量取值，一键填入"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="预设 ID，主键自增"
    )
    prompt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False, comment="所属提示词 ID（级联删除）"
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="预设名称"
    )
    values: Mapped[str] = mapped_column(
        Text, nullable=False, comment="变量取值，JSON 对象字符串（键为变量名）"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )

    prompt = relationship("Prompt", back_populates="presets")


class PromptUsageLog(Base):
    __tablename__ = "prompt_usage_logs"
    __table_args__ = (
        Index("ix_usage_prompt_date", "prompt_id", "used_at"),
        Index("ix_usage_user_date", "user_id", "used_at"),
        {"comment": "提示词使用记录表：每次运行留痕，供使用分析面板统计"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="记录 ID，主键自增"
    )
    prompt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False, comment="被使用的提示词 ID（级联删除）"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="使用人用户 ID（级联删除）"
    )
    used_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="使用时间"
    )

    prompt = relationship("Prompt", back_populates="usage_logs")
