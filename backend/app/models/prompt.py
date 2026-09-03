from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    variables: Mapped[str | None] = mapped_column(String(500), nullable=True)  # JSON array string
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)  # JSON array string
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    owner = relationship("User", back_populates="prompts")
    category = relationship("Category", back_populates="prompts")
    versions = relationship("PromptVersion", back_populates="prompt", cascade="all, delete-orphan")
    presets = relationship("PromptPreset", back_populates="prompt", cascade="all, delete-orphan")
    usage_logs = relationship("PromptUsageLog", back_populates="prompt", cascade="all, delete-orphan")


class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[str | None] = mapped_column(String(500), nullable=True)  # JSON array
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)  # JSON array
    message: Mapped[str | None] = mapped_column(String(500), nullable=True)  # commit message
    labels: Mapped[str | None] = mapped_column(String(500), nullable=True)  # JSON array: ["production", "staging"]
    branch_name: Mapped[str] = mapped_column(String(100), nullable=False, default="main")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    prompt = relationship("Prompt", back_populates="versions")


class PromptPreset(Base):
    __tablename__ = "prompt_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    values: Mapped[str] = mapped_column(Text, nullable=False)  # JSON dict of variable values
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    prompt = relationship("Prompt", back_populates="presets")


class PromptUsageLog(Base):
    __tablename__ = "prompt_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    prompt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    used_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    prompt = relationship("Prompt", back_populates="usage_logs")

    __table_args__ = (
        Index("ix_usage_prompt_date", "prompt_id", "used_at"),
        Index("ix_usage_user_date", "user_id", "used_at"),
    )
