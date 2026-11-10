"""add_password_reset_tokens

Revision ID: e4b9c2f17a63
Revises: f9d2b6c1a8e4
Create Date: 2026-11-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4b9c2f17a63'
down_revision: Union[str, None] = 'f9d2b6c1a8e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="主键自增"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="所属用户 ID（用户删除时级联删除）"),
        sa.Column("code_hash", sa.String(length=64), nullable=False, comment="验证码 HMAC-SHA256，不存明文"),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False, comment="验证失败次数"),
        sa.Column("expires_at", sa.DateTime(), nullable=False, comment="过期时间（应用时钟，与数据库时钟无关）"),
        sa.Column("used_at", sa.DateTime(), nullable=True, comment="失效时间：已使用或被新验证码作废，非空即不可再用"),
        sa.Column("created_at", sa.DateTime(), nullable=False, comment="创建时间（应用时钟，与数据库时钟无关）"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        comment="密码重置验证码：只存哈希，用后即焚",
    )
    op.create_index(
        "ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
