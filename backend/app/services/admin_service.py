"""Business rules for the admin dashboard and reporting (FR-J1 to FR-J5).

Reports return counts and workload only. Administrators never see diagnoses,
prescriptions or certificate reasons (least privilege, NFR-B).
"""

from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.config import settings
from app.core.constants import ROLES_REQUIRING_APPROVAL, AccountStatus, AppointmentStatus, UserRole
from app.core.errors import ValidationError
from app.core.utils import get_or_404, utc_now
from app.models.appointment import Appointment
from app.models.doctor_profile import DoctorProfile
from app.models.system_setting import SystemSetting
from app.models.user import User

ACTIVE, SUSPENDED, PENDING = (s.value for s in (AccountStatus.ACTIVE, AccountStatus.SUSPENDED, AccountStatus.PENDING_APPROVAL))
DEFAULTS = {"daily_token_limit": settings.DEFAULT_DAILY_TOKEN_LIMIT, "slot_duration_minutes": settings.DEFAULT_SLOT_DURATION_MINUTES,
            "reminder_hours_before": 24, "max_advance_booking_days": 30}
MAX_REPORT_DAYS = 365


def _row(user: User) -> dict:
    """Return the account fields an administrator may see."""
    return {f: getattr(user, f) for f in ("id", "university_id", "full_name", "email", "role", "status", "department")}


def pending(db: Session) -> list[dict]:
    """List staff registrations awaiting a decision (FR-J1)."""
    roles = [r.value for r in ROLES_REQUIRING_APPROVAL]
    return [_row(u) for u in db.query(User).filter(User.status == PENDING, User.role.in_(roles)).order_by(User.created_at)]


def decide_registration(db: Session, admin: User, user_id: int, approve: bool, reason: str | None) -> dict:
    """Approve (creating a doctor profile if needed) or reject a registration (FR-J1)."""
    user = get_or_404(db, User, user_id, "That account was not found.")
    if user.status != PENDING:
        raise ValidationError("This registration is not awaiting approval.")
    if not approve and not (reason or "").strip():
        raise ValidationError("Provide a reason for rejecting this registration.")
    user.status = ACTIVE if approve else SUSPENDED
    if approve and user.role == UserRole.DOCTOR.value and not db.query(DoctorProfile).filter_by(user_id=user.id).first():
        db.add(DoctorProfile(user_id=user.id, speciality=user.designation or "General Medicine",
                             consultation_minutes=settings_map(db)["slot_duration_minutes"]))
    record_audit(db, actor_id=admin.id, action="registration.approve" if approve else "registration.reject",
                 entity_type="user", entity_id=user.id, summary=reason)
    db.commit()
    return _row(user)


def list_users(db: Session, role: str | None = None, status: str | None = None, search: str | None = None) -> list[dict]:
    """List accounts with optional role, status and name/ID filters (FR-J2)."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if status:
        query = query.filter(User.status == status)
    if search:
        term = f"%{search.lower()}%"
        query = query.filter(func.lower(User.full_name).like(term) | func.lower(User.university_id).like(term))
    return [_row(u) for u in query.order_by(User.id.desc())]


def set_status(db: Session, admin: User, user_id: int, suspend: bool, reason: str | None) -> dict:
    """Suspend or reactivate an account; admins cannot change their own (FR-J2)."""
    user = get_or_404(db, User, user_id, "That account was not found.")
    if user.id == admin.id:
        raise ValidationError("You cannot change the status of your own account.")
    target = SUSPENDED if suspend else ACTIVE
    if user.status == target:
        raise ValidationError(f"This account is already {target}.")
    user.status = target
    record_audit(db, actor_id=admin.id, action="account.suspend" if suspend else "account.reactivate",
                 entity_type="user", entity_id=user.id, summary=reason)
    db.commit()
    return _row(user)


def metrics(db: Session, day: date | None = None) -> dict:
    """Headline figures for one day; patients are counted once, cancellations excluded (FR-J3)."""
    day = day or date.today()
    appts = db.query(Appointment).filter(Appointment.appointment_date == day).all()
    count = lambda status: sum(1 for a in appts if a.status == status)  # noqa: E731
    users = lambda status: db.query(func.count(User.id)).filter(User.status == status).scalar()  # noqa: E731
    return {
        "report_date": day, "appointments_today": len(appts), "completed_today": count("completed"),
        "cancelled_today": count("cancelled"), "no_show_today": count("no_show"),
        "patients_today": len({a.patient_id for a in appts if a.status != AppointmentStatus.CANCELLED.value}),
        "pending_registrations": users(PENDING), "active_users": users(ACTIVE), "suspended_users": users(SUSPENDED),
    }


def workload(db: Session, start: date, end: date) -> list[dict]:
    """Per-doctor workload including doctors with no appointments (FR-J3)."""
    rows = db.query(Appointment).filter(Appointment.appointment_date.between(start, end)).all()
    result = []
    for doctor in db.query(User).filter(User.role == UserRole.DOCTOR.value).order_by(User.full_name):
        mine = [a.status for a in rows if a.doctor_id == doctor.id]
        done = mine.count("completed")
        result.append({"doctor_id": doctor.id, "doctor_name": doctor.full_name, "total": len(mine), "completed": done,
                       "cancelled": mine.count("cancelled"), "no_show": mine.count("no_show"),
                       "completion_rate": round(done / len(mine) * 100, 1) if mine else 0.0})
    return sorted(result, key=lambda r: -r["total"])


def report(db: Session, admin: User, start: date, end: date) -> dict:
    """Build the exportable analytics report for a bounded window (FR-J3, FR-J4)."""
    if end < start:
        raise ValidationError("The end date cannot be before the start date.")
    if (end - start).days + 1 > MAX_REPORT_DAYS:
        raise ValidationError(f"A report can cover at most {MAX_REPORT_DAYS} days.")
    rows = db.query(Appointment).filter(Appointment.appointment_date.between(start, end)).all()
    daily = [{"day": d, "total": sum(1 for a in rows if a.appointment_date == d),
              "unique_patients": len({a.patient_id for a in rows if a.appointment_date == d})}
             for d in sorted({a.appointment_date for a in rows})]
    record_audit(db, actor_id=admin.id, action="report.generate", entity_type="report", summary=f"{start} to {end}")
    db.commit()
    return {"start_date": start, "end_date": end, "generated_at": utc_now(), "total_appointments": len(rows),
            "patients_seen": len({a.patient_id for a in rows if a.status == "completed"}),
            "daily": daily, "doctor_workload": workload(db, start, end)}


def report_csv(data: dict) -> str:
    """Render a report as CSV for download (FR-J4)."""
    lines = ["JU_FIX Analytics Report", f"Period,{data['start_date']},{data['end_date']}",
             f"Total Appointments,{data['total_appointments']}", f"Patients Seen,{data['patients_seen']}", "",
             "Doctor Workload", "Doctor,Total,Completed,Cancelled,No Show,Completion Rate %"]
    lines += [f"\"{r['doctor_name']}\",{r['total']},{r['completed']},{r['cancelled']},{r['no_show']},{r['completion_rate']}"
              for r in data["doctor_workload"]]
    return "\n".join(lines)


def settings_map(db: Session) -> dict[str, int]:
    """Return every setting, falling back to its default (FR-J5)."""
    stored = {row.key: row.value for row in db.query(SystemSetting)}
    return {key: int(stored.get(key, default)) for key, default in DEFAULTS.items()}


def update_settings(db: Session, admin: User, changes: dict[str, int]) -> dict[str, int]:
    """Change token limits, slot duration, reminder timing or the booking window (FR-J5)."""
    if not changes:
        raise ValidationError("Provide at least one setting to update.")
    for key, value in changes.items():
        row = db.query(SystemSetting).filter_by(key=key).first() or SystemSetting(key=key, value="")
        row.value, row.updated_by = str(value), admin.id
        db.add(row)
    record_audit(db, actor_id=admin.id, action="settings.update", entity_type="system_setting", summary=str(changes))
    db.commit()
    return settings_map(db)
