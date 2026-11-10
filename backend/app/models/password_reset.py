from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    __table_args__ = {"comment": "密码重置验证码：只存哈希，用后即焚"}

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="主键自增"
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属用户 ID（用户删除时级联删除）",
    )
    code_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="验证码 HMAC-SHA256，不存明文"
    )
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="验证失败次数"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="过期时间（应用时钟，与数据库时钟无关）"
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="失效时间：已使用或被新验证码作废，非空即不可再用"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, comment="创建时间（应用时钟，与数据库时钟无关）"
    )
