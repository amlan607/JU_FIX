"""Smoke tests for the application factory and shared infrastructure."""

import pytest

from app.core.responses import error_response, success_response
from app.core.security import hash_password, verify_password


@pytest.mark.api
def test_health_endpoint_reports_ok(client):
    """The health endpoint answers with the standard success envelope."""
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert body["error"] is None


@pytest.mark.unit
def test_success_response_shape():
    """A success envelope always carries data and a null error."""
    assert success_response({"a": 1}) == {"success": True, "data": {"a": 1}, "error": None}


@pytest.mark.unit
def test_error_response_shape():
    """An error envelope always carries a code and a message."""
    body = error_response("Not allowed", "permission_denied")

    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "permission_denied"


@pytest.mark.unit
def test_password_hash_is_not_reversible():
    """Passwords are stored as bcrypt hashes, never in plain text (FR-A3)."""
    hashed = hash_password("JuFix@2026")

    assert hashed != "JuFix@2026"
    assert verify_password("JuFix@2026", hashed) is True
    assert verify_password("WrongPassword1!", hashed) is False
