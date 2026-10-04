"""Compact workflow tests for accounts and authentication (FR-A)."""

import pytest

from app.core.config import settings
from app.core.constants import AccountStatus
from tests.conftest import TEST_PASSWORD, auth_header, make_user


@pytest.mark.api
def test_registration_validation_and_verification(client):
    """Registration enforces required fields and activates only after verification."""
    base = {
        "university_id": "STU-2021-503",
        "full_name": "Flow Student",
        "password": TEST_PASSWORD,
        "email": "flow@ju.edu.bd",
    }
    weak_password = client.post(
        "/api/auth/register", json={**base, "password": "password"}
    )
    no_contact = client.post(
        "/api/auth/register",
        json={key: value for key, value in base.items() if key != "email"},
    )
    invalid_phone = client.post(
        "/api/auth/register",
        json={**base, "university_id": "STU-2021-504", "email": None, "phone": "12345"},
    )
    assert [weak_password.status_code, no_contact.status_code, invalid_phone.status_code] == [
        400,
        400,
        400,
    ]

    registration = client.post("/api/auth/register", json=base)
    assert registration.status_code == 201
    body = registration.json()["data"]
    assert "password_hash" not in body["user"]

    verified = client.post(
        "/api/auth/verify-account", json={"token": body["verification_token"]}
    )
    assert verified.status_code == 200
    assert verified.json()["data"]["user"]["status"] == AccountStatus.ACTIVE.value
    assert client.post(
        "/api/auth/verify-account", json={"token": body["verification_token"]}
    ).status_code == 400
    assert client.post("/api/auth/register", json=base).status_code == 409


@pytest.mark.api
def test_verified_doctor_waits_for_admin_approval(client):
    """Verified staff requiring approval remain unable to sign in."""
    registration = client.post(
        "/api/auth/register",
        json={
            "university_id": "DOC-9001",
            "full_name": "Doctor One",
            "password": TEST_PASSWORD,
            "email": "doctor@ju.edu.bd",
            "role": "doctor",
        },
    )
    assert registration.status_code == 201
    token = registration.json()["data"]["verification_token"]

    verified = client.post("/api/auth/verify-account", json={"token": token})
    assert verified.json()["data"]["user"]["status"] == AccountStatus.PENDING_APPROVAL.value
    login = client.post(
        "/api/auth/login",
        json={"identifier": "DOC-9001", "password": TEST_PASSWORD},
    )
    assert login.status_code == 401


@pytest.mark.api
def test_login_accepts_email_and_locks_after_repeated_failures(client, db_session):
    """Login accepts email while obscuring unknown IDs and enforcing lockout."""
    make_user(db_session, university_id="STU-2021-370", email="oywon@ju.edu.bd")
    success = client.post(
        "/api/auth/login",
        json={"identifier": "oywon@ju.edu.bd", "password": TEST_PASSWORD},
    )
    assert success.status_code == 200

    unknown = client.post(
        "/api/auth/login",
        json={"identifier": "STU-0000-000", "password": TEST_PASSWORD},
    )
    wrong = client.post(
        "/api/auth/login",
        json={"identifier": "STU-2021-370", "password": "WrongPass1!"},
    )
    assert unknown.json()["error"]["message"] == wrong.json()["error"]["message"]

    for _ in range(settings.MAX_FAILED_LOGIN_ATTEMPTS - 1):
        failed = client.post(
            "/api/auth/login",
            json={"identifier": "STU-2021-370", "password": "WrongPass1!"},
        )
        assert failed.status_code == 401

    locked = client.post(
        "/api/auth/login",
        json={"identifier": "STU-2021-370", "password": TEST_PASSWORD},
    )
    assert locked.status_code == 401
    assert "Too many failed attempts" in locked.json()["error"]["message"]


@pytest.mark.api
def test_profile_update_and_logout_revoke_current_session(client, db_session):
    """Users can edit their own profile and logout invalidates their bearer token."""
    make_user(db_session, university_id="STU-2021-370")
    headers = auth_header(client, "STU-2021-370")

    profile = client.get("/api/auth/me", headers=headers)
    assert profile.status_code == 200
    updated = client.patch(
        "/api/auth/me", json={"department": "CSE"}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["department"] == "CSE"

    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401


@pytest.mark.api
def test_password_reset_revokes_sessions_and_replaces_password(client, db_session):
    """Reset is non-enumerating, changes credentials, and revokes old sessions."""
    make_user(db_session, university_id="STU-2021-370")
    login = client.post(
        "/api/auth/login",
        json={"identifier": "STU-2021-370", "password": TEST_PASSWORD},
    )
    old_token = login.json()["data"]["access_token"]

    known = client.post(
        "/api/auth/forgot-password", json={"identifier": "STU-2021-370"}
    )
    unknown = client.post(
        "/api/auth/forgot-password", json={"identifier": "STU-9999-999"}
    )
    assert known.json()["data"]["message"] == unknown.json()["data"]["message"]

    reset_token = known.json()["data"]["reset_token"]
    reset = client.post(
        "/api/auth/reset-password",
        json={"token": reset_token, "new_password": "BrandNew@2026"},
    )
    assert reset.status_code == 200
    assert client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {old_token}"}
    ).status_code == 401
    assert client.post(
        "/api/auth/login",
        json={"identifier": "STU-2021-370", "password": "BrandNew@2026"},
    ).status_code == 200
    assert client.post(
        "/api/auth/login",
        json={"identifier": "STU-2021-370", "password": TEST_PASSWORD},
    ).status_code == 401