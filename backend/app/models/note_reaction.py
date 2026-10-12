"""资源广场笔记互动模型：点赞 / 收藏（社交关系表）

与 fork 溯源字段（故意无外键）不同，点赞/收藏是实时状态：
笔记或删除用户时，关联互动行应级联清理，因此使用 FK + ondelete=CASCADE。
取消发布不删行——重新发布后历史点赞/收藏自动恢复。
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class NoteLike(Base):
    """广场笔记点赞（一个用户对一篇公开笔记最多一行）"""

    __tablename__ = "note_likes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    note_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("note_id", "user_id", name="uq_note_likes_note_user"),
        Index("ix_note_likes_user_created", "user_id", "created_at"),
    )


class NoteFavorite(Base):
    """广场笔记收藏（只读书签，区别于 fork 复制副本）"""

    __tablename__ = "note_favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    note_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("note_id", "user_id", name="uq_note_favorites_note_user"),
        Index("ix_note_favorites_user_created", "user_id", "created_at"),
    )
