"""Request and response schemas for Electronic Health Records (FR-D)."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.core.constants import RecordType
from app.schemas.common import ORMModel


class CreateRecordRequest(BaseModel):
    """Payload for adding a clinical entry (FR-D1, FR-D2)."""

    patient_id: int = Field(gt=0)
    visit_date: date
    title: str = Field(min_length=3, max_length=160)
    diagnosis: str = Field(min_length=3)
    record_type: RecordType = RecordType.CONSULTATION
    appointment_id: int | None = None
    symptoms: str | None = None
    examination: str | None = None
    treatment: str | None = None
    follow_up: str | None = None
    notes: str | None = None
    is_confidential: bool = False


class UpdateRecordRequest(BaseModel):
    """Payload for editing a clinical entry. Every edit creates a version (FR-D5)."""

    title: str | None = Field(default=None, min_length=3, max_length=160)
    diagnosis: str | None = Field(default=None, min_length=3)
    symptoms: str | None = None
    examination: str | None = None
    treatment: str | None = None
    follow_up: str | None = None
    notes: str | None = None
    change_note: str | None = Field(default=None, max_length=300)


class RecordSummary(ORMModel):
    """A record as shown in the patient timeline list."""

    id: int
    patient_id: int
    doctor_id: int
    record_type: str
    visit_date: date
    title: str
    diagnosis: str
    version: int
    doctor_name: str | None = None


class RecordDetail(RecordSummary):
    """The full clinical detail of one record."""

    appointment_id: int | None = None
    symptoms: str | None = None
    examination: str | None = None
    treatment: str | None = None
    follow_up: str | None = None
    notes: str | None = None
    is_confidential: bool = False
    patient_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class RecordVersionResponse(ORMModel):
    """One historical snapshot of a record (FR-D5)."""

    id: int
    record_id: int
    version_number: int
    title: str
    diagnosis: str
    symptoms: str | None = None
    treatment: str | None = None
    change_note: str | None = None
    edited_by: int
    editor_name: str | None = None
    created_at: datetime


class PatientSummary(BaseModel):
    """A patient the signed in doctor is authorised to open (FR-D4)."""

    patient_id: int
    full_name: str
    university_id: str
    department: str | None = None
    record_count: int
    last_visit: date | None = None
