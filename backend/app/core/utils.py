"""Shared helpers used by several services (DRY, Coding Standard 3.1)."""

from datetime import date, datetime, timezone
from secrets import randbelow

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError


def utc_now() -> datetime:
    """Return the current timezone aware UTC time."""
    return datetime.now(timezone.utc)


def as_utc(value: datetime | None) -> datetime | None:
    """Attach UTC to a naive timestamp read back from SQLite."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def get_or_404(db: Session, model, pk: int, message: str):
    """Load a row by primary key or raise ``NotFoundError``."""
    row = db.get(model, pk)
    if row is None:
        raise NotFoundError(message)
    return row


def unique_code(db: Session, column, prefix: str, stamp: str = "%Y") -> str:
    """Return a random reference such as ``RX-20260824-004312`` not yet stored in ``column``."""
    while True:
        code = f"{prefix}-{date.today().strftime(stamp)}-{randbelow(1_000_000):06d}"
        if db.query(column.class_).filter(column == code).first() is None:
            return code
