"""Request and response schemas for digital prescriptions (FR-D1, FR-D3)."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class PrescriptionItemRequest(BaseModel):
    """One medicine line submitted by the prescribing doctor."""

    medicine_name: str = Field(min_length=2, max_length=160)
    dosage: str = Field(min_length=1, max_length=60)
    frequency: str = Field(min_length=1, max_length=60)
    duration: str = Field(min_length=1, max_length=60)
    instructions: str | None = Field(default=None, max_length=500)


class CreatePrescriptionRequest(BaseModel):
    """Payload for creating a prescription draft (FR-D1)."""

    patient_id: int = Field(gt=0)
    diagnosis: str = Field(min_length=3)
    items: list[PrescriptionItemRequest] = Field(min_length=1)
    advice: str | None = None
    appointment_id: int | None = None
    record_id: int | None = None
    valid_days: int = Field(default=30, ge=1, le=180)


class UpdatePrescriptionRequest(BaseModel):
    """Payload for editing a draft before it is issued."""

    diagnosis: str | None = Field(default=None, min_length=3)
    advice: str | None = None
    items: list[PrescriptionItemRequest] | None = Field(default=None, min_length=1)


class DispensePrescriptionRequest(BaseModel):
    """Payload for recording a pharmacy dispensing event."""

    note: str | None = Field(default=None, max_length=500)


class PrescriptionItemResponse(ORMModel):
    """One medicine line as returned to the client."""

    id: int
    medicine_name: str
    dosage: str
    frequency: str
    duration: str
    instructions: str | None = None


class PrescriptionResponse(ORMModel):
    """A prescription as returned to the doctor, patient or pharmacist."""

    id: int
    reference_code: str
    patient_id: int
    doctor_id: int
    appointment_id: int | None = None
    record_id: int | None = None
    diagnosis: str
    advice: str | None = None
    status: str
    issued_at: datetime | None = None
    valid_until: date | None = None
    dispensed_at: datetime | None = None
    pharmacist_note: str | None = None
    items: list[PrescriptionItemResponse] = []

    patient_name: str | None = None
    patient_university_id: str | None = None
    doctor_name: str | None = None
    dispensed_by_name: str | None = None
