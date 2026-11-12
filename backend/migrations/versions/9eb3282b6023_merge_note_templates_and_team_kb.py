"""merge_note_templates_and_team_kb

Revision ID: 9eb3282b6023
Revises: b7e3d9c41f20, f4b7c2d9e610
Create Date: 2026-11-12 16:23:15.375303

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9eb3282b6023'
down_revision: Union[str, None] = ('b7e3d9c41f20', 'f4b7c2d9e610')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
