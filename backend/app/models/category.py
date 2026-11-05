from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = {"comment": "分类表：树形分类，同时服务笔记与提示词（type 区分）"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="分类 ID，主键自增"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, comment="所属用户 ID（用户删除时级联删除）"
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="分类名称"
    )
    type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="分类用途：note=笔记分类 / prompt=提示词分类"
    )
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, comment="父分类 ID（自引用，NULL 为顶级分类；父级删除后置空）"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, comment="同级排序序号，越小越靠前"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )

    # Relationships
    owner = relationship("User", back_populates="categories")
    children = relationship(
        "Category", backref="parent", remote_side=[id]
    )
    notes = relationship("Note", back_populates="category")
    prompts = relationship("Prompt", back_populates="category")
