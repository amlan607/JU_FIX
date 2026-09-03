"""HTTP endpoints for notifications and reminders (FR-H1 to FR-H3)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import UserRole
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.responses import success_response
from app.models.user import User
from app.schemas.notification import NotificationResponse, UpdatePreferenceRequest
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications and Reminders"])


@router.get("")
def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return the signed-in user's notification history and unread count."""
    result = notification_service.list_for_user(db, current_user, unread_only, limit)
    return success_response(
        {
            "unread_count": result["unread_count"],
            "notifications": [
                NotificationResponse.model_validate(item).model_dump()
                for item in result["notifications"]
            ],
        }
    )


@router.patch("/read-all")
def mark_all_read(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict:
    """Mark every unread notification as read."""
    return success_response({"marked": notification_service.mark_all_read(db, current_user)})


@router.post("/run-reminders")
def run_reminders(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(UserRole.ADMIN)),
) -> dict:
    """Run the appointment and medicine reminder sweep."""
    return success_response(notification_service.run_all_reminders(db))


@router.get("/preferences")
def list_preferences(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict:
    """Return the signed-in user's notification preferences."""
    return success_response(notification_service.list_preferences(db, current_user))


@router.patch("/preferences")
def update_preference(
    payload: UpdatePreferenceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Change one notification category preference."""
    return success_response(
        notification_service.update_preference(
            db, current_user, payload.category, payload.in_app_enabled, payload.email_enabled
        )
    )


@router.patch("/{notification_id}/read")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Mark one notification read after checking ownership."""
    notification = notification_service.mark_read(db, notification_id, current_user)
    return success_response(NotificationResponse.model_validate(notification).model_dump())
