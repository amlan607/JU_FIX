"""Business rules for appointment booking and scheduling (FR-C1 to FR-C3).

Slot availability is derived from the clinic's opening hours and the doctor's own
consultation length, then filtered against existing bookings. No slot rows are
stored, so a change to opening hours or slot length takes effect immediately.
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.constants import PATIENT_ROLES, AccountStatus, AppointmentStatus, UserRole
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.models.appointment import Appointment
from app.models.doctor_profile import DoctorProfile
from app.models.user import User
from app.schemas.appointment import BookAppointmentRequest

#: Medical centre opening hours used to build the slot grid.
CLINIC_OPENS_AT = time(9, 0)
CLINIC_CLOSES_AT = time(17, 0)

#: Lunch break excluded from the bookable grid.
BREAK_STARTS_AT = time(13, 0)
BREAK_ENDS_AT = time(14, 0)

#: How far ahead a patient may book.
MAX_ADVANCE_DAYS = 30

#: Statuses a patient may still change (FR-C3).
PATIENT_EDITABLE_STATUSES = {AppointmentStatus.BOOKED.value}


def _to_minutes(value: time) -> int:
    """Convert a ``time`` to minutes since midnight."""
    return value.hour * 60 + value.minute


def _to_time(minutes: int) -> time:
    """Convert minutes since midnight back to a ``time``."""
    return time(hour=minutes // 60, minute=minutes % 60)


def build_slot_grid(slot_minutes: int) -> list[tuple[time, time]]:
    """Build the bookable slot grid for one clinic day.

    Args:
        slot_minutes: The doctor's consultation length in minutes.

    Returns:
        list[tuple[time, time]]: Ordered ``(start, end)`` pairs, excluding the break.

    Raises:
        ValidationError: When the slot length is not a positive number of minutes.
    """
    if slot_minutes <= 0:
        raise ValidationError("The consultation length must be a positive number of minutes.")

    grid: list[tuple[time, time]] = []
    cursor = _to_minutes(CLINIC_OPENS_AT)
    closing = _to_minutes(CLINIC_CLOSES_AT)
    break_start = _to_minutes(BREAK_STARTS_AT)
    break_end = _to_minutes(BREAK_ENDS_AT)

    while cursor + slot_minutes <= closing:
        slot_end = cursor + slot_minutes
        overlaps_break = cursor < break_end and slot_end > break_start
        if overlaps_break:
            cursor = break_end
            continue
        grid.append((_to_time(cursor), _to_time(slot_end)))
        cursor = slot_end

    return grid


def get_doctor_profile(db: Session, doctor_id: int) -> tuple[User, DoctorProfile]:
    """Load a doctor account together with its clinical profile.

    Args:
        db: The active database session.
        doctor_id: The doctor's user identifier.

    Returns:
        tuple[User, DoctorProfile]: The account and its profile.

    Raises:
        NotFoundError: When the account is missing, inactive or not a doctor.
    """
    doctor = db.get(User, doctor_id)
    if doctor is None or doctor.role != UserRole.DOCTOR.value:
        raise NotFoundError("That doctor was not found.")
    if doctor.status != AccountStatus.ACTIVE.value:
        raise NotFoundError("That doctor is not currently available.")

    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == doctor_id).first()
    if profile is None:
        # A doctor without a stored profile still gets the clinic default length.
        profile = DoctorProfile(user_id=doctor_id, speciality="General Medicine")

    return doctor, profile


def list_doctors(db: Session, speciality: str | None = None) -> list[dict]:
    """List doctors available for booking (FR-C1).

    Args:
        db: The active database session.
        speciality: Optional case insensitive speciality filter.

    Returns:
        list[dict]: One entry per bookable doctor.
    """
    query = (
        db.query(User, DoctorProfile)
        .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
        .filter(User.role == UserRole.DOCTOR.value, User.status == AccountStatus.ACTIVE.value)
    )
    if speciality:
        query = query.filter(func.lower(DoctorProfile.speciality).like(f"%{speciality.lower()}%"))

    results = []
    for doctor, profile in query.order_by(User.full_name).all():
        if profile is not None and not profile.accepts_appointments:
            continue
        results.append(
            {
                "doctor_id": doctor.id,
                "full_name": doctor.full_name,
                "speciality": profile.speciality if profile else "General Medicine",
                "room_number": profile.room_number if profile else None,
                "consultation_minutes": profile.consultation_minutes if profile else 20,
            }
        )
    return results


def _validate_booking_date(appointment_date: date) -> None:
    """Reject dates that are in the past, too far ahead, or on a Friday.

    Args:
        appointment_date: The requested date.

    Raises:
        ValidationError: When the date is not bookable.
    """
    today = datetime.now().date()
    if appointment_date < today:
        raise ValidationError("Appointments cannot be booked for a past date.")
    if appointment_date > today + timedelta(days=MAX_ADVANCE_DAYS):
        raise ValidationError(f"Appointments can be booked up to {MAX_ADVANCE_DAYS} days ahead.")
    if appointment_date.weekday() == 4:
        raise ValidationError("The medical centre is closed on Friday. Choose another date.")


def get_available_slots(db: Session, doctor_id: int, appointment_date: date) -> dict:
    """Return the slot grid for one doctor on one date (FR-C1, FR-C2).

    Args:
        db: The active database session.
        doctor_id: The doctor to check.
        appointment_date: The date to check.

    Returns:
        dict: The doctor summary, the date and every slot with its availability.
    """
    _validate_booking_date(appointment_date)
    doctor, profile = get_doctor_profile(db, doctor_id)

    taken = {
        row.start_time
        for row in db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == appointment_date,
            Appointment.status.notin_(
                [AppointmentStatus.CANCELLED.value, AppointmentStatus.NO_SHOW.value]
            ),
        )
        .all()
    }

    now = datetime.now()
    slots = []
    for start, end in build_slot_grid(profile.consultation_minutes):
        in_the_past = appointment_date == now.date() and start <= now.time()
        slots.append(
            {
                "start_time": start.strftime("%H:%M"),
                "end_time": end.strftime("%H:%M"),
                "available": start not in taken and not in_the_past,
            }
        )

    return {
        "doctor": {
            "doctor_id": doctor.id,
            "full_name": doctor.full_name,
            "speciality": profile.speciality,
            "room_number": profile.room_number,
            "consultation_minutes": profile.consultation_minutes,
        },
        "appointment_date": appointment_date,
        "slots": slots,
    }


def _require_patient(user: User) -> None:
    """Allow only student and faculty roles to book (FR-C1).

    Args:
        user: The signed in user.

    Raises:
        PermissionDeniedError: When the role may not book an appointment.
    """
    if UserRole(user.role) not in PATIENT_ROLES:
        raise PermissionDeniedError("Only students and faculty or staff can book an appointment.")


def book_appointment(db: Session, patient: User, payload: BookAppointmentRequest) -> Appointment:
    """Create a booking for the signed in patient (FR-C1, FR-C2).

    Args:
        db: The active database session.
        patient: The signed in student or faculty member.
        payload: The validated booking request.

    Returns:
        Appointment: The stored booking.

    Raises:
        ConflictError: When the slot is taken or the patient already has a booking that day.
        ValidationError: When the requested time is not part of the doctor's grid.
    """
    _require_patient(patient)
    _validate_booking_date(payload.appointment_date)
    _doctor, profile = get_doctor_profile(db, payload.doctor_id)

    grid = {start: end for start, end in build_slot_grid(profile.consultation_minutes)}
    if payload.start_time not in grid:
        raise ValidationError("That time is not one of the doctor's consultation slots.")

    if payload.appointment_date == datetime.now().date() and payload.start_time <= datetime.now().time():
        raise ValidationError("That slot has already started. Choose a later time.")

    active_statuses = [
        AppointmentStatus.BOOKED.value,
        AppointmentStatus.CONFIRMED.value,
    ]

    slot_taken = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == payload.doctor_id,
            Appointment.appointment_date == payload.appointment_date,
            Appointment.start_time == payload.start_time,
            Appointment.status.in_(active_statuses),
        )
        .first()
    )
    if slot_taken is not None:
        raise ConflictError("That slot has just been booked. Choose another time.")

    duplicate = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id == patient.id,
            Appointment.doctor_id == payload.doctor_id,
            Appointment.appointment_date == payload.appointment_date,
            Appointment.status.in_(active_statuses),
        )
        .first()
    )
    if duplicate is not None:
        raise ConflictError("You already have an appointment with this doctor on that date.")

    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=payload.doctor_id,
        appointment_date=payload.appointment_date,
        start_time=payload.start_time,
        end_time=grid[payload.start_time],
        reason=payload.reason.strip(),
        visit_type=payload.visit_type,
        status=AppointmentStatus.BOOKED.value,
    )
    db.add(appointment)

    record_audit(
        db,
        actor_id=patient.id,
        action="appointment.book",
        entity_type="appointment",
        summary=f"Booked doctor {payload.doctor_id} on {payload.appointment_date}.",
    )

    try:
        db.commit()
    except IntegrityError:
        # The unique constraint is the final guard against a concurrent booking.
        db.rollback()
        raise ConflictError("That slot has just been booked. Choose another time.") from None

    db.refresh(appointment)
    return appointment


def get_appointment_for_user(db: Session, appointment_id: int, user: User) -> Appointment:
    """Load an appointment the user is allowed to see.

    Args:
        db: The active database session.
        appointment_id: The booking identifier.
        user: The signed in user.

    Returns:
        Appointment: The requested booking.

    Raises:
        NotFoundError: When the booking does not exist.
        PermissionDeniedError: When the user is neither the patient, the doctor nor an admin.
    """
    appointment = db.get(Appointment, appointment_id)
    if appointment is None:
        raise NotFoundError("That appointment was not found.")

    is_owner = appointment.patient_id == user.id
    is_assigned_doctor = appointment.doctor_id == user.id
    is_admin = user.role == UserRole.ADMIN.value

    if not (is_owner or is_assigned_doctor or is_admin):
        raise PermissionDeniedError("You do not have access to this appointment.")

    return appointment


def list_appointments_for_patient(db: Session, patient: User, status: str | None = None) -> list[Appointment]:
    """List the signed in patient's own bookings.

    Args:
        db: The active database session.
        patient: The signed in patient.
        status: Optional status filter.

    Returns:
        list[Appointment]: Bookings, newest date first.
    """
    query = db.query(Appointment).filter(Appointment.patient_id == patient.id)
    if status:
        query = query.filter(Appointment.status == status)
    return query.order_by(Appointment.appointment_date.desc(), Appointment.start_time.desc()).all()


def list_appointments_for_doctor(
    db: Session, doctor: User, on_date: date | None = None
) -> list[Appointment]:
    """List the bookings assigned to a doctor.

    Args:
        db: The active database session.
        doctor: The signed in doctor.
        on_date: Optional date filter; defaults to every upcoming booking.

    Returns:
        list[Appointment]: Bookings ordered by date then start time.
    """
    query = db.query(Appointment).filter(Appointment.doctor_id == doctor.id)
    if on_date:
        query = query.filter(Appointment.appointment_date == on_date)
    return query.order_by(Appointment.appointment_date, Appointment.start_time).all()


def reschedule_appointment(
    db: Session, appointment_id: int, patient: User, new_date: date, new_start: time
) -> Appointment:
    """Move a booking to a different slot (FR-C3).

    Args:
        db: The active database session.
        appointment_id: The booking to move.
        patient: The signed in patient.
        new_date: The new date.
        new_start: The new start time.

    Returns:
        Appointment: The updated booking.

    Raises:
        PermissionDeniedError: When the signed in user does not own the booking.
        ValidationError: When the booking is no longer patient editable.
        ConflictError: When the target slot is already taken.
    """
    appointment = get_appointment_for_user(db, appointment_id, patient)

    if appointment.patient_id != patient.id:
        raise PermissionDeniedError("Only the patient who booked can reschedule this appointment.")

    if appointment.status not in PATIENT_EDITABLE_STATUSES:
        raise ValidationError(
            "This appointment can no longer be rescheduled because the doctor has confirmed it."
        )

    _validate_booking_date(new_date)
    _doctor, profile = get_doctor_profile(db, appointment.doctor_id)

    grid = {start: end for start, end in build_slot_grid(profile.consultation_minutes)}
    if new_start not in grid:
        raise ValidationError("That time is not one of the doctor's consultation slots.")

    clash = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == appointment.doctor_id,
            Appointment.appointment_date == new_date,
            Appointment.start_time == new_start,
            Appointment.id != appointment.id,
            Appointment.status.in_([AppointmentStatus.BOOKED.value, AppointmentStatus.CONFIRMED.value]),
        )
        .first()
    )
    if clash is not None:
        raise ConflictError("That slot is already booked. Choose another time.")

    appointment.appointment_date = new_date
    appointment.start_time = new_start
    appointment.end_time = grid[new_start]

    record_audit(
        db,
        actor_id=patient.id,
        action="appointment.reschedule",
        entity_type="appointment",
        entity_id=appointment.id,
        summary=f"Moved to {new_date} {new_start}.",
    )
    db.commit()
    db.refresh(appointment)
    return appointment


def cancel_appointment(
    db: Session, appointment_id: int, user: User, reason: str | None = None
) -> Appointment:
    """Cancel a booking (FR-C3).

    A patient may cancel their own booking before the doctor confirms it. The
    assigned doctor and an administrator may cancel at any point.

    Args:
        db: The active database session.
        appointment_id: The booking to cancel.
        user: The signed in user.
        reason: Optional free text reason.

    Returns:
        Appointment: The cancelled booking.

    Raises:
        ValidationError: When the booking is already cancelled or completed, or
            when a patient tries to cancel a confirmed booking.
    """
    appointment = get_appointment_for_user(db, appointment_id, user)

    if appointment.status in {AppointmentStatus.CANCELLED.value, AppointmentStatus.COMPLETED.value}:
        raise ValidationError("This appointment can no longer be cancelled.")

    is_patient = appointment.patient_id == user.id
    if is_patient and appointment.status not in PATIENT_EDITABLE_STATUSES:
        raise ValidationError(
            "The doctor has confirmed this appointment. Contact the medical centre to cancel it."
        )

    appointment.status = AppointmentStatus.CANCELLED.value
    appointment.cancelled_reason = (reason or "").strip() or None

    record_audit(
        db,
        actor_id=user.id,
        action="appointment.cancel",
        entity_type="appointment",
        entity_id=appointment.id,
        summary="Appointment cancelled.",
    )
    db.commit()
    db.refresh(appointment)
    return appointment


def update_status(db: Session, appointment_id: int, doctor: User, new_status: AppointmentStatus) -> Appointment:
    """Let the assigned doctor advance the booking status (FR-C7).

    Args:
        db: The active database session.
        appointment_id: The booking to update.
        doctor: The signed in doctor.
        new_status: The target status.

    Returns:
        Appointment: The updated booking.

    Raises:
        PermissionDeniedError: When the doctor is not assigned to the booking.
        ValidationError: When the transition is not allowed.
    """
    appointment = get_appointment_for_user(db, appointment_id, doctor)

    if appointment.doctor_id != doctor.id:
        raise PermissionDeniedError("Only the assigned doctor can update this appointment.")

    allowed = {
        AppointmentStatus.BOOKED.value: {
            AppointmentStatus.CONFIRMED.value,
            AppointmentStatus.CANCELLED.value,
        },
        AppointmentStatus.CONFIRMED.value: {
            AppointmentStatus.COMPLETED.value,
            AppointmentStatus.NO_SHOW.value,
            AppointmentStatus.CANCELLED.value,
        },
    }
    if new_status.value not in allowed.get(appointment.status, set()):
        raise ValidationError(
            f"An appointment cannot move from {appointment.status} to {new_status.value}."
        )

    appointment.status = new_status.value

    record_audit(
        db,
        actor_id=doctor.id,
        action="appointment.status_change",
        entity_type="appointment",
        entity_id=appointment.id,
        summary=f"Status set to {new_status.value}.",
    )
    db.commit()
    db.refresh(appointment)
    return appointment


def to_response_dict(db: Session, appointment: Appointment) -> dict:
    """Expand an appointment row with the names the UI needs.

    Args:
        db: The active database session.
        appointment: The booking to expand.

    Returns:
        dict: Booking fields plus patient name, doctor name and room.
    """
    patient = db.get(User, appointment.patient_id)
    doctor = db.get(User, appointment.doctor_id)
    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == appointment.doctor_id).first()

    return {
        "id": appointment.id,
        "patient_id": appointment.patient_id,
        "doctor_id": appointment.doctor_id,
        "appointment_date": appointment.appointment_date,
        "start_time": appointment.start_time,
        "end_time": appointment.end_time,
        "reason": appointment.reason,
        "visit_type": appointment.visit_type,
        "status": appointment.status,
        "cancelled_reason": appointment.cancelled_reason,
        "patient_name": patient.full_name if patient else None,
        "doctor_name": doctor.full_name if doctor else None,
        "doctor_speciality": profile.speciality if profile else None,
        "room_number": profile.room_number if profile else None,
    }
