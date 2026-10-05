"""HTTP controller for appointment booking and scheduling (FR-C1 to FR-C3, FR-C7)."""

from datetime import date

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.constants import AppointmentStatus, UserRole
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.responses import success_response as ok
from app.models.user import User
from app.schemas.appointment import BookRequest, CancelRequest, RescheduleRequest
from app.services import appointment_service as service

router = APIRouter(prefix="/appointments", tags=["Appointment Booking and Scheduling"])
Patient = Depends(require_roles(UserRole.STUDENT, UserRole.FACULTY))
Doctor = Depends(require_roles(UserRole.DOCTOR))


@router.get("/doctors")
def doctors(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    """List bookable doctors (FR-C1)."""
    return ok(service.list_doctors(db))


@router.get("/availability")
def availability(doctor_id: int = Query(gt=0), day: date = Query(alias="date"),
                 db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    """Return the slot grid for a doctor and date (FR-C1, FR-C2)."""
    return ok(service.availability(db, doctor_id, day))


@router.post("", status_code=status.HTTP_201_CREATED)
def book(payload: BookRequest, db: Session = Depends(get_db), user: User = Patient) -> dict:
    """Book a slot for the signed in patient (FR-C1, FR-C2)."""
    return ok(service.to_dict(db, service.book(db, user, payload)))


@router.get("")
def mine(db: Session = Depends(get_db), user: User = Patient) -> dict:
    """List the signed in patient's bookings (FR-C3)."""
    return ok([service.to_dict(db, a) for a in service.mine(db, user)])


@router.get("/doctor-schedule")
def schedule(day: date | None = Query(default=None, alias="date"), db: Session = Depends(get_db),
             user: User = Doctor) -> dict:
    """List the signed in doctor's bookings (FR-C7)."""
    return ok([service.to_dict(db, a) for a in service.schedule(db, user, day)])


@router.patch("/{appointment_id}/reschedule")
def reschedule(appointment_id: int, payload: RescheduleRequest, db: Session = Depends(get_db),
               user: User = Patient) -> dict:
    """Move a booking before the doctor confirms it (FR-C3)."""
    appointment = service.reschedule(db, appointment_id, user, payload.appointment_date, payload.start_time)
    return ok(service.to_dict(db, appointment))


@router.patch("/{appointment_id}/cancel")
def cancel(appointment_id: int, payload: CancelRequest, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)) -> dict:
    """Cancel a booking (FR-C3)."""
    return ok(service.to_dict(db, service.cancel(db, appointment_id, user, payload.reason)))


@router.patch("/{appointment_id}/status")
def set_status(appointment_id: int, new: AppointmentStatus = Query(alias="status"),
               db: Session = Depends(get_db), user: User = Doctor) -> dict:
    """Confirm, complete or mark a no-show as the assigned doctor (FR-C7)."""
    return ok(service.to_dict(db, service.set_status(db, appointment_id, user, new)))
