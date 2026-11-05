"""remove_legacy_note_columns

Revision ID: e5b9d2f4c817
Revises: a7c3e91d5b48
Create Date: 2026-11-05 14:10:00.000000

删除 notes 表的两列 SQLite 迁移时期遗留死列（代码与模型均已不再使用）：
- content_json    旧版富文本 JSON 存储
- content_format  旧版内容格式标记
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5b9d2f4c817"
down_revision: Union[str, None] = "a7c3e91d5b48"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """删除 notes 表的遗留列"""
    op.drop_column("notes", "content_json")
    op.drop_column("notes", "content_format")


def downgrade() -> None:
    """恢复遗留列（仅用于回滚场景，新数据不会写入）"""
    op.add_column(
        "notes",
        sa.Column("content_format", sa.String(length=20), nullable=False, server_default="markdown"),
    )
    op.add_column("notes", sa.Column("content_json", sa.Text(), nullable=True))
