from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"comment": "用户表：账号、登录凭证与时间戳"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="用户 ID，主键自增"
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="用户名，全站唯一"
    )
    email: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True, comment="邮箱，唯一，可为空"
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="密码哈希（不存明文）"
    )
    avatar: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="头像 URL，可空"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )

    # Relationships
    notes = relationship("Note", back_populates="owner", cascade="all, delete-orphan")
    prompts = relationship("Prompt", back_populates="owner", cascade="all, delete-orphan")
    categories = relationship("Category", back_populates="owner", cascade="all, delete-orphan")
