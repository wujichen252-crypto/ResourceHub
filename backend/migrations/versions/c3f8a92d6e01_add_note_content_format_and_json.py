"""add_note_content_format_and_json

存储双轨：notes 表新增 content_format / content_json 两列，为块编辑器打底。
- content_format：VARCHAR(20) NOT NULL DEFAULT 'markdown'（VARCHAR 允许 DEFAULT）
- content_json：TEXT NULL（MySQL 5.7 TEXT 列不允许 DEFAULT，应用层填充）

Revision ID: c3f8a92d6e01
Revises: 4d8a1f6c9b02
Create Date: 2026-11-04 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3f8a92d6e01"
down_revision: Union[str, None] = "4d8a1f6c9b02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notes",
        sa.Column(
            "content_format",
            sa.String(20),
            nullable=False,
            server_default="markdown",
        ),
    )
    op.add_column("notes", sa.Column("content_json", sa.Text(), nullable=True))


def downgrade() -> None:
    # 回滚前清空块文档列，避免遗留孤儿数据
    op.drop_column("notes", "content_json")
    op.drop_column("notes", "content_format")
