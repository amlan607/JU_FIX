"""Electronic Health Record models (FR-D2, FR-D5).

Two tables cooperate: ``medical_records`` holds the current state of a clinical
entry, and ``medical_record_versions`` holds an immutable snapshot of every
previous state so the audit trail required by FR-D5 is complete.
"""

from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import RecordType
from app.core.database import Base
from app.models.user import utc_now


class MedicalRecord(Base):
    """One clinical entry in a patient's health record.

    Attributes:
        patient_id: The patient the entry belongs to.
        doctor_id: The doctor who authored the entry.
        appointment_id: The consultation the entry came from, when there was one.
        record_type: One of :class:`~app.core.constants.RecordType`.
        is_confidential: Marks an entry that is hidden from ordinary listings.
        version: Increments on every edit and matches the latest version row.
    """

    __tablename__ = "medical_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    appointment_id: Mapped[int | None] = mapped_column(
        ForeignKey("appointments.id"), nullable=True, index=True
    )

    record_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default=RecordType.CONSULTATION.value, index=True
    )
    visit_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)

    symptoms: Mapped[str | None] = mapped_column(Text, nullable=True)
    examination: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    treatment: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_confidential: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    def __repr__(self) -> str:
        """Return a debug representation that excludes clinical content."""
        return f"<MedicalRecord id={self.id} patient={self.patient_id} version={self.version}>"


class MedicalRecordVersion(Base):
    """An immutable snapshot of a record as it was before an edit (FR-D5).

    Attributes:
        record_id: The record this snapshot belongs to.
        version_number: The version the snapshot captures.
        edited_by: The doctor who made the edit that created this snapshot.
        change_note: A short description of what the edit changed.
    """

    __tablename__ = "medical_record_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_id: Mapped[int] = mapped_column(
        ForeignKey("medical_records.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    symptoms: Mapped[str | None] = mapped_column(Text, nullable=True)
    examination: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    treatment: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    edited_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    change_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
