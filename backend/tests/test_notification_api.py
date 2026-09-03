"""API tests for notification centre and reminder operations (FR-H1 to FR-H3)."""

import pytest

from app.core.constants import UserRole
from app.services import notification_service
from tests.conftest import auth_header, make_user


@pytest.mark.api
def test_notifications_require_authentication(client):
    assert client.get("/api/notifications").status_code == 401


@pytest.mark.api
def test_user_can_list_and_mark_notifications_read(client, db_session):
    user = make_user(db_session)
    notification_service.notify(
        db_session, user_id=user.id, category="appointment_update", title="Confirmed", body="Booked."
    )
    headers = auth_header(client, user.university_id)
    response = client.get("/api/notifications", headers=headers)
    assert response.status_code == 200
    notification_id = response.json()["data"]["notifications"][0]["id"]
    marked = client.patch(f"/api/notifications/{notification_id}/read", headers=headers)
    assert marked.status_code == 200
    assert marked.json()["data"]["is_read"] is True


@pytest.mark.api
def test_user_cannot_mark_another_users_notification(client, db_session):
    owner = make_user(db_session)
    stranger = make_user(db_session, university_id="STU-2021-371")
    notification = notification_service.notify(
        db_session, user_id=owner.id, category="security", title="Sign in", body="Account accessed."
    )
    response = client.patch(
        f"/api/notifications/{notification.id}/read",
        headers=auth_header(client, stranger.university_id),
    )
    assert response.status_code == 403


@pytest.mark.api
def test_only_admin_can_run_reminder_sweep(client, db_session):
    user = make_user(db_session)
    assert client.post("/api/notifications/run-reminders", headers=auth_header(client, user.university_id)).status_code == 403
    admin = make_user(db_session, university_id="ADM-370", role=UserRole.ADMIN)
    response = client.post("/api/notifications/run-reminders", headers=auth_header(client, admin.university_id))
    assert response.status_code == 200
    assert "appointment_reminders_created" in response.json()["data"]
