"""Request schemas for Electronic Health Records (FR-D2 to FR-D5)."""

from datetime import date

from pydantic import BaseModel, Field


class CreateRecordRequest(BaseModel):
    """Payload for adding a clinical entry (FR-D2)."""

    patient_id: int = Field(gt=0)
    visit_date: date
    title: str = Field(min_length=3, max_length=160)
    diagnosis: str = Field(min_length=3)
    record_type: str = Field(default="consultation", max_length=30)
    appointment_id: int | None = None
    symptoms: str | None = None
    examination: str | None = None
    treatment: str | None = None
    follow_up: str | None = None
    notes: str | None = None


class UpdateRecordRequest(BaseModel):
    """Payload for editing an entry; every edit creates a version (FR-D5)."""

    title: str | None = Field(default=None, min_length=3, max_length=160)
    diagnosis: str | None = Field(default=None, min_length=3)
    symptoms: str | None = None
    examination: str | None = None
    treatment: str | None = None
    follow_up: str | None = None
    notes: str | None = None
    change_note: str | None = Field(default=None, max_length=300)
