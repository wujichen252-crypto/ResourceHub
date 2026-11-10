"""add_note_templates

Revision ID: b7e3d9c41f20
Revises: e4b9c2f17a63
Create Date: 2026-11-10 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7e3d9c41f20'
down_revision: Union[str, None] = 'e4b9c2f17a63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "note_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="模板 ID，主键自增"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="所属用户 ID（用户删除时级联删除）"),
        sa.Column("name", sa.String(length=255), nullable=False, comment="模板名称，同时作为套用后笔记的初始标题"),
        sa.Column("content", sa.Text(), nullable=True, comment="模板正文（HTML 快照或 Markdown 原文）"),
        sa.Column("content_format", sa.String(length=20), server_default="markdown", nullable=False, comment="正文存储格式：markdown=Markdown 原文 / json=块编辑器 JSON"),
        sa.Column("content_json", sa.Text(), nullable=True, comment="块编辑器 JSON 正文（content_format=json 时为权威）"),
        sa.Column("tags", sa.String(length=500), nullable=True, comment="默认标签，JSON 数组字符串"),
        sa.Column("category_id", sa.Integer(), nullable=True, comment="默认目录 ID（目录删除后置空）"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        comment="笔记模板表：新建笔记时套用的初始标题、正文与标签预设",
    )
    op.create_index(
        "ix_note_templates_user_id", "note_templates", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_note_templates_user_id", table_name="note_templates")
    op.drop_table("note_templates")
