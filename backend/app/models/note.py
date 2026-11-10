from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Note(Base):
    __tablename__ = "notes"
    __table_args__ = (
        Index("ix_notes_visibility_updated", "visibility", "updated_at"),
        {"comment": "笔记表：用户笔记正文、标签与广场分享状态"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="笔记 ID，主键自增"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户 ID（用户删除时级联删除）"
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="笔记标题"
    )
    content: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="笔记正文（Markdown 或 HTML 快照）"
    )
    # ── 存储双轨（块编辑器地基）──
    # content_format='markdown'：content 为权威（旧数据 / MD 导入）
    # content_format='json'：content_json 为权威，content 退化为 HTML 快照（供搜索 / 预览 / 阅读兜底）
    content_format: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="markdown", default="markdown",
        comment="正文存储格式：markdown=Markdown 原文 / json=块编辑器 JSON",
    )
    # 注意：MySQL 5.7 TEXT 列不允许 DEFAULT，由应用层填充
    content_json: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="块编辑器 JSON 正文（content_format=json 时为权威）"
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, comment="所属分类 ID（分类删除后置空）"
    )
    tags: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="标签，JSON 数组字符串"
    )
    is_pinned: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="是否置顶"
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
        Integer, nullable=True, comment="fork 来源笔记 ID（无外键）"
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
    owner = relationship("User", back_populates="notes")
    category = relationship("Category", back_populates="notes")


class NoteTemplate(Base):
    __tablename__ = "note_templates"
    __table_args__ = (
        Index("ix_note_templates_user_id", "user_id"),
        {"comment": "笔记模板表：新建笔记时套用的初始标题、正文与标签预设"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="模板 ID，主键自增"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户 ID（用户删除时级联删除）"
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="模板名称，同时作为套用后笔记的初始标题"
    )
    content: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="模板正文（HTML 快照或 Markdown 原文）"
    )
    content_format: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="markdown", default="markdown",
        comment="正文存储格式：markdown=Markdown 原文 / json=块编辑器 JSON",
    )
    content_json: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="块编辑器 JSON 正文（content_format=json 时为权威）"
    )
    tags: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="默认标签，JSON 数组字符串"
    )
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, comment="默认目录 ID（目录删除后置空）"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )
