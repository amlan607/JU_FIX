"""Doctor specific profile data used by booking and roster features."""

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DoctorProfile(Base):
    """Clinical profile attached to a user whose role is ``doctor``.

    Attributes:
        speciality: The clinical speciality shown on the booking screen.
        room_number: The consultation room used for the queue display.
        consultation_minutes: Slot length for this doctor, overriding the default.
        accepts_appointments: Whether the doctor currently appears in search results.
    """

    __tablename__ = "doctor_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False, index=True)
    speciality: Mapped[str] = mapped_column(String(120), nullable=False, default="General Medicine")
    room_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    consultation_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    accepts_appointments: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
