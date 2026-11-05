from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ── 存储双轨（块编辑器地基）──
    # content_format='markdown'：content 为权威（旧数据 / MD 导入）
    # content_format='json'：content_json 为权威，content 退化为 HTML 快照（供搜索 / 预览 / 阅读兜底）
    content_format: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="markdown", default="markdown"
    )
    # 注意：MySQL 5.7 TEXT 列不允许 DEFAULT，由应用层填充
    content_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)  # JSON string
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    # ── 资源广场（分享）字段 ──
    visibility: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="private", default="private"
    )  # private / public
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # fork 溯源：故意不建外键，原作者删号不影响副本
    source_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_content_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_username: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_notes_visibility_updated", "visibility", "updated_at"),
    )

    # Relationships
    owner = relationship("User", back_populates="notes")
    category = relationship("Category", back_populates="notes")
