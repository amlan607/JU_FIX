"""Response schemas for notifications and reminder sweeps (FR-H1 to FR-H3)."""

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class NotificationResponse(ORMModel):
    """A notification displayed in the user's notification centre."""

    id: int
    category: str
    title: str
    body: str
    entity_type: str | None = None
    entity_id: int | None = None
    is_read: bool
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Notifications together with the unread badge count."""

    unread_count: int
    notifications: list[NotificationResponse]


class ReminderRunResponse(BaseModel):
    """Counts returned by one reminder sweep."""

    appointment_reminders_created: int
    medicine_reminders_created: int
    checked_at: datetime
