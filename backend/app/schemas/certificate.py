"""Request and response schemas for medical certificates (FR-F1 to FR-F4)."""

from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ORMModel


class CreateCertificateRequest(BaseModel):
    """Payload for requesting a certificate after a consultation (FR-F1)."""

    appointment_id: int = Field(gt=0)
    reason: str = Field(min_length=5, max_length=1000)
    leave_start: date
    leave_end: date

    @model_validator(mode="after")
    def check_leave_window(self) -> "CreateCertificateRequest":
        """Reject a leave period that ends before it starts."""
        if self.leave_end < self.leave_start:
            raise ValueError("The leave end date cannot be before the start date.")
        return self


class DecideCertificateRequest(BaseModel):
    """Payload for a doctor's approval or rejection decision (FR-F2)."""

    approve: bool
    remarks: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def require_remarks_on_rejection(self) -> "DecideCertificateRequest":
        """FR-F2 requires a reason whenever a request is refused."""
        if not self.approve and not (self.remarks or "").strip():
            raise ValueError("Provide remarks explaining why the request is rejected.")
        return self


class CertificateResponse(ORMModel):
    """A certificate request as returned to the patient or the doctor."""

    id: int
    reference_id: str | None = None
    patient_id: int
    doctor_id: int
    appointment_id: int
    reason: str
    leave_start: date
    leave_end: date
    leave_days: int
    status: str
    doctor_remarks: str | None = None
    decided_at: datetime | None = None
    created_at: datetime | None = None

    patient_name: str | None = None
    patient_university_id: str | None = None
    doctor_name: str | None = None


class VerificationResponse(BaseModel):
    """The public verification result for a certificate reference (FR-F4).

    The payload deliberately excludes the medical reason. Verification confirms
    that a valid certificate exists and covers the stated dates, and nothing more.
    """

    valid: bool
    reference_id: str | None = None
    patient_name: str | None = None
    patient_university_id: str | None = None
    issued_by: str | None = None
    leave_start: date | None = None
    leave_end: date | None = None
    leave_days: int | None = None
    issued_on: datetime | None = None
    message: str
