"""HTTP controller for appointment booking and scheduling (FR-C)."""

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.constants import AppointmentStatus, UserRole
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.responses import success_response
from app.models.user import User
from app.schemas.appointment import (
    BookAppointmentRequest,
    CancelAppointmentRequest,
    RescheduleAppointmentRequest,
)
from app.services import appointment_service

router = APIRouter(prefix="/appointments", tags=["Appointment Booking and Scheduling"])


@router.get("/doctors")
def list_doctors(
    speciality: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """List the doctors a patient can book (FR-C1)."""
    return success_response(appointment_service.list_doctors(db, speciality))


@router.get("/availability")
def get_availability(
    doctor_id: int = Query(gt=0),
    appointment_date: date = Query(alias="date"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """Return the slot grid for one doctor on one date (FR-C1, FR-C2)."""
    return success_response(appointment_service.get_available_slots(db, doctor_id, appointment_date))


@router.post("", status_code=status.HTTP_201_CREATED)
def book_appointment(
    payload: BookAppointmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT, UserRole.FACULTY)),
) -> dict:
    """Book a consultation slot for the signed in patient (FR-C1, FR-C2)."""
    appointment = appointment_service.book_appointment(db, current_user, payload)
    return success_response(appointment_service.to_response_dict(db, appointment))


@router.get("")
def list_my_appointments(
    appointment_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT, UserRole.FACULTY)),
) -> dict:
    """List the signed in patient's own bookings (FR-C3)."""
    appointments = appointment_service.list_appointments_for_patient(db, current_user, appointment_status)
    return success_response(
        [appointment_service.to_response_dict(db, item) for item in appointments]
    )


@router.get("/doctor-schedule")
def list_doctor_schedule(
    on_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR)),
) -> dict:
    """List the bookings assigned to the signed in doctor (FR-C7)."""
    appointments = appointment_service.list_appointments_for_doctor(db, current_user, on_date)
    return success_response(
        [appointment_service.to_response_dict(db, item) for item in appointments]
    )


@router.get("/{appointment_id}")
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return one booking the signed in user is allowed to see."""
    appointment = appointment_service.get_appointment_for_user(db, appointment_id, current_user)
    return success_response(appointment_service.to_response_dict(db, appointment))


@router.patch("/{appointment_id}/reschedule")
def reschedule_appointment(
    appointment_id: int,
    payload: RescheduleAppointmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT, UserRole.FACULTY)),
) -> dict:
    """Move a booking to a different slot before the doctor confirms it (FR-C3)."""
    appointment = appointment_service.reschedule_appointment(
        db, appointment_id, current_user, payload.appointment_date, payload.start_time
    )
    return success_response(appointment_service.to_response_dict(db, appointment))


@router.patch("/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: int,
    payload: CancelAppointmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Cancel a booking (FR-C3)."""
    appointment = appointment_service.cancel_appointment(
        db, appointment_id, current_user, payload.reason
    )
    return success_response(appointment_service.to_response_dict(db, appointment))


@router.patch("/{appointment_id}/status")
def update_appointment_status(
    appointment_id: int,
    new_status: AppointmentStatus = Query(alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR)),
) -> dict:
    """Let the assigned doctor confirm, complete or mark a no show (FR-C7)."""
    appointment = appointment_service.update_status(db, appointment_id, current_user, new_status)
    return success_response(appointment_service.to_response_dict(db, appointment))
