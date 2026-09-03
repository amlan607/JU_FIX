"""Request and response schemas for notifications (FR-H1 to FR-H5)."""

from datetime import datetime

from pydantic import BaseModel, Field

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


class PreferenceItem(BaseModel):
    """One category preference shown in settings."""

    category: str
    label: str
    description: str
    in_app_enabled: bool
    email_enabled: bool
    can_disable: bool


class UpdatePreferenceRequest(BaseModel):
    """Payload for changing one category's delivery channels."""

    category: str = Field(min_length=2, max_length=40)
    in_app_enabled: bool | None = None
    email_enabled: bool | None = None
