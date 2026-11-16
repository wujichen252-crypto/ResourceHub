from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class NoteLink(Base):
    __tablename__ = "note_links"
    __table_args__ = (
        # 同一篇笔记对同一标题只保留一条链接（同名笔记解析时取最近更新的一篇）
        UniqueConstraint("source_note_id", "target_title", name="uq_note_links_source_title"),
        Index("ix_note_links_target_note", "target_note_id"),
        {"comment": "笔记双向链接表：source 引用 target_title；target_note_id 解析成功时非空，目标被删后置空"},
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="链接记录 ID，主键自增"
    )
    source_note_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("notes.id", ondelete="CASCADE"), nullable=False,
        comment="引用方笔记 ID（来源笔记删除时级联删除）",
    )
    target_note_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("notes.id", ondelete="SET NULL"), nullable=True,
        comment="被引用笔记 ID（保存时按标题解析；目标删除后置空，保留标题以便展示断链）",
    )
    target_title: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="被引用笔记标题快照（链接的唯一事实来源，目标改名不回写）"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
