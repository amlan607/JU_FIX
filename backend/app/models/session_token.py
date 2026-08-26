"""Issued JWT session records used for explicit logout and revocation.

Consistency Note 11.4 states that logging out must invalidate the session on the
server. Each issued token stores its ``jti`` so a single session can be revoked.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.user import utc_now


class SessionToken(Base):
    """A single issued access token.

    Attributes:
        token_id: The ``jti`` claim of the issued JWT.
        user_id: The owner of the session.
        expires_at: The natural expiry of the token.
        revoked_at: Set when the user logs out or an admin ends the session.
    """

    __tablename__ = "session_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    @property
    def is_active(self) -> bool:
        """Return ``True`` when the session has not been revoked."""
        return self.revoked_at is None
