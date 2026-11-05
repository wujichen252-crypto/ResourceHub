"""add_ai_usage_prompt_id

Revision ID: c8e2f4a6b9d1
Revises: b6d4e2f7a913
Create Date: 2026-11-05 12:00:00.000000

AI 成本与效果看板（知识资产 ROI）数据层：
- ai_usage_logs 增加 prompt_id 可空列，用于 eval/optimize 场景的提示词级成本归集
  （历史计量不随提示词删除而消失，故不设外键约束）
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c8e2f4a6b9d1"
down_revision: Union[str, None] = "b6d4e2f7a913"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_usage_logs",
        sa.Column("prompt_id", sa.Integer(), nullable=True,
                  comment="关联提示词 ID（eval/optimize 场景使用，用于提示词级成本归集）"),
    )


def downgrade() -> None:
    op.drop_column("ai_usage_logs", "prompt_id")
