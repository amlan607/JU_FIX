"""HTTP controller for the admin dashboard and reporting (FR-J1 to FR-J5). Admin only."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.constants import UserRole
from app.core.database import get_db
from app.core.deps import require_roles
from app.core.responses import success_response as ok
from app.models.user import User
from app.schemas.admin import AccountAction, RegistrationDecision, SettingsRequest
from app.services import admin_service as service

router = APIRouter(prefix="/admin", tags=["Admin Dashboard and Reporting"])
Admin = Depends(require_roles(UserRole.ADMIN))


def _window(start: date | None, end: date | None) -> tuple[date, date]:
    """Default to the last 30 days."""
    end = end or date.today()
    return start or end - timedelta(days=29), end


@router.get("/dashboard")
def dashboard(day: date | None = Query(default=None, alias="date"), db: Session = Depends(get_db), _: User = Admin) -> dict:
    """Return the day's headline figures (FR-J3)."""
    return ok({"metrics": service.metrics(db, day)})


@router.get("/registrations/pending")
def pending(db: Session = Depends(get_db), _: User = Admin) -> dict:
    """List registrations awaiting approval (FR-J1)."""
    return ok(service.pending(db))


@router.patch("/registrations/{user_id}/decision")
def decide(user_id: int, payload: RegistrationDecision, db: Session = Depends(get_db), admin: User = Admin) -> dict:
    """Approve or reject a staff registration (FR-J1)."""
    return ok(service.decide_registration(db, admin, user_id, payload.approve, payload.reason))


@router.get("/users")
def users(role: str | None = None, status: str | None = None, search: str | None = None,
          db: Session = Depends(get_db), _: User = Admin) -> dict:
    """List accounts with filters (FR-J2)."""
    return ok(service.list_users(db, role, status, search))


@router.patch("/users/{user_id}/status")
def set_status(user_id: int, payload: AccountAction, db: Session = Depends(get_db), admin: User = Admin) -> dict:
    """Suspend or reactivate an account (FR-J2)."""
    return ok(service.set_status(db, admin, user_id, payload.suspend, payload.reason))


@router.get("/reports")
def reports(start: date | None = None, end: date | None = None, db: Session = Depends(get_db), admin: User = Admin) -> dict:
    """Generate the analytics report (FR-J3, FR-J4)."""
    return ok(service.report(db, admin, *_window(start, end)))


@router.get("/reports/export")
def export(start: date | None = None, end: date | None = None, db: Session = Depends(get_db), admin: User = Admin) -> Response:
    """Download the report as CSV; a file, so not the JSON envelope (FR-J4)."""
    data = service.report(db, admin, *_window(start, end))
    headers = {"Content-Disposition": f'attachment; filename="ju-fix-report-{data["start_date"]}.csv"'}
    return Response(service.report_csv(data), media_type="text/csv", headers=headers)


@router.get("/settings")
def get_settings(db: Session = Depends(get_db), _: User = Admin) -> dict:
    """Return the operational settings (FR-J5)."""
    return ok(service.settings_map(db))


@router.patch("/settings")
def update_settings(payload: SettingsRequest, db: Session = Depends(get_db), admin: User = Admin) -> dict:
    """Change token limits, slot duration and reminder timing (FR-J5)."""
    return ok(service.update_settings(db, admin, payload.model_dump(exclude_none=True)))
