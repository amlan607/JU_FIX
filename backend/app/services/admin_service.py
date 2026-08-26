"""Business rules for the admin dashboard and reporting (FR-J1 to FR-J5).

The administrator oversees accounts and operations. This service deliberately
reports counts and workload only: it never returns diagnoses, prescriptions or
certificate reasons, which keeps clinical data with the clinicians (NFR-B).
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.config import settings
from app.core.constants import (
    ROLES_REQUIRING_APPROVAL,
    AccountStatus,
    AppointmentStatus,
    CertificateStatus,
    PrescriptionStatus,
    UserRole,
)
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.models.appointment import Appointment
from app.models.certificate import CertificateRequest
from app.models.doctor_profile import DoctorProfile
from app.models.prescription import Prescription
from app.models.system_setting import SystemSetting
from app.models.user import User

#: Default operational settings applied when an administrator has not set one.
DEFAULT_SETTINGS: dict[str, int] = {
    "daily_token_limit": settings.DEFAULT_DAILY_TOKEN_LIMIT,
    "slot_duration_minutes": settings.DEFAULT_SLOT_DURATION_MINUTES,
    "reminder_hours_before": 24,
    "max_advance_booking_days": 30,
}

#: Longest reporting window a single report may cover.
MAX_REPORT_DAYS = 365


def _utc_now() -> datetime:
    """Return the current timezone aware UTC time."""
    return datetime.now(timezone.utc)


def _require_admin(user: User) -> None:
    """Allow only the administrator role.

    Args:
        user: The signed in user.

    Raises:
        PermissionDeniedError: When the user is not an administrator.
    """
    if user.role != UserRole.ADMIN.value:
        raise PermissionDeniedError("Only an administrator can perform this action.")


def list_pending_registrations(db: Session, admin: User) -> list[dict]:
    """List registrations awaiting an administrator decision (FR-J1).

    Args:
        db: The active database session.
        admin: The signed in administrator.

    Returns:
        list[dict]: Pending doctor, pharmacist and admin registrations.
    """
    _require_admin(admin)

    pending = (
        db.query(User)
        .filter(
            User.status == AccountStatus.PENDING_APPROVAL.value,
            User.role.in_([role.value for role in ROLES_REQUIRING_APPROVAL]),
        )
        .order_by(User.created_at)
        .all()
    )

    return [
        {
            "user_id": user.id,
            "university_id": user.university_id,
            "full_name": user.full_name,
            "email": user.email,
            "phone": user.phone,
            "role": user.role,
            "department": user.department,
            "designation": user.designation,
            "requested_at": user.created_at,
        }
        for user in pending
    ]


def decide_registration(
    db: Session, admin: User, user_id: int, approve: bool, reason: str | None
) -> User:
    """Approve or reject a pending registration (FR-J1).

    Args:
        db: The active database session.
        admin: The signed in administrator.
        user_id: The account being decided.
        approve: ``True`` to activate the account, ``False`` to refuse it.
        reason: The reason. Required on rejection.

    Returns:
        User: The updated account.

    Raises:
        ValidationError: When the account is not awaiting approval, or a
            rejection carries no reason.
    """
    _require_admin(admin)

    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("That account was not found.")

    if user.status != AccountStatus.PENDING_APPROVAL.value:
        raise ValidationError("This registration is not awaiting approval.")

    if not approve and not (reason or "").strip():
        raise ValidationError("Provide a reason for rejecting this registration.")

    if approve:
        user.status = AccountStatus.ACTIVE.value
        # A doctor needs a clinical profile before they appear in booking search.
        if user.role == UserRole.DOCTOR.value:
            exists = db.query(DoctorProfile).filter(DoctorProfile.user_id == user.id).first()
            if exists is None:
                db.add(
                    DoctorProfile(
                        user_id=user.id,
                        speciality=user.designation or "General Medicine",
                        consultation_minutes=get_settings_map(db)["slot_duration_minutes"],
                    )
                )
        action, summary = "registration.approve", f"Approved {user.role} registration."
    else:
        user.status = AccountStatus.SUSPENDED.value
        action, summary = "registration.reject", f"Rejected registration: {reason.strip()}"

    record_audit(
        db,
        actor_id=admin.id,
        action=action,
        entity_type="user",
        entity_id=user.id,
        summary=summary,
    )
    db.commit()
    db.refresh(user)
    return user


def list_users(
    db: Session, admin: User, role: str | None = None, status: str | None = None, search: str | None = None
) -> list[dict]:
    """List accounts for the user management screen (FR-J2).

    Args:
        db: The active database session.
        admin: The signed in administrator.
        role: Optional role filter.
        status: Optional account status filter.
        search: Optional case insensitive name or university ID search.

    Returns:
        list[dict]: Matching accounts, newest first.
    """
    _require_admin(admin)

    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if status:
        query = query.filter(User.status == status)
    if search:
        term = f"%{search.lower()}%"
        query = query.filter(
            func.lower(User.full_name).like(term) | func.lower(User.university_id).like(term)
        )

    return [
        {
            "user_id": user.id,
            "university_id": user.university_id,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "status": user.status,
            "department": user.department,
            "created_at": user.created_at,
        }
        for user in query.order_by(User.id.desc()).all()
    ]


def set_account_status(
    db: Session, admin: User, user_id: int, suspend: bool, reason: str | None
) -> User:
    """Suspend or reactivate an account (FR-J2).

    Args:
        db: The active database session.
        admin: The signed in administrator.
        user_id: The account being changed.
        suspend: ``True`` to suspend, ``False`` to reactivate.
        reason: The reason. Required when suspending.

    Returns:
        User: The updated account.

    Raises:
        ValidationError: When an administrator suspends their own account or
            the account is already in the requested state.
    """
    _require_admin(admin)

    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("That account was not found.")

    # Suspending your own account would lock the last administrator out.
    if user.id == admin.id:
        raise ValidationError("You cannot change the status of your own account.")

    if suspend and not (reason or "").strip():
        raise ValidationError("Provide a reason for suspending this account.")

    target = AccountStatus.SUSPENDED.value if suspend else AccountStatus.ACTIVE.value
    if user.status == target:
        raise ValidationError(f"This account is already {target}.")

    user.status = target

    record_audit(
        db,
        actor_id=admin.id,
        action="account.suspend" if suspend else "account.reactivate",
        entity_type="user",
        entity_id=user.id,
        summary=(reason or "").strip() or "Account reactivated by an administrator.",
    )
    db.commit()
    db.refresh(user)
    return user


def get_dashboard_metrics(db: Session, admin: User, report_date: date | None = None) -> dict:
    """Build the headline operational figures (FR-J3).

    Args:
        db: The active database session.
        admin: The signed in administrator.
        report_date: The day to report on. Defaults to today.

    Returns:
        dict: Daily counts plus account totals.
    """
    _require_admin(admin)

    day = report_date or date.today()

    def count_on_day(status: AppointmentStatus | None = None) -> int:
        """Count appointments on the report date, optionally by status."""
        query = db.query(func.count(Appointment.id)).filter(Appointment.appointment_date == day)
        if status is not None:
            query = query.filter(Appointment.status == status.value)
        return query.scalar() or 0

    patients_today = (
        db.query(func.count(func.distinct(Appointment.patient_id)))
        .filter(
            Appointment.appointment_date == day,
            Appointment.status != AppointmentStatus.CANCELLED.value,
        )
        .scalar()
        or 0
    )

    prescriptions_today = (
        db.query(func.count(Prescription.id))
        .filter(
            Prescription.status != PrescriptionStatus.DRAFT.value,
            func.date(Prescription.issued_at) == day.isoformat(),
        )
        .scalar()
        or 0
    )

    certificates_pending = (
        db.query(func.count(CertificateRequest.id))
        .filter(CertificateRequest.status == CertificateStatus.SUBMITTED.value)
        .scalar()
        or 0
    )

    pending_registrations = (
        db.query(func.count(User.id))
        .filter(User.status == AccountStatus.PENDING_APPROVAL.value)
        .scalar()
        or 0
    )

    active_users = (
        db.query(func.count(User.id)).filter(User.status == AccountStatus.ACTIVE.value).scalar() or 0
    )
    suspended_users = (
        db.query(func.count(User.id)).filter(User.status == AccountStatus.SUSPENDED.value).scalar()
        or 0
    )

    return {
        "report_date": day,
        "patients_today": patients_today,
        "appointments_today": count_on_day(),
        "completed_today": count_on_day(AppointmentStatus.COMPLETED),
        "cancelled_today": count_on_day(AppointmentStatus.CANCELLED),
        "no_show_today": count_on_day(AppointmentStatus.NO_SHOW),
        "prescriptions_issued_today": prescriptions_today,
        "certificates_pending": certificates_pending,
        "pending_registrations": pending_registrations,
        "active_users": active_users,
        "suspended_users": suspended_users,
    }


def get_doctor_workload(db: Session, admin: User, start: date, end: date) -> list[dict]:
    """Report each doctor's workload over a window (FR-J3).

    Args:
        db: The active database session.
        admin: The signed in administrator.
        start: First day of the window, inclusive.
        end: Last day of the window, inclusive.

    Returns:
        list[dict]: One row per doctor, busiest first.
    """
    _require_admin(admin)

    completed = func.sum(case((Appointment.status == AppointmentStatus.COMPLETED.value, 1), else_=0))
    cancelled = func.sum(case((Appointment.status == AppointmentStatus.CANCELLED.value, 1), else_=0))
    no_show = func.sum(case((Appointment.status == AppointmentStatus.NO_SHOW.value, 1), else_=0))

    rows = (
        db.query(
            User.id,
            User.full_name,
            DoctorProfile.speciality,
            func.count(Appointment.id).label("total"),
            completed.label("completed"),
            cancelled.label("cancelled"),
            no_show.label("no_show"),
        )
        .select_from(User)
        .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
        .outerjoin(
            Appointment,
            (Appointment.doctor_id == User.id)
            & (Appointment.appointment_date >= start)
            & (Appointment.appointment_date <= end),
        )
        .filter(User.role == UserRole.DOCTOR.value)
        .group_by(User.id, User.full_name, DoctorProfile.speciality)
        .order_by(func.count(Appointment.id).desc())
        .all()
    )

    workload = []
    for doctor_id, name, speciality, total, done, cancel_count, absent in rows:
        total = total or 0
        done = done or 0
        workload.append(
            {
                "doctor_id": doctor_id,
                "doctor_name": name,
                "speciality": speciality,
                "total_appointments": total,
                "completed": done,
                "cancelled": cancel_count or 0,
                "no_show": absent or 0,
                "completion_rate": round(done / total * 100, 1) if total else 0.0,
            }
        )
    return workload


def get_daily_volumes(db: Session, admin: User, start: date, end: date) -> list[dict]:
    """Report appointment volume per day over a window (FR-J3).

    Args:
        db: The active database session.
        admin: The signed in administrator.
        start: First day of the window, inclusive.
        end: Last day of the window, inclusive.

    Returns:
        list[dict]: One row per day that has at least one appointment.
    """
    _require_admin(admin)

    completed = func.sum(case((Appointment.status == AppointmentStatus.COMPLETED.value, 1), else_=0))
    cancelled = func.sum(case((Appointment.status == AppointmentStatus.CANCELLED.value, 1), else_=0))
    no_show = func.sum(case((Appointment.status == AppointmentStatus.NO_SHOW.value, 1), else_=0))

    rows = (
        db.query(
            Appointment.appointment_date,
            func.count(Appointment.id),
            completed,
            cancelled,
            no_show,
            func.count(func.distinct(Appointment.patient_id)),
        )
        .filter(Appointment.appointment_date >= start, Appointment.appointment_date <= end)
        .group_by(Appointment.appointment_date)
        .order_by(Appointment.appointment_date)
        .all()
    )

    return [
        {
            "day": day,
            "total": total or 0,
            "completed": done or 0,
            "cancelled": cancel_count or 0,
            "no_show": absent or 0,
            "unique_patients": patients or 0,
        }
        for day, total, done, cancel_count, absent, patients in rows
    ]


def build_analytics_report(db: Session, admin: User, start: date, end: date) -> dict:
    """Assemble the exportable platform report (FR-J4).

    Args:
        db: The active database session.
        admin: The signed in administrator.
        start: First day of the window, inclusive.
        end: Last day of the window, inclusive.

    Returns:
        dict: Totals, daily volumes and doctor workload.

    Raises:
        ValidationError: When the window is inverted or too long.
    """
    _require_admin(admin)

    if end < start:
        raise ValidationError("The end date cannot be before the start date.")
    if (end - start).days + 1 > MAX_REPORT_DAYS:
        raise ValidationError(f"A report can cover at most {MAX_REPORT_DAYS} days.")

    daily = get_daily_volumes(db, admin, start, end)
    workload = get_doctor_workload(db, admin, start, end)

    total_appointments = sum(row["total"] for row in daily)

    patients_seen = (
        db.query(func.count(func.distinct(Appointment.patient_id)))
        .filter(
            Appointment.appointment_date >= start,
            Appointment.appointment_date <= end,
            Appointment.status == AppointmentStatus.COMPLETED.value,
        )
        .scalar()
        or 0
    )

    total_prescriptions = (
        db.query(func.count(Prescription.id))
        .filter(
            Prescription.status != PrescriptionStatus.DRAFT.value,
            func.date(Prescription.issued_at) >= start.isoformat(),
            func.date(Prescription.issued_at) <= end.isoformat(),
        )
        .scalar()
        or 0
    )

    total_certificates = (
        db.query(func.count(CertificateRequest.id))
        .filter(
            CertificateRequest.status == CertificateStatus.APPROVED.value,
            func.date(CertificateRequest.decided_at) >= start.isoformat(),
            func.date(CertificateRequest.decided_at) <= end.isoformat(),
        )
        .scalar()
        or 0
    )

    record_audit(
        db,
        actor_id=admin.id,
        action="report.generate",
        entity_type="analytics_report",
        summary=f"Generated the platform report for {start} to {end}.",
    )
    db.commit()

    return {
        "start_date": start,
        "end_date": end,
        "generated_at": _utc_now(),
        "total_appointments": total_appointments,
        "total_patients_seen": patients_seen,
        "total_prescriptions": total_prescriptions,
        "total_certificates_approved": total_certificates,
        "daily_volumes": daily,
        "doctor_workload": workload,
    }


def report_to_csv(report: dict) -> str:
    """Render a report as CSV for download (FR-J4).

    Args:
        report: The report produced by :func:`build_analytics_report`.

    Returns:
        str: CSV text with a summary block, a daily block and a workload block.
    """
    lines = [
        "JU_FIX Platform Analytics Report",
        f"Period,{report['start_date']},{report['end_date']}",
        f"Generated At,{report['generated_at'].isoformat()}",
        "",
        "Summary",
        "Metric,Value",
        f"Total Appointments,{report['total_appointments']}",
        f"Patients Seen,{report['total_patients_seen']}",
        f"Prescriptions Issued,{report['total_prescriptions']}",
        f"Certificates Approved,{report['total_certificates_approved']}",
        "",
        "Daily Appointment Volume",
        "Date,Total,Completed,Cancelled,No Show,Unique Patients",
    ]
    lines.extend(
        f"{row['day']},{row['total']},{row['completed']},{row['cancelled']},"
        f"{row['no_show']},{row['unique_patients']}"
        for row in report["daily_volumes"]
    )

    lines.extend(
        [
            "",
            "Doctor Workload",
            "Doctor,Speciality,Total,Completed,Cancelled,No Show,Completion Rate %",
        ]
    )
    lines.extend(
        f"\"{row['doctor_name']}\",\"{row['speciality'] or ''}\",{row['total_appointments']},"
        f"{row['completed']},{row['cancelled']},{row['no_show']},{row['completion_rate']}"
        for row in report["doctor_workload"]
    )

    return "\n".join(lines)


def get_settings_map(db: Session) -> dict[str, int]:
    """Return the operational settings, falling back to defaults (FR-J5).

    Args:
        db: The active database session.

    Returns:
        dict[str, int]: Every known setting with its current value.
    """
    stored = {row.key: row.value for row in db.query(SystemSetting).all()}
    resolved: dict[str, int] = {}
    for key, fallback in DEFAULT_SETTINGS.items():
        try:
            resolved[key] = int(stored.get(key, fallback))
        except (TypeError, ValueError):
            resolved[key] = fallback
    return resolved


def update_settings(db: Session, admin: User, changes: dict[str, int]) -> dict[str, int]:
    """Change one or more operational settings (FR-J5).

    Args:
        db: The active database session.
        admin: The signed in administrator.
        changes: The settings to write.

    Returns:
        dict[str, int]: The settings after the change.

    Raises:
        ValidationError: When a key is unknown or nothing was supplied.
    """
    _require_admin(admin)

    applied = {key: value for key, value in changes.items() if value is not None}
    if not applied:
        raise ValidationError("Provide at least one setting to update.")

    unknown = set(applied) - set(DEFAULT_SETTINGS)
    if unknown:
        raise ValidationError(f"Unknown setting: {', '.join(sorted(unknown))}.")

    for key, value in applied.items():
        row = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if row is None:
            db.add(SystemSetting(key=key, value=str(value), updated_by=admin.id))
        else:
            row.value = str(value)
            row.updated_by = admin.id

    record_audit(
        db,
        actor_id=admin.id,
        action="settings.update",
        entity_type="system_setting",
        summary="Updated settings: " + ", ".join(f"{k}={v}" for k, v in sorted(applied.items())),
    )
    db.commit()
    return get_settings_map(db)


def get_recent_activity(db: Session, admin: User, limit: int = 15) -> list[dict]:
    """Return the most recent audit entries for the dashboard feed.

    Args:
        db: The active database session.
        admin: The signed in administrator.
        limit: Maximum number of entries.

    Returns:
        list[dict]: Recent non clinical activity, newest first.
    """
    _require_admin(admin)

    from app.models.audit_log import AuditLog

    entries = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 50)).all()

    names: dict[int, str] = {}
    feed = []
    for entry in entries:
        if entry.actor_id and entry.actor_id not in names:
            actor = db.get(User, entry.actor_id)
            names[entry.actor_id] = actor.full_name if actor else "Unknown user"
        feed.append(
            {
                "id": entry.id,
                "action": entry.action,
                "entity_type": entry.entity_type,
                "actor_name": names.get(entry.actor_id, "System"),
                "summary": entry.summary,
                "created_at": entry.created_at,
            }
        )
    return feed


def default_report_window(days: int = 30) -> tuple[date, date]:
    """Return a sensible default reporting window ending today.

    Args:
        days: The length of the window in days.

    Returns:
        tuple[date, date]: The start and end dates, inclusive.
    """
    end = date.today()
    return end - timedelta(days=days - 1), end
