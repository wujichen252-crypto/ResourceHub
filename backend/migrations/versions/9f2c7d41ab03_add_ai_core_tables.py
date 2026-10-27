"""add_ai_core_tables

Revision ID: 9f2c7d41ab03
Revises: 7eee4f46a3db
Create Date: 2026-10-21 10:00:00.000000

新增 AI 能力层数据表：
- note_chunks                 笔记分块与向量索引
- ai_conversations            会话
- ai_messages                 会话消息（引用/工具调用留档）
- ai_runs                     Agent 运行轨迹与待确认动作
- ai_usage_logs               模型调用计量
- prompt_eval_suites/cases/results  提示词实验室评测
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f2c7d41ab03"
down_revision: Union[str, None] = "7eee4f46a3db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """创建 AI 能力层全部表与索引"""
    op.create_table(
        "note_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("note_id", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("embedding", sa.Text(), nullable=True),
        sa.Column("embedding_model", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("note_id", "chunk_index", name="uq_note_chunks_note_index"),
    )
    op.create_index("ix_note_chunks_user_note", "note_chunks", ["user_id", "note_id"], unique=False)

    op.create_table(
        "ai_conversations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False, server_default="新对话"),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_conversations_user_updated",
        "ai_conversations",
        ["user_id", "updated_at"],
        unique=False,
    )

    op.create_table(
        "ai_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", sa.Text(), nullable=True),
        sa.Column("tool_calls", sa.Text(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_messages_conversation_id", "ai_messages", ["conversation_id", "id"], unique=False
    )

    op.create_table(
        "ai_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Integer(), nullable=True),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="running"),
        sa.Column("steps", sa.Text(), nullable=False),
        sa.Column("step_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pending_action", sa.Text(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_runs_user_created", "ai_runs", ["user_id", "created_at"], unique=False)
    op.create_index("ix_ai_runs_status", "ai_runs", ["status"], unique=False)

    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("scene", sa.String(length=32), nullable=False),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_usage_user_created", "ai_usage_logs", ["user_id", "created_at"], unique=False
    )
    op.create_index(
        "ix_ai_usage_scene_created", "ai_usage_logs", ["scene", "created_at"], unique=False
    )

    op.create_table(
        "prompt_eval_suites",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("prompt_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=191), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("judge_model", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prompt_id"], ["prompts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_prompt_eval_suites_user_prompt",
        "prompt_eval_suites",
        ["user_id", "prompt_id"],
        unique=False,
    )

    op.create_table(
        "prompt_eval_cases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("suite_id", sa.Integer(), nullable=False),
        sa.Column("variables", sa.Text(), nullable=False),
        sa.Column("expected_output", sa.Text(), nullable=True),
        sa.Column("rubric", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["suite_id"], ["prompt_eval_suites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_prompt_eval_cases_suite", "prompt_eval_cases", ["suite_id"], unique=False)

    op.create_table(
        "prompt_eval_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("suite_id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("prompt_version_id", sa.Integer(), nullable=True),
        sa.Column("model", sa.String(length=64), nullable=True),
        sa.Column("output", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("judge_reason", sa.Text(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["suite_id"], ["prompt_eval_suites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["case_id"], ["prompt_eval_cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["prompt_version_id"], ["prompt_versions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_prompt_eval_results_suite_created",
        "prompt_eval_results",
        ["suite_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_prompt_eval_results_case", "prompt_eval_results", ["case_id"], unique=False
    )


def downgrade() -> None:
    """按依赖倒序删除 AI 能力层表"""
    op.drop_index("ix_prompt_eval_results_case", table_name="prompt_eval_results")
    op.drop_index("ix_prompt_eval_results_suite_created", table_name="prompt_eval_results")
    op.drop_table("prompt_eval_results")
    op.drop_index("ix_prompt_eval_cases_suite", table_name="prompt_eval_cases")
    op.drop_table("prompt_eval_cases")
    op.drop_index("ix_prompt_eval_suites_user_prompt", table_name="prompt_eval_suites")
    op.drop_table("prompt_eval_suites")
    op.drop_index("ix_ai_usage_scene_created", table_name="ai_usage_logs")
    op.drop_index("ix_ai_usage_user_created", table_name="ai_usage_logs")
    op.drop_table("ai_usage_logs")
    op.drop_index("ix_ai_runs_status", table_name="ai_runs")
    op.drop_index("ix_ai_runs_user_created", table_name="ai_runs")
    op.drop_table("ai_runs")
    op.drop_index("ix_ai_messages_conversation_id", table_name="ai_messages")
    op.drop_table("ai_messages")
    op.drop_index("ix_ai_conversations_user_updated", table_name="ai_conversations")
    op.drop_table("ai_conversations")
    op.drop_index("ix_note_chunks_user_note", table_name="note_chunks")
    op.drop_table("note_chunks")
