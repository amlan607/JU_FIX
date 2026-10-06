"""Digital prescription models (FR-D1, FR-D3).

A prescription is a header row plus one row per medicine. Splitting the items
into their own table keeps each medicine individually queryable, which the
pharmacy dispensing screen needs, and avoids storing a delimited string.
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import PrescriptionStatus
from app.core.database import Base
from app.models.user import utc_now


class Prescription(Base):
    """A prescription issued by a doctor to a patient.

    Attributes:
        reference_code: Human readable identifier printed on the prescription.
        status: One of :class:`~app.core.constants.PrescriptionStatus`.
        issued_at: Set when the doctor issues the draft to the patient.
        dispensed_by: The pharmacist who dispensed the medicines.
        valid_until: Last date the prescription may be dispensed.
    """

    __tablename__ = "prescriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference_code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)

    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    appointment_id: Mapped[int | None] = mapped_column(
        ForeignKey("appointments.id"), nullable=True, index=True
    )
    record_id: Mapped[int | None] = mapped_column(
        ForeignKey("medical_records.id"), nullable=True, index=True
    )

    diagnosis: Mapped[str] = mapped_column(Text, nullable=False)
    advice: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PrescriptionStatus.DRAFT.value, index=True
    )
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    dispensed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    dispensed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pharmacist_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    items: Mapped[list["PrescriptionItem"]] = relationship(
        back_populates="prescription",
        cascade="all, delete-orphan",
        order_by="PrescriptionItem.id",
    )

    def __repr__(self) -> str:
        """Return a debug representation without clinical content."""
        return f"<Prescription {self.reference_code} status={self.status}>"


class PrescriptionItem(Base):
    """One medicine on a prescription.

    Attributes:
        medicine_name: The prescribed medicine.
        dosage: Strength per dose, for example ``500mg``.
        frequency: How often the dose is taken, for example ``1+0+1``.
        duration: How long the course lasts, for example ``7 days``.
        instructions: Free text guidance such as ``after meals``.
    """

    __tablename__ = "prescription_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prescription_id: Mapped[int] = mapped_column(
        ForeignKey("prescriptions.id"), nullable=False, index=True
    )

    medicine_name: Mapped[str] = mapped_column(String(160), nullable=False)
    dosage: Mapped[str] = mapped_column(String(60), nullable=False)
    frequency: Mapped[str] = mapped_column(String(60), nullable=False)
    duration: Mapped[str] = mapped_column(String(60), nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    prescription: Mapped["Prescription"] = relationship(back_populates="items")
