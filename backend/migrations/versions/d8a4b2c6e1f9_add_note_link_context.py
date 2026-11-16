"""add_note_link_context

Revision ID: d8a4b2c6e1f9
Revises: b3e7a1c5d8f2
Create Date: 2026-11-16 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8a4b2c6e1f9'
down_revision: Union[str, None] = 'b3e7a1c5d8f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'note_links',
        sa.Column('context', sa.String(length=200), nullable=True,
                  comment='引用上下文片段：引用处所在段落/行的纯文本（取首个引用处），供反链面板展示'),
    )


def downgrade() -> None:
    op.drop_column('note_links', 'context')
