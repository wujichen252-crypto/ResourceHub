"""add_prompt_optimization_tables

Revision ID: a7c3e91d5b48
Revises: 4d8a1f6c9b02
Create Date: 2026-11-05 10:00:00.000000

新增提示词自动优化器数据表（评测闭环）：
- prompt_optimization_runs    优化会话：基线/候选分数、状态机、诊断与改动说明
- prompt_optimization_rounds  单轮历史：逐用例对比快照，供回放
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a7c3e91d5b48"
down_revision: Union[str, None] = "4d8a1f6c9b02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prompt_optimization_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("prompt_id", sa.Integer(), nullable=False),
        sa.Column("suite_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="running"),
        sa.Column("round_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_rounds", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("score_threshold", sa.Float(), nullable=False, server_default="80"),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.3"),
        sa.Column("baseline_version_id", sa.Integer(), nullable=True),
        sa.Column("baseline_content", sa.Text(), nullable=True),
        sa.Column("baseline_score", sa.Float(), nullable=True),
        sa.Column("baseline_detail", sa.Text(), nullable=True),
        sa.Column("candidate_content", sa.Text(), nullable=True),
        sa.Column("candidate_score", sa.Float(), nullable=True),
        sa.Column("candidate_detail", sa.Text(), nullable=True),
        sa.Column("candidate_version_id", sa.Integer(), nullable=True),
        sa.Column("analysis", sa.Text(), nullable=True),
        sa.Column("changelog", sa.String(length=500), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["prompt_id"], ["prompts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["suite_id"], ["prompt_eval_suites.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["baseline_version_id"], ["prompt_versions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["candidate_version_id"], ["prompt_versions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_prompt_opt_runs_user_created",
        "prompt_optimization_runs",
        ["user_id", "created_at"],
        unique=False,
    )
    op.create_index("ix_prompt_opt_runs_status", "prompt_optimization_runs", ["status"], unique=False)

    op.create_table(
        "prompt_optimization_rounds",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="completed"),
        sa.Column("candidate_content", sa.Text(), nullable=True),
        sa.Column("candidate_score", sa.Float(), nullable=True),
        sa.Column("reference_score", sa.Float(), nullable=True),
        sa.Column("analysis", sa.Text(), nullable=True),
        sa.Column("changelog", sa.String(length=500), nullable=True),
        sa.Column("snapshot", sa.Text(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"], ["prompt_optimization_runs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_prompt_opt_rounds_run",
        "prompt_optimization_rounds",
        ["run_id", "round_number"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_prompt_opt_rounds_run", table_name="prompt_optimization_rounds")
    op.drop_table("prompt_optimization_rounds")
    op.drop_index("ix_prompt_opt_runs_status", table_name="prompt_optimization_runs")
    op.drop_index("ix_prompt_opt_runs_user_created", table_name="prompt_optimization_runs")
    op.drop_table("prompt_optimization_runs")
