from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Team(Base):
    """团队：团队知识库的空间主体，成员共享笔记与提示词"""

    __tablename__ = "teams"
    __table_args__ = {"comment": "团队表：团队知识库空间，成员共享资源"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="团队 ID，主键自增"
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="团队名称"
    )
    description: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="团队简介，可空"
    )
    owner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="团队创建者用户 ID（用户删除时级联删除团队）",
    )
    invite_code: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        unique=True,
        index=True,
        comment="邀请码，成员凭码加入，全局唯一",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )

    members = relationship(
        "TeamMember", back_populates="team", cascade="all, delete-orphan"
    )


class TeamMember(Base):
    """团队成员：团队与用户的多对多关系，role 决定管理权限"""

    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),
        Index("ix_team_members_user", "user_id"),
        {"comment": "团队成员表：记录角色（owner/admin/member）与加入时间"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="成员记录 ID，主键自增"
    )
    team_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属团队 ID（团队删除时级联删除成员关系）",
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="成员用户 ID（用户删除时级联删除成员关系）",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="member",
        default="member",
        comment="角色：owner=创建者 / admin=管理员 / member=普通成员",
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="加入时间"
    )

    team = relationship("Team", back_populates="members")
