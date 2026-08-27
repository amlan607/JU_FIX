"""Unit tests for the authentication business rules (FR-A)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.config import settings
from app.core.constants import AccountStatus, UserRole
from app.core.errors import AuthenticationError, ConflictError, ValidationError
from app.core.security import verify_password
from app.models.user import User
from app.schemas.auth import RegisterRequest, UpdateProfileRequest, validate_password_strength
from app.services import auth_service
from tests.conftest import TEST_PASSWORD, make_user


def _registration(**overrides) -> RegisterRequest:
    """Build a valid registration payload with optional overrides."""
    data = {
        "university_id": "STU-2021-999",
        "full_name": "New Student",
        "password": TEST_PASSWORD,
        "email": "new.student@ju.edu.bd",
        "role": UserRole.STUDENT,
    }
    data.update(overrides)
    return RegisterRequest(**data)


@pytest.mark.unit
@pytest.mark.parametrize(
    "password",
    ["Short1!", "alllowercase1!", "ALLUPPERCASE1!", "NoDigitsHere!", "NoSpecial123"],
)
def test_weak_passwords_are_rejected(password):
    """FR-A3 requires length plus four character classes."""
    with pytest.raises(ValueError):
        validate_password_strength(password)


@pytest.mark.unit
def test_strong_password_is_accepted():
    """A password meeting every rule passes validation."""
    assert validate_password_strength("JuFix@2026") == "JuFix@2026"


@pytest.mark.unit
def test_register_stores_only_a_bcrypt_hash(db_session):
    """FR-A3: the plain password is never persisted."""
    result = auth_service.register_user(db_session, _registration())
    user = result["user"]

    assert user.password_hash != TEST_PASSWORD
    assert verify_password(TEST_PASSWORD, user.password_hash) is True


@pytest.mark.unit
def test_register_starts_pending_verification(db_session):
    """FR-A2: a new account is not usable until it is verified."""
    result = auth_service.register_user(db_session, _registration())

    assert result["user"].status == AccountStatus.PENDING_VERIFICATION.value
    assert result["verification_required"] is True


@pytest.mark.unit
def test_register_rejects_duplicate_university_id(db_session):
    """A university ID identifies exactly one account."""
    make_user(db_session, university_id="STU-2021-999")

    with pytest.raises(ConflictError):
        auth_service.register_user(db_session, _registration(email="other@ju.edu.bd"))


@pytest.mark.unit
def test_register_rejects_duplicate_email(db_session):
    """An email address identifies exactly one account."""
    make_user(db_session, university_id="STU-2021-111", email="taken@ju.edu.bd")

    with pytest.raises(ConflictError):
        auth_service.register_user(db_session, _registration(email="taken@ju.edu.bd"))


@pytest.mark.unit
def test_student_activates_immediately_after_verification(db_session):
    """FR-A2: a student needs no administrator decision."""
    result = auth_service.register_user(db_session, _registration())

    user = auth_service.verify_account(db_session, result["verification_token"])

    assert user.status == AccountStatus.ACTIVE.value
    assert user.email_verified is True


@pytest.mark.unit
def test_doctor_waits_for_admin_approval_after_verification(db_session):
    """FR-J1: doctor registrations require an administrator decision."""
    result = auth_service.register_user(
        db_session,
        _registration(university_id="DOC-9001", email="doc9001@ju.edu.bd", role=UserRole.DOCTOR),
    )

    assert result["admin_approval_required"] is True

    user = auth_service.verify_account(db_session, result["verification_token"])
    assert user.status == AccountStatus.PENDING_APPROVAL.value


@pytest.mark.unit
def test_verification_token_cannot_be_reused(db_session):
    """A single use token is consumed on first use."""
    result = auth_service.register_user(db_session, _registration())
    auth_service.verify_account(db_session, result["verification_token"])

    with pytest.raises(ValidationError):
        auth_service.verify_account(db_session, result["verification_token"])


@pytest.mark.unit
def test_authenticate_returns_a_token_for_valid_credentials(db_session):
    """FR-A4: correct credentials produce a JWT session."""
    make_user(db_session, university_id="STU-2021-370")

    result = auth_service.authenticate(db_session, "STU-2021-370", TEST_PASSWORD)

    assert result["access_token"]
    assert result["user"].university_id == "STU-2021-370"


@pytest.mark.unit
def test_authenticate_accepts_email_as_identifier(db_session):
    """The login screen accepts either the university ID or the email."""
    make_user(db_session, university_id="STU-2021-370", email="oywon@ju.edu.bd")

    result = auth_service.authenticate(db_session, "oywon@ju.edu.bd", TEST_PASSWORD)

    assert result["user"].university_id == "STU-2021-370"


@pytest.mark.unit
def test_authenticate_rejects_a_wrong_password(db_session):
    """An incorrect password never produces a session."""
    make_user(db_session, university_id="STU-2021-370")

    with pytest.raises(AuthenticationError):
        auth_service.authenticate(db_session, "STU-2021-370", "WrongPass1!")


@pytest.mark.unit
def test_unknown_and_wrong_password_share_one_message(db_session):
    """Account enumeration is prevented by an identical failure message."""
    make_user(db_session, university_id="STU-2021-370")

    with pytest.raises(AuthenticationError) as unknown:
        auth_service.authenticate(db_session, "STU-0000-000", TEST_PASSWORD)
    with pytest.raises(AuthenticationError) as wrong:
        auth_service.authenticate(db_session, "STU-2021-370", "WrongPass1!")

    assert str(unknown.value) == str(wrong.value)


@pytest.mark.unit
def test_account_locks_after_five_failed_attempts(db_session):
    """FR-A6: five consecutive failures start a lockout window."""
    user = make_user(db_session, university_id="STU-2021-370")

    for _ in range(settings.MAX_FAILED_LOGIN_ATTEMPTS):
        with pytest.raises(AuthenticationError):
            auth_service.authenticate(db_session, "STU-2021-370", "WrongPass1!")

    db_session.refresh(user)
    assert user.locked_until is not None

    with pytest.raises(AuthenticationError, match="Too many failed attempts"):
        auth_service.authenticate(db_session, "STU-2021-370", TEST_PASSWORD)


@pytest.mark.unit
def test_successful_login_clears_the_failure_counter(db_session):
    """A correct password resets the FR-A6 counter."""
    user = make_user(db_session, university_id="STU-2021-370")

    for _ in range(settings.MAX_FAILED_LOGIN_ATTEMPTS - 1):
        with pytest.raises(AuthenticationError):
            auth_service.authenticate(db_session, "STU-2021-370", "WrongPass1!")

    auth_service.authenticate(db_session, "STU-2021-370", TEST_PASSWORD)

    db_session.refresh(user)
    assert user.failed_login_attempts == 0


@pytest.mark.unit
def test_suspended_account_cannot_sign_in(db_session):
    """FR-J2: a suspended account is refused even with correct credentials."""
    make_user(db_session, university_id="STU-2021-370", status=AccountStatus.SUSPENDED)

    with pytest.raises(AuthenticationError, match="suspended"):
        auth_service.authenticate(db_session, "STU-2021-370", TEST_PASSWORD)


@pytest.mark.unit
def test_password_reset_replaces_the_hash(db_session):
    """FR-A5: the reset flow sets a new password."""
    user = make_user(db_session, university_id="STU-2021-370")
    token = auth_service.start_password_reset(db_session, "STU-2021-370")

    auth_service.complete_password_reset(db_session, token, "BrandNew@2026")

    db_session.refresh(user)
    assert verify_password("BrandNew@2026", user.password_hash) is True
    assert verify_password(TEST_PASSWORD, user.password_hash) is False


@pytest.mark.unit
def test_password_reset_for_unknown_account_returns_none(db_session):
    """An unknown identifier is acknowledged without revealing anything."""
    assert auth_service.start_password_reset(db_session, "STU-0000-000") is None


@pytest.mark.unit
def test_expired_token_is_rejected(db_session):
    """A token past its validity window cannot be used."""
    user = make_user(db_session, university_id="STU-2021-370")
    token_row = auth_service._issue_token(db_session, user, auth_service.PURPOSE_PASSWORD_RESET)
    token_row.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    with pytest.raises(ValidationError, match="expired"):
        auth_service.complete_password_reset(db_session, token_row.token, "BrandNew@2026")


@pytest.mark.unit
def test_update_profile_changes_only_supplied_fields(db_session):
    """FR-A8: an unset field is left untouched."""
    user = make_user(db_session, university_id="STU-2021-370", full_name="Original Name")

    updated = auth_service.update_profile(
        db_session, user, UpdateProfileRequest(department="CSE")
    )

    assert updated.department == "CSE"
    assert updated.full_name == "Original Name"


@pytest.mark.unit
def test_update_profile_rejects_an_empty_request(db_session):
    """A request with nothing to change is a validation error."""
    user = make_user(db_session, university_id="STU-2021-370")

    with pytest.raises(ValidationError):
        auth_service.update_profile(db_session, user, UpdateProfileRequest())


@pytest.mark.unit
def test_registration_requires_a_contact_method():
    """FR-A1: an account needs an email address or a phone number."""
    with pytest.raises(ValueError):
        RegisterRequest(
            university_id="STU-2021-999",
            full_name="No Contact",
            password=TEST_PASSWORD,
        )


@pytest.mark.unit
def test_registration_rejects_an_invalid_bd_phone_number():
    """FR-A1: the phone number must be a valid Bangladeshi mobile number."""
    with pytest.raises(ValueError):
        RegisterRequest(
            university_id="STU-2021-999",
            full_name="Bad Phone",
            password=TEST_PASSWORD,
            phone="12345",
        )


@pytest.mark.unit
def test_registration_accepts_a_valid_bd_phone_number():
    """A correctly formatted Bangladeshi mobile number is accepted."""
    payload = RegisterRequest(
        university_id="STU-2021-999",
        full_name="Good Phone",
        password=TEST_PASSWORD,
        phone="01712345678",
    )
    assert payload.phone == "01712345678"
