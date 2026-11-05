"""merge_local_prompt_and_remote_note_branches

合并两条并行迁移分支：
- 本地：提示词自动优化 / ROI / 可信度（a7c3e91d5b48 → b6d4e2f7a913 → c8e2f4a6b9d1 → d1a7c3e5f2b4）
- 远程：笔记存储双轨（c3f8a92d6e01）

空迁移，仅用于收束分支头，保证后续只有一个 head。

Revision ID: f9d2b6c1a8e4
Revises: d1a7c3e5f2b4, c3f8a92d6e01
Create Date: 2026-11-05 15:30:00.000000

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "f9d2b6c1a8e4"
down_revision: Union[str, Sequence[str], None] = ("d1a7c3e5f2b4", "c3f8a92d6e01")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
