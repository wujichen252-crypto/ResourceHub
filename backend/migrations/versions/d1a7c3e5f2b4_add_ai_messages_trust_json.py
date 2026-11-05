"""add_ai_messages_trust_json

Revision ID: d1a7c3e5f2b4
Revises: c8e2f4a6b9d1
Create Date: 2026-11-05 16:00:00.000000

回答可信度可视化数据层：
- ai_messages 增加 trust_json 可空列，落库每条回答的可信度报告（JSON 对象字符串）
- 旧消息为 NULL，前端优雅降级（只显示引用 chip、不渲染徽章）
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d1a7c3e5f2b4"
down_revision: Union[str, None] = "c8e2f4a6b9d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "ai_messages",
        sa.Column("trust_json", sa.Text(), nullable=True,
                  comment="回答可信度报告，JSON 对象字符串（旧消息为 NULL，前端不渲染徽章）"),
    )


def downgrade() -> None:
    op.drop_column("ai_messages", "trust_json")
