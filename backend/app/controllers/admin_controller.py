"""HTTP controller for the admin dashboard and reporting (FR-J1 to FR-J5)."""

from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.constants import UserRole
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.responses import success_response
from app.models.user import User
from app.schemas.admin import (
    AccountActionRequest,
    ApprovalDecisionRequest,
    UpdateSettingsRequest,
)
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["Admin Dashboard and Reporting"])

#: Every endpoint in this controller is administrator only.
AdminUser = Depends(require_roles(UserRole.ADMIN))


@router.get("/dashboard")
def get_dashboard(
    report_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    current_user: User = AdminUser,
) -> dict:
    """Return the headline operational figures and the activity feed (FR-J3)."""
    metrics = admin_service.get_dashboard_metrics(db, current_user, report_date)
    activity = admin_service.get_recent_activity(db, current_user)
    return success_response({"metrics": metrics, "recent_activity": activity})


@router.get("/registrations/pending")
def list_pending_registrations(
    db: Session = Depends(get_db), current_user: User = AdminUser
) -> dict:
    """List registrations awaiting an administrator decision (FR-J1)."""
    return success_response(admin_service.list_pending_registrations(db, current_user))


@router.patch("/registrations/{user_id}/decision")
def decide_registration(
    user_id: int,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    current_user: User = AdminUser,
) -> dict:
    """Approve or reject a doctor, pharmacist or admin registration (FR-J1)."""
    user = admin_service.decide_registration(
        db, current_user, user_id, payload.approve, payload.reason
    )
    return success_response(
        {
            "user_id": user.id,
            "university_id": user.university_id,
            "full_name": user.full_name,
            "role": user.role,
            "status": user.status,
        }
    )


@router.get("/users")
def list_users(
    role: str | None = Query(default=None),
    account_status: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=120),
    db: Session = Depends(get_db),
    current_user: User = AdminUser,
) -> dict:
    """List accounts for the user management screen (FR-J2)."""
    return success_response(
        admin_service.list_users(db, current_user, role, account_status, search)
    )


@router.patch("/users/{user_id}/status")
def set_account_status(
    user_id: int,
    payload: AccountActionRequest,
    db: Session = Depends(get_db),
    current_user: User = AdminUser,
) -> dict:
    """Suspend or reactivate an account (FR-J2)."""
    user = admin_service.set_account_status(
        db, current_user, user_id, payload.suspend, payload.reason
    )
    return success_response(
        {
            "user_id": user.id,
            "university_id": user.university_id,
            "full_name": user.full_name,
            "role": user.role,
            "status": user.status,
        }
    )


@router.get("/reports")
def get_report(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = AdminUser,
) -> dict:
    """Generate the platform analytics report (FR-J3, FR-J4)."""
    default_start, default_end = admin_service.default_report_window()
    report = admin_service.build_analytics_report(
        db, current_user, start or default_start, end or default_end
    )
    return success_response(report)


@router.get("/reports/export")
def export_report(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = AdminUser,
) -> Response:
    """Download the platform analytics report as CSV (FR-J4).

    This endpoint returns a file rather than the standard JSON envelope because
    the browser downloads it directly.
    """
    default_start, default_end = admin_service.default_report_window()
    report = admin_service.build_analytics_report(
        db, current_user, start or default_start, end or default_end
    )
    csv_body = admin_service.report_to_csv(report)
    filename = f"ju-fix-report-{report['start_date']}-to-{report['end_date']}.csv"

    return Response(
        content=csv_body,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/settings")
def get_settings(db: Session = Depends(get_db), current_user: User = AdminUser) -> dict:
    """Return the administrator configurable operational settings (FR-J5)."""
    admin_service._require_admin(current_user)
    return success_response(admin_service.get_settings_map(db))


@router.patch("/settings")
def update_settings(
    payload: UpdateSettingsRequest,
    db: Session = Depends(get_db),
    current_user: User = AdminUser,
) -> dict:
    """Change token limits, slot duration and reminder timing (FR-J5)."""
    updated = admin_service.update_settings(db, current_user, payload.model_dump(exclude_none=True))
    return success_response(updated)
