"""Digital prescription models (FR-D1, FR-D3): a header row plus one row per medicine."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import PrescriptionStatus
from app.core.database import Base
from app.models.user import utc_now


class Prescription(Base):
    """A prescription that moves draft -> issued -> dispensed."""

    __tablename__ = "prescriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"))
    record_id: Mapped[int | None] = mapped_column(Integer)  # plain id: no FK keeps features independent
    diagnosis: Mapped[str] = mapped_column(Text)
    advice: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=PrescriptionStatus.DRAFT.value, index=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[date | None] = mapped_column(Date)
    dispensed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    dispensed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pharmacist_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    items: Mapped[list["PrescriptionItem"]] = relationship(
        back_populates="prescription", cascade="all, delete-orphan", order_by="PrescriptionItem.id")


class PrescriptionItem(Base):
    """One medicine on a prescription."""

    __tablename__ = "prescription_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prescription_id: Mapped[int] = mapped_column(ForeignKey("prescriptions.id"), index=True)
    medicine_name: Mapped[str] = mapped_column(String(160))
    dosage: Mapped[str] = mapped_column(String(60))
    frequency: Mapped[str] = mapped_column(String(60))
    duration: Mapped[str] = mapped_column(String(60))
    instructions: Mapped[str | None] = mapped_column(Text)
    prescription: Mapped["Prescription"] = relationship(back_populates="items")
