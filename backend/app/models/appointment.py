"""Appointment model (FR-C1 to FR-C3).

A partial unique index on doctor, date and start time enforces FR-C2 at the
database level, so a race between two concurrent bookings cannot create a double
booking even if both pass the service level check.

The index is restricted to active statuses. A cancelled or no-show booking must
leave the slot free for someone else, which a plain unique constraint would
prevent.
"""

from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, Time, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import AppointmentStatus
from app.core.database import Base
from app.models.user import utc_now


class Appointment(Base):
    """A booked consultation between a patient and a doctor.

    Attributes:
        patient_id: The student or faculty member attending.
        doctor_id: The doctor delivering the consultation.
        appointment_date: The calendar date of the consultation.
        start_time: The start of the reserved slot.
        end_time: The end of the reserved slot.
        reason: Why the patient is attending (FR-C1).
        status: One of :class:`~app.core.constants.AppointmentStatus`.
        cancelled_reason: Free text recorded when a booking is cancelled.
    """

    __tablename__ = "appointments"
    __table_args__ = (
        Index(
            "uq_appointment_doctor_active_slot",
            "doctor_id",
            "appointment_date",
            "start_time",
            unique=True,
            sqlite_where=text("status IN ('booked', 'confirmed')"),
            postgresql_where=text("status IN ('booked', 'confirmed')"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    appointment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)

    reason: Mapped[str] = mapped_column(Text, nullable=False)
    visit_type: Mapped[str] = mapped_column(String(30), nullable=False, default="consultation")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AppointmentStatus.BOOKED.value, index=True
    )
    cancelled_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    def __repr__(self) -> str:
        """Return a debug representation without clinical detail."""
        return (
            f"<Appointment id={self.id} doctor={self.doctor_id} "
            f"date={self.appointment_date} start={self.start_time} status={self.status}>"
        )
