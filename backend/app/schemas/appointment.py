"""Request and response schemas for appointment booking (FR-C)."""

from datetime import date, time

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class DoctorSummary(BaseModel):
    """A doctor as shown on the appointment search screen.

    Attributes:
        doctor_id: The user identifier of the doctor.
        full_name: The doctor's display name.
        speciality: The clinical speciality used to filter search results.
        room_number: The consultation room.
        consultation_minutes: Slot length used to build the slot grid.
    """

    doctor_id: int
    full_name: str
    speciality: str
    room_number: str | None = None
    consultation_minutes: int


class SlotOption(BaseModel):
    """One bookable slot in the doctor's day.

    Attributes:
        start_time: Slot start in ``HH:MM`` form.
        end_time: Slot end in ``HH:MM`` form.
        available: ``False`` when the slot is already booked (FR-C2).
    """

    start_time: str
    end_time: str
    available: bool


class SlotAvailabilityResponse(BaseModel):
    """The full slot grid for one doctor on one date."""

    doctor: DoctorSummary
    appointment_date: date
    slots: list[SlotOption]


class BookAppointmentRequest(BaseModel):
    """Payload for creating a booking (FR-C1)."""

    doctor_id: int = Field(gt=0)
    appointment_date: date
    start_time: time
    reason: str = Field(min_length=3, max_length=500)
    visit_type: str = Field(default="consultation", max_length=30)


class RescheduleAppointmentRequest(BaseModel):
    """Payload for moving a booking to a different slot (FR-C3)."""

    appointment_date: date
    start_time: time


class CancelAppointmentRequest(BaseModel):
    """Payload for cancelling a booking (FR-C3)."""

    reason: str | None = Field(default=None, max_length=500)


class AppointmentResponse(ORMModel):
    """An appointment as returned to the patient or the doctor."""

    id: int
    patient_id: int
    doctor_id: int
    appointment_date: date
    start_time: time
    end_time: time
    reason: str
    visit_type: str
    status: str
    cancelled_reason: str | None = None

    patient_name: str | None = None
    doctor_name: str | None = None
    doctor_speciality: str | None = None
    room_number: str | None = None
