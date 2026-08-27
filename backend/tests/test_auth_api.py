"""Endpoint tests for the accounts and authentication controller (FR-A)."""

import pytest

from app.core.constants import AccountStatus, UserRole
from tests.conftest import TEST_PASSWORD, auth_header, make_user


@pytest.mark.api
def test_register_endpoint_creates_an_account(client):
    """POST /api/auth/register returns 201 with the standard envelope."""
    response = client.post(
        "/api/auth/register",
        json={
            "university_id": "STU-2021-500",
            "full_name": "Api Student",
            "password": TEST_PASSWORD,
            "email": "api.student@ju.edu.bd",
            "role": "student",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["user"]["university_id"] == "STU-2021-500"


@pytest.mark.api
def test_register_never_returns_the_password_hash(client):
    """NFR-B: credential material never leaves the API."""
    response = client.post(
        "/api/auth/register",
        json={
            "university_id": "STU-2021-501",
            "full_name": "Api Student",
            "password": TEST_PASSWORD,
            "email": "api.student2@ju.edu.bd",
        },
    )

    assert "password_hash" not in response.text
    assert TEST_PASSWORD not in response.json()["data"]["user"].values()


@pytest.mark.api
def test_register_rejects_a_weak_password(client):
    """A password failing FR-A3 returns 400 with field level detail."""
    response = client.post(
        "/api/auth/register",
        json={
            "university_id": "STU-2021-502",
            "full_name": "Weak Password",
            "password": "password",
            "email": "weak@ju.edu.bd",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "validation_error"


@pytest.mark.api
def test_full_registration_and_login_flow(client):
    """Register, verify, then sign in successfully."""
    register = client.post(
        "/api/auth/register",
        json={
            "university_id": "STU-2021-503",
            "full_name": "Flow Student",
            "password": TEST_PASSWORD,
            "email": "flow@ju.edu.bd",
        },
    ).json()

    verify = client.post(
        "/api/auth/verify-account",
        json={"token": register["data"]["verification_token"]},
    )
    assert verify.status_code == 200
    assert verify.json()["data"]["user"]["status"] == AccountStatus.ACTIVE.value

    login = client.post(
        "/api/auth/login",
        json={"identifier": "STU-2021-503", "password": TEST_PASSWORD},
    )
    assert login.status_code == 200
    assert login.json()["data"]["access_token"]


@pytest.mark.api
def test_login_before_verification_is_refused(client):
    """An unverified account cannot sign in (FR-A2)."""
    client.post(
        "/api/auth/register",
        json={
            "university_id": "STU-2021-504",
            "full_name": "Unverified",
            "password": TEST_PASSWORD,
            "email": "unverified@ju.edu.bd",
        },
    )

    response = client.post(
        "/api/auth/login",
        json={"identifier": "STU-2021-504", "password": TEST_PASSWORD},
    )

    assert response.status_code == 401
    assert "Verify your account" in response.json()["error"]["message"]


@pytest.mark.api
def test_login_returns_the_role_for_role_based_routing(client, db_session):
    """FR-A7: the login payload carries the role the frontend routes on."""
    make_user(db_session, university_id="DOC-2001", role=UserRole.DOCTOR)

    response = client.post(
        "/api/auth/login",
        json={"identifier": "DOC-2001", "password": TEST_PASSWORD},
    )

    assert response.json()["data"]["user"]["role"] == "doctor"


@pytest.mark.api
def test_me_requires_authentication(client):
    """A protected endpoint refuses an anonymous request."""
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_error"


@pytest.mark.api
def test_me_returns_the_signed_in_profile(client, db_session):
    """FR-A8: a signed in user can read their own profile."""
    make_user(db_session, university_id="STU-2021-370", full_name="Oywon Islam")
    headers = auth_header(client, "STU-2021-370")

    response = client.get("/api/auth/me", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["full_name"] == "Oywon Islam"


@pytest.mark.api
def test_profile_can_be_updated(client, db_session):
    """FR-A8: a user can edit their own profile fields."""
    make_user(db_session, university_id="STU-2021-370")
    headers = auth_header(client, "STU-2021-370")

    response = client.patch(
        "/api/auth/me",
        json={"department": "CSE", "designation": "Undergraduate Student"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["department"] == "CSE"


@pytest.mark.api
def test_logout_invalidates_the_session(client, db_session):
    """FR-A9 and Consistency Note 11.4: the token stops working after logout."""
    make_user(db_session, university_id="STU-2021-370")
    headers = auth_header(client, "STU-2021-370")

    assert client.post("/api/auth/logout", headers=headers).status_code == 200

    after_logout = client.get("/api/auth/me", headers=headers)
    assert after_logout.status_code == 401


@pytest.mark.api
def test_forgot_password_does_not_reveal_whether_the_account_exists(client, db_session):
    """The same acknowledgement is returned for known and unknown identifiers."""
    make_user(db_session, university_id="STU-2021-370")

    known = client.post("/api/auth/forgot-password", json={"identifier": "STU-2021-370"})
    unknown = client.post("/api/auth/forgot-password", json={"identifier": "STU-9999-999"})

    assert known.status_code == unknown.status_code == 200
    assert known.json()["data"]["message"] == unknown.json()["data"]["message"]


@pytest.mark.api
def test_password_reset_end_to_end(client, db_session):
    """FR-A5: the new password works and the old one stops working."""
    make_user(db_session, university_id="STU-2021-370")

    reset_token = client.post(
        "/api/auth/forgot-password", json={"identifier": "STU-2021-370"}
    ).json()["data"]["reset_token"]

    assert client.post(
        "/api/auth/reset-password",
        json={"token": reset_token, "new_password": "BrandNew@2026"},
    ).status_code == 200

    assert client.post(
        "/api/auth/login", json={"identifier": "STU-2021-370", "password": "BrandNew@2026"}
    ).status_code == 200

    assert client.post(
        "/api/auth/login", json={"identifier": "STU-2021-370", "password": TEST_PASSWORD}
    ).status_code == 401


@pytest.mark.api
def test_invalid_token_is_rejected(client):
    """A forged bearer token never grants access."""
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == 401
