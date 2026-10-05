"""Business rules for appointment booking and scheduling (FR-C1 to FR-C3, FR-C7)."""

from datetime import date, datetime, time, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.constants import PATIENT_ROLES, AccountStatus, AppointmentStatus, UserRole
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.core.utils import get_or_404
from app.models.appointment import Appointment
from app.models.doctor_profile import DoctorProfile
from app.models.user import User
from app.schemas.appointment import BookRequest

OPENS, CLOSES, BREAK = 9 * 60, 17 * 60, (13 * 60, 14 * 60)  # minutes since midnight
MAX_ADVANCE_DAYS = 30
ACTIVE = (AppointmentStatus.BOOKED.value, AppointmentStatus.CONFIRMED.value)
TRANSITIONS = {"booked": {"confirmed", "cancelled"}, "confirmed": {"completed", "no_show", "cancelled"}}  # FR-C7


def _t(minutes: int) -> time:
    """Convert minutes since midnight to a ``time``."""
    return time(minutes // 60, minutes % 60)


def slot_grid(length: int) -> list[tuple[time, time]]:
    """Build the day's slots from a consultation length, skipping the lunch break."""
    if length <= 0:
        raise ValidationError("The consultation length must be positive.")
    slots, cursor = [], OPENS
    while cursor + length <= CLOSES:
        if cursor < BREAK[1] and cursor + length > BREAK[0]:
            cursor = BREAK[1]
            continue
        slots.append((_t(cursor), _t(cursor + length)))
        cursor += length
    return slots


def _doctor(db: Session, doctor_id: int) -> tuple[User, DoctorProfile | None]:
    """Load an active doctor with their profile."""
    doctor = db.get(User, doctor_id)
    if doctor is None or doctor.role != UserRole.DOCTOR.value or doctor.status != AccountStatus.ACTIVE.value:
        raise NotFoundError("That doctor was not found.")
    return doctor, db.query(DoctorProfile).filter_by(user_id=doctor_id).first()


def list_doctors(db: Session) -> list[dict]:
    """List active doctors for the booking search (FR-C1)."""
    rows = db.query(User, DoctorProfile).outerjoin(DoctorProfile, DoctorProfile.user_id == User.id).filter(
        User.role == UserRole.DOCTOR.value, User.status == AccountStatus.ACTIVE.value
    ).order_by(User.full_name).all()
    return [
        {"doctor_id": u.id, "full_name": u.full_name, "speciality": p.speciality if p else "General Medicine",
         "room_number": p.room_number if p else None}
        for u, p in rows
    ]


def _check_day(day: date) -> None:
    """Reject past dates, dates beyond the booking window and closed Fridays."""
    today = date.today()
    if day < today:
        raise ValidationError("Appointments cannot be booked for a past date.")
    if day > today + timedelta(days=MAX_ADVANCE_DAYS):
        raise ValidationError(f"Appointments can be booked up to {MAX_ADVANCE_DAYS} days ahead.")
    if day.weekday() == 4:
        raise ValidationError("The medical centre is closed on Friday.")


def _taken(db: Session, doctor_id: int, day: date, start: time, exclude: int | None = None) -> bool:
    """Report whether a doctor already has an active booking in that slot."""
    query = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id, Appointment.appointment_date == day,
        Appointment.start_time == start, Appointment.status.in_(ACTIVE),
    )
    return (query.filter(Appointment.id != exclude) if exclude else query).first() is not None


def _slot(db: Session, doctor_id: int, day: date, start: time) -> time:
    """Validate a requested slot and return its end time."""
    _check_day(day)
    _, profile = _doctor(db, doctor_id)
    grid = dict(slot_grid(profile.consultation_minutes if profile else 20))
    if start not in grid:
        raise ValidationError("That time is not one of the doctor's consultation slots.")
    if day == date.today() and start <= datetime.now().time():
        raise ValidationError("That slot has already started.")
    return grid[start]


def availability(db: Session, doctor_id: int, day: date) -> dict:
    """Return the slot grid for one doctor and date, marking taken slots (FR-C1, FR-C2)."""
    _check_day(day)
    _, profile = _doctor(db, doctor_id)
    now = datetime.now()
    slots = [
        {"start_time": s.strftime("%H:%M"), "end_time": e.strftime("%H:%M"),
         "available": not _taken(db, doctor_id, day, s) and not (day == now.date() and s <= now.time())}
        for s, e in slot_grid(profile.consultation_minutes if profile else 20)
    ]
    return {"doctor_id": doctor_id, "appointment_date": day, "slots": slots}


def book(db: Session, patient: User, payload: BookRequest) -> Appointment:
    """Book a slot (FR-C1) while preventing double booking (FR-C2)."""
    if UserRole(patient.role) not in PATIENT_ROLES:
        raise PermissionDeniedError("Only students and faculty or staff can book an appointment.")
    day, end = payload.appointment_date, _slot(db, payload.doctor_id, payload.appointment_date, payload.start_time)
    if _taken(db, payload.doctor_id, day, payload.start_time):
        raise ConflictError("That slot has just been booked. Choose another time.")
    if db.query(Appointment).filter(
        Appointment.patient_id == patient.id, Appointment.doctor_id == payload.doctor_id,
        Appointment.appointment_date == day, Appointment.status.in_(ACTIVE),
    ).first():
        raise ConflictError("You already have an appointment with this doctor on that date.")
    appointment = Appointment(patient_id=patient.id, end_time=end, **payload.model_dump())
    db.add(appointment)
    try:
        db.commit()  # the partial unique index is the final guard against a concurrent booking
    except IntegrityError:
        db.rollback()
        raise ConflictError("That slot has just been booked. Choose another time.") from None
    return appointment


def _owned(db: Session, appointment_id: int, user: User) -> Appointment:
    """Load an appointment the user may touch: its patient, its doctor, or an admin."""
    appointment = get_or_404(db, Appointment, appointment_id, "That appointment was not found.")
    if user.id not in (appointment.patient_id, appointment.doctor_id) and user.role != UserRole.ADMIN.value:
        raise PermissionDeniedError("You do not have access to this appointment.")
    return appointment


def mine(db: Session, patient: User) -> list[Appointment]:
    """List the patient's own bookings, newest first."""
    return db.query(Appointment).filter_by(patient_id=patient.id).order_by(
        Appointment.appointment_date.desc(), Appointment.start_time.desc()).all()


def schedule(db: Session, doctor: User, day: date | None = None) -> list[Appointment]:
    """List a doctor's bookings, optionally for one day (FR-C7)."""
    query = db.query(Appointment).filter_by(doctor_id=doctor.id)
    return (query.filter_by(appointment_date=day) if day else query).order_by(
        Appointment.appointment_date, Appointment.start_time).all()


def reschedule(db: Session, appointment_id: int, patient: User, day: date, start: time) -> Appointment:
    """Move a booking until the doctor confirms it (FR-C3)."""
    appointment = _owned(db, appointment_id, patient)
    if appointment.patient_id != patient.id or appointment.status != AppointmentStatus.BOOKED.value:
        raise ValidationError("Only your own, unconfirmed appointment can be rescheduled.")
    end = _slot(db, appointment.doctor_id, day, start)
    if _taken(db, appointment.doctor_id, day, start, exclude=appointment.id):
        raise ConflictError("That slot is already booked. Choose another time.")
    appointment.appointment_date, appointment.start_time, appointment.end_time = day, start, end
    db.commit()
    return appointment


def cancel(db: Session, appointment_id: int, user: User, reason: str | None = None) -> Appointment:
    """Cancel a booking; a patient may do so only before confirmation (FR-C3)."""
    appointment = _owned(db, appointment_id, user)
    if appointment.status in (AppointmentStatus.CANCELLED.value, AppointmentStatus.COMPLETED.value):
        raise ValidationError("This appointment can no longer be cancelled.")
    if user.id == appointment.patient_id and appointment.status != AppointmentStatus.BOOKED.value:
        raise ValidationError("The doctor has confirmed this appointment. Contact the medical centre.")
    appointment.status, appointment.cancelled_reason = AppointmentStatus.CANCELLED.value, reason
    db.commit()
    return appointment


def set_status(db: Session, appointment_id: int, doctor: User, new: AppointmentStatus) -> Appointment:
    """Let the assigned doctor confirm, complete or mark a no-show (FR-C7)."""
    appointment = _owned(db, appointment_id, doctor)
    if appointment.doctor_id != doctor.id:
        raise PermissionDeniedError("Only the assigned doctor can update this appointment.")
    if new.value not in TRANSITIONS.get(appointment.status, set()):
        raise ValidationError(f"An appointment cannot move from {appointment.status} to {new.value}.")
    appointment.status = new.value
    db.commit()
    return appointment


def to_dict(db: Session, appointment: Appointment) -> dict:
    """Expand an appointment with the names the screens need."""
    fields = ("id", "patient_id", "doctor_id", "appointment_date", "start_time", "end_time",
              "reason", "visit_type", "status", "cancelled_reason")
    profile = db.query(DoctorProfile).filter_by(user_id=appointment.doctor_id).first()
    return {f: getattr(appointment, f) for f in fields} | {
        "patient_name": db.get(User, appointment.patient_id).full_name,
        "doctor_name": db.get(User, appointment.doctor_id).full_name,
        "doctor_speciality": profile.speciality if profile else None,
    }
