"""Request schemas for digital prescriptions (FR-D1, FR-D3)."""

from pydantic import BaseModel, Field


class PrescriptionItemRequest(BaseModel):
    """One medicine line written by the doctor."""

    medicine_name: str = Field(min_length=2, max_length=160)
    dosage: str = Field(min_length=1, max_length=60)
    frequency: str = Field(min_length=1, max_length=60)
    duration: str = Field(min_length=1, max_length=60)
    instructions: str | None = Field(default=None, max_length=500)


class CreatePrescriptionRequest(BaseModel):
    """Payload for a prescription draft; at least one medicine is required (FR-D1)."""

    patient_id: int = Field(gt=0)
    diagnosis: str = Field(min_length=3)
    items: list[PrescriptionItemRequest] = Field(min_length=1)
    advice: str | None = None
    appointment_id: int | None = None
    record_id: int | None = None
    valid_days: int = Field(default=30, ge=1, le=180)


class UpdatePrescriptionRequest(BaseModel):
    """Draft edit payload (kept so later sprints can extend the service without schema changes)."""

    diagnosis: str | None = Field(default=None, min_length=3)
    advice: str | None = None
    items: list[PrescriptionItemRequest] | None = Field(default=None, min_length=1)


class DispenseRequest(BaseModel):
    """Optional pharmacy counter note."""

    note: str | None = Field(default=None, max_length=500)
