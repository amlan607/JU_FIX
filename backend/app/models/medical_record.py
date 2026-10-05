"""Electronic Health Record models (FR-D2, FR-D5)."""

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.user import utc_now


class MedicalRecord(Base):
    """One clinical entry; ``version`` increments on every edit."""

    __tablename__ = "medical_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"))
    record_type: Mapped[str] = mapped_column(String(30), default="consultation")
    visit_date: Mapped[date] = mapped_column(Date)
    title: Mapped[str] = mapped_column(String(160))
    symptoms: Mapped[str | None] = mapped_column(Text)
    examination: Mapped[str | None] = mapped_column(Text)
    diagnosis: Mapped[str] = mapped_column(Text)
    treatment: Mapped[str | None] = mapped_column(Text)
    follow_up: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MedicalRecordVersion(Base):
    """Immutable snapshot of a record taken before an edit (FR-D5)."""

    __tablename__ = "medical_record_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("medical_records.id"), index=True)
    version_number: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(JSON)
    edited_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    change_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
