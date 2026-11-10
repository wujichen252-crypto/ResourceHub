"""add_team_knowledge_base

Revision ID: f4b7c2d9e610
Revises: f9d2b6c1a8e4
Create Date: 2026-11-11 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4b7c2d9e610'
down_revision: Union[str, None] = 'f9d2b6c1a8e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'teams',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='团队 ID，主键自增'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='团队名称'),
        sa.Column('description', sa.String(length=500), nullable=True, comment='团队简介，可空'),
        sa.Column('owner_id', sa.Integer(), nullable=False, comment='团队创建者用户 ID'),
        sa.Column('invite_code', sa.String(length=16), nullable=False, comment='邀请码，成员凭码加入'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='更新时间'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invite_code'),
        comment='团队表：团队知识库空间，成员共享资源',
    )
    op.create_index('ix_teams_invite_code', 'teams', ['invite_code'], unique=True)

    op.create_table(
        'team_members',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False, comment='成员记录 ID，主键自增'),
        sa.Column('team_id', sa.Integer(), nullable=False, comment='所属团队 ID'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='成员用户 ID'),
        sa.Column('role', sa.String(length=20), server_default='member', nullable=False, comment='角色：owner/admin/member'),
        sa.Column('joined_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='加入时间'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('team_id', 'user_id', name='uq_team_members_team_user'),
        comment='团队成员表：记录角色与加入时间',
    )
    op.create_index('ix_team_members_user', 'team_members', ['user_id'], unique=False)

    # 笔记 / 提示词归属团队：为空表示个人资源；团队解散后置空，回落个人空间
    op.add_column('notes', sa.Column('team_id', sa.Integer(), nullable=True, comment='所属团队 ID（NULL=个人笔记）'))
    op.create_foreign_key('fk_notes_team_id_teams', 'notes', 'teams', ['team_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_notes_team_id', 'notes', ['team_id'], unique=False)

    op.add_column('prompts', sa.Column('team_id', sa.Integer(), nullable=True, comment='所属团队 ID（NULL=个人提示词）'))
    op.create_foreign_key('fk_prompts_team_id_teams', 'prompts', 'teams', ['team_id'], ['id'], ondelete='SET NULL')
    op.create_index('ix_prompts_team_id', 'prompts', ['team_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_prompts_team_id', table_name='prompts')
    op.drop_constraint('fk_prompts_team_id_teams', 'prompts', type_='foreignkey')
    op.drop_column('prompts', 'team_id')

    op.drop_index('ix_notes_team_id', table_name='notes')
    op.drop_constraint('fk_notes_team_id_teams', 'notes', type_='foreignkey')
    op.drop_column('notes', 'team_id')

    op.drop_index('ix_team_members_user', table_name='team_members')
    op.drop_table('team_members')
    op.drop_index('ix_teams_invite_code', table_name='teams')
    op.drop_table('teams')
