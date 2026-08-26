"""Configurable operational settings managed by an administrator (FR-J5).

Values are stored as strings in a single key/value table so a new setting needs
no schema migration. The service layer parses each value to its expected type.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.user import utc_now


class SystemSetting(Base):
    """One administrator configurable value.

    Attributes:
        key: The stable setting name, for example ``daily_token_limit``.
        value: The stored value as text.
        updated_by: The administrator who last changed it.
    """

    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
