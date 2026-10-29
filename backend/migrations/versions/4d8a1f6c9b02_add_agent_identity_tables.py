"""add_agent_identity_tables

Revision ID: 4d8a1f6c9b02
Revises: 9f2c7d41ab03
Create Date: 2026-10-29 12:00:00.000000

新增智能体身份层数据表：
- agent_profiles              人格配置
- agent_memories              长期记忆
- agent_proactive_messages    主动消息
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4d8a1f6c9b02"
down_revision: Union[str, None] = "9f2c7d41ab03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建人格、记忆与主动消息三张表"""
    op.create_table(
        "agent_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False, server_default="知识助手"),
        sa.Column(
            "persona",
            sa.Text(),
            nullable=False,
            server_default="你的个人知识搭档，帮你梳理笔记与推进目标",
        ),
        sa.Column("tone", sa.String(length=20), nullable=False, server_default="严谨"),
        sa.Column("expertise", sa.String(length=200), nullable=True),
        sa.Column("boundaries", sa.Text(), nullable=True),
        sa.Column("greeting", sa.String(length=200), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_profiles_user_default",
        "agent_profiles",
        ["user_id", "is_default"],
        unique=False,
    )

    op.create_table(
        "agent_memories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=True),
        sa.Column("memory_type", sa.String(length=20), nullable=False, server_default="fact"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column("importance", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="manual"),
        sa.Column("source_conversation_id", sa.Integer(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("use_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["agent_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_memories_user_type",
        "agent_memories",
        ["user_id", "memory_type"],
        unique=False,
    )
    op.create_index(
        "ix_agent_memories_user_importance",
        "agent_memories",
        ["user_id", "importance"],
        unique=False,
    )

    op.create_table(
        "agent_proactive_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "kind", sa.String(length=30), nullable=False, server_default="daily_review"
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="unread"),
        sa.Column("source_ref", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_agent_proactive_user_status",
        "agent_proactive_messages",
        ["user_id", "status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_proactive_user_status", table_name="agent_proactive_messages"
    )
    op.drop_table("agent_proactive_messages")
    op.drop_index("ix_agent_memories_user_importance", table_name="agent_memories")
    op.drop_index("ix_agent_memories_user_type", table_name="agent_memories")
    op.drop_table("agent_memories")
    op.drop_index("ix_agent_profiles_user_default", table_name="agent_profiles")
    op.drop_table("agent_profiles")
