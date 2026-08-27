"""User account model.

One table stores all five roles (FR-A7). Role specific detail lives in
companion tables such as ``doctor_profiles`` so that the account table stays
focused on identity, credentials and account state.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import AccountStatus, UserRole
from app.core.database import Base


def utc_now() -> datetime:
    """Return the current timezone aware UTC timestamp."""
    return datetime.now(timezone.utc)


class User(Base):
    """A JU_FIX account belonging to one of the five system roles.

    Attributes:
        university_id: The unique JU identifier used as the primary login handle.
        email: Optional verified email address (FR-A1).
        phone: Optional Bangladeshi phone number (FR-A1).
        password_hash: The bcrypt hash of the password. Never the password itself.
        role: One of :class:`~app.core.constants.UserRole`.
        status: One of :class:`~app.core.constants.AccountStatus`.
        failed_login_attempts: Consecutive failed logins used for lockout (FR-A6).
        locked_until: Timestamp until which login is refused.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    university_id: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[str] = mapped_column(String(20), nullable=False, default=UserRole.STUDENT.value)
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=AccountStatus.PENDING_VERIFICATION.value
    )

    department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    designation: Mapped[str | None] = mapped_column(String(120), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(255), nullable=True)

    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    def __repr__(self) -> str:
        """Return a debug representation that never exposes credentials."""
        return f"<User id={self.id} university_id={self.university_id} role={self.role}>"
