"""Request schemas for appointment booking (FR-C1 to FR-C3)."""

from datetime import date, time

from pydantic import BaseModel, Field


class BookRequest(BaseModel):
    """Payload for booking a slot (FR-C1)."""

    doctor_id: int = Field(gt=0)
    appointment_date: date
    start_time: time
    reason: str = Field(min_length=3, max_length=500)
    visit_type: str = Field(default="consultation", max_length=30)


class RescheduleRequest(BaseModel):
    """Payload for moving a booking (FR-C3)."""

    appointment_date: date
    start_time: time


class CancelRequest(BaseModel):
    """Payload for cancelling a booking (FR-C3)."""

    reason: str | None = Field(default=None, max_length=500)
