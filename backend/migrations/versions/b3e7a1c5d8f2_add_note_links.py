"""add_note_links

Revision ID: b3e7a1c5d8f2
Revises: 9eb3282b6023
Create Date: 2026-11-12 16:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3e7a1c5d8f2'
down_revision: Union[str, None] = '9eb3282b6023'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'note_links',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='链接记录 ID，主键自增'),
        sa.Column('source_note_id', sa.Integer(), nullable=False, comment='引用方笔记 ID（来源笔记删除时级联删除）'),
        sa.Column('target_note_id', sa.Integer(), nullable=True, comment='被引用笔记 ID（保存时按标题解析；目标删除后置空，保留标题以便展示断链）'),
        sa.Column('target_title', sa.String(length=255), nullable=False, comment='被引用笔记标题快照（链接的唯一事实来源，目标改名不回写）'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='创建时间'),
        sa.ForeignKeyConstraint(['source_note_id'], ['notes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_note_id'], ['notes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_note_id', 'target_title', name='uq_note_links_source_title'),
        comment='笔记双向链接表：source 引用 target_title；target_note_id 解析成功时非空，目标被删后置空',
    )
    op.create_index('ix_note_links_target_note', 'note_links', ['target_note_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_note_links_target_note', table_name='note_links')
    op.drop_table('note_links')
