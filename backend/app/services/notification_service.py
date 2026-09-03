"""Business rules for notifications and reminders (FR-H1 to FR-H3)."""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.constants import AppointmentStatus, PrescriptionStatus
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.models.appointment import Appointment
from app.models.notification import Notification, ReminderDispatch
from app.models.prescription import Prescription
from app.models.user import User

CATEGORIES = {
    "appointment_reminder",
    "appointment_update",
    "medicine_reminder",
    "queue_update",
    "record_update",
    "certificate_update",
    "emergency",
    "security",
}
APPOINTMENT_REMINDER_OFFSETS = (("24h", 24), ("1h", 1))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def validate_category(category: str) -> str:
    """Reject unknown categories before persisting a notification."""
    if category not in CATEGORIES:
        raise ValidationError(f"Unknown notification category: {category}.")
    return category


def notify(
    db: Session,
    *,
    user_id: int,
    category: str,
    title: str,
    body: str,
    entity_type: str | None = None,
    entity_id: int | None = None,
    commit: bool = True,
) -> Notification:
    """Create one stored notification through the shared notification gateway."""
    validate_category(category)
    notification = Notification(
        user_id=user_id,
        category=category,
        title=title.strip(),
        body=body.strip(),
        entity_type=entity_type,
        entity_id=entity_id,
        sent_at=_utc_now(),
    )
    db.add(notification)
    if commit:
        db.commit()
        db.refresh(notification)
    else:
        db.flush()
    return notification


def notify_many(db: Session, user_ids, **kwargs) -> list[Notification]:
    """Create one notification per distinct recipient."""
    created = [
        notify(db, user_id=user_id, commit=False, **kwargs)
        for user_id in dict.fromkeys(user_ids)
    ]
    db.commit()
    return created


def list_for_user(
    db: Session, user: User, unread_only: bool = False, limit: int = 50
) -> dict:
    """Return a user's newest notifications and unread badge count."""
    query = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        query = query.filter(Notification.read_at.is_(None))
    notifications = query.order_by(Notification.id.desc()).limit(min(limit, 100)).all()
    unread_count = (
        db.query(func.count(Notification.id))
        .filter(Notification.user_id == user.id, Notification.read_at.is_(None))
        .scalar()
        or 0
    )
    return {"unread_count": unread_count, "notifications": notifications}


def mark_read(db: Session, notification_id: int, user: User) -> Notification:
    """Mark a notification read only when it belongs to the signed-in user."""
    notification = db.get(Notification, notification_id)
    if notification is None:
        raise NotFoundError("That notification was not found.")
    if notification.user_id != user.id:
        raise PermissionDeniedError("You can only read your own notifications.")
    if notification.read_at is None:
        notification.read_at = _utc_now()
        db.commit()
        db.refresh(notification)
    return notification


def mark_all_read(db: Session, user: User) -> int:
    """Mark every unread notification for a user as read."""
    unread = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.read_at.is_(None))
        .all()
    )
    now = _utc_now()
    for notification in unread:
        notification.read_at = now
    db.commit()
    return len(unread)


def _record_dispatch(db: Session, entity_type: str, entity_id: int, label: str) -> bool:
    """Claim a reminder before creating its notification."""
    db.add(ReminderDispatch(entity_type=entity_type, entity_id=entity_id, offset_label=label))
    try:
        db.flush()
        return True
    except IntegrityError:
        db.rollback()
        return False


def run_appointment_reminders(db: Session, now: datetime | None = None) -> int:
    """Create each 24-hour and one-hour appointment reminder once."""
    moment = now or _utc_now()
    created = 0
    upcoming = (
        db.query(Appointment)
        .filter(
            Appointment.appointment_date >= moment.date(),
            Appointment.appointment_date <= moment.date() + timedelta(days=2),
            Appointment.status.in_([AppointmentStatus.BOOKED.value, AppointmentStatus.CONFIRMED.value]),
        )
        .all()
    )
    for appointment in upcoming:
        starts_at = datetime.combine(
            appointment.appointment_date, appointment.start_time, tzinfo=timezone.utc
        )
        hours_away = (starts_at - moment).total_seconds() / 3600
        for label, offset_hours in APPOINTMENT_REMINDER_OFFSETS:
            if not (0 < hours_away <= offset_hours):
                continue
            if not _record_dispatch(db, "appointment", appointment.id, label):
                continue
            doctor = db.get(User, appointment.doctor_id)
            when = appointment.start_time.strftime("%H:%M")
            notify(
                db,
                user_id=appointment.patient_id,
                category="appointment_reminder",
                title=f"Appointment in about {offset_hours} hour(s)",
                body=(
                    f"You have an appointment with {doctor.full_name if doctor else 'your doctor'} "
                    f"on {appointment.appointment_date} at {when}."
                ),
                entity_type="appointment",
                entity_id=appointment.id,
                commit=False,
            )
            created += 1
    db.commit()
    return created


def run_medicine_reminders(db: Session, now: datetime | None = None) -> int:
    """Create one daily reminder for every active prescription."""
    today: date = (now or _utc_now()).date()
    active = (
        db.query(Prescription)
        .filter(
            Prescription.status.in_([PrescriptionStatus.ISSUED.value, PrescriptionStatus.DISPENSED.value]),
            Prescription.valid_until >= today,
        )
        .all()
    )
    created = 0
    for prescription in active:
        if not _record_dispatch(db, "prescription", prescription.id, f"dose-{today.isoformat()}"):
            continue
        medicines = ", ".join(item.medicine_name for item in prescription.items[:3])
        notify(
            db,
            user_id=prescription.patient_id,
            category="medicine_reminder",
            title="Medicine reminder",
            body=(
                f"Prescription {prescription.reference_code} is still active today. "
                f"Remember to take: {medicines}."
            ),
            entity_type="prescription",
            entity_id=prescription.id,
            commit=False,
        )
        created += 1
    db.commit()
    return created


def run_all_reminders(db: Session, now: datetime | None = None) -> dict:
    """Run appointment and medicine reminder sweeps."""
    return {
        "appointment_reminders_created": run_appointment_reminders(db, now),
        "medicine_reminders_created": run_medicine_reminders(db, now),
        "checked_at": now or _utc_now(),
    }
