"""Business rules for accounts and authentication (FR-A1 to FR-A9).

The Controller layer stays lightweight and delegates every rule here
(Architecture 1.3 and 1.5). Nothing in this module imports FastAPI.
"""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.config import settings
from app.core.constants import ROLES_REQUIRING_APPROVAL, AccountStatus, UserRole
from app.core.errors import AuthenticationError, ConflictError, NotFoundError, ValidationError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.session_token import SessionToken
from app.models.user import User
from app.models.verification_token import VerificationToken
from app.schemas.auth import RegisterRequest, UpdateProfileRequest

#: Purpose values stored on ``VerificationToken.purpose``.
PURPOSE_ACCOUNT_VERIFICATION = "account_verification"
PURPOSE_PASSWORD_RESET = "password_reset"

#: How long a verification or reset token stays usable.
TOKEN_VALIDITY_HOURS = 24


def _utc_now() -> datetime:
    """Return the current timezone aware UTC time."""
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    """Normalise a stored timestamp to a timezone aware UTC value.

    SQLite returns naive datetimes even for ``DateTime(timezone=True)`` columns,
    so comparisons must attach UTC before use.

    Args:
        value: The stored timestamp, possibly naive.

    Returns:
        datetime | None: A timezone aware timestamp, or ``None``.
    """
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _issue_token(db: Session, user: User, purpose: str) -> VerificationToken:
    """Create a single use token bound to a user and purpose.

    Args:
        db: The active database session.
        user: The account the token belongs to.
        purpose: Either account verification or password reset.

    Returns:
        VerificationToken: The pending token row.
    """
    token = VerificationToken(
        user_id=user.id,
        purpose=purpose,
        token=secrets.token_urlsafe(24),
        expires_at=_utc_now() + timedelta(hours=TOKEN_VALIDITY_HOURS),
    )
    db.add(token)
    return token


def _consume_token(db: Session, raw_token: str, purpose: str) -> User:
    """Validate and consume a single use token.

    Args:
        db: The active database session.
        raw_token: The token value supplied by the user.
        purpose: The purpose the token must match.

    Returns:
        User: The account the token belongs to.

    Raises:
        ValidationError: When the token is unknown, already used or expired.
    """
    token = (
        db.query(VerificationToken)
        .filter(VerificationToken.token == raw_token, VerificationToken.purpose == purpose)
        .first()
    )
    if token is None or token.used_at is not None:
        raise ValidationError("This link is not valid. Request a new one.")

    if _as_utc(token.expires_at) < _utc_now():
        raise ValidationError("This link has expired. Request a new one.")

    user = db.get(User, token.user_id)
    if user is None:
        raise ValidationError("This link is not valid. Request a new one.")

    token.used_at = _utc_now()
    return user


def register_user(db: Session, payload: RegisterRequest) -> dict:
    """Create a new account (FR-A1, FR-A2, FR-A3, FR-J1).

    Student and faculty accounts activate as soon as the contact method is
    verified. Doctor, pharmacist and admin accounts additionally wait for an
    administrator decision.

    Args:
        db: The active database session.
        payload: The validated registration request.

    Returns:
        dict: The created user and the next step required of them.

    Raises:
        ConflictError: When the university ID or email is already registered.
    """
    identifier = payload.university_id.strip()

    if db.query(User).filter(func.lower(User.university_id) == identifier.lower()).first():
        raise ConflictError("An account with this university ID already exists.")

    if payload.email and db.query(User).filter(func.lower(User.email) == payload.email.lower()).first():
        raise ConflictError("An account with this email address already exists.")

    user = User(
        university_id=identifier,
        full_name=payload.full_name.strip(),
        email=payload.email.lower() if payload.email else None,
        phone=payload.phone,
        password_hash=hash_password(payload.password),
        role=payload.role.value,
        status=AccountStatus.PENDING_VERIFICATION.value,
        department=payload.department,
        designation=payload.designation,
    )
    db.add(user)
    db.flush()

    verification = _issue_token(db, user, PURPOSE_ACCOUNT_VERIFICATION)
    needs_approval = payload.role in ROLES_REQUIRING_APPROVAL

    record_audit(
        db,
        actor_id=user.id,
        action="account.register",
        entity_type="user",
        entity_id=user.id,
        summary=f"Registered with role {user.role}.",
    )
    db.commit()
    db.refresh(user)

    message = (
        "Account created. Verify your contact details, then wait for administrator approval."
        if needs_approval
        else "Account created. Verify your contact details to activate the account."
    )

    return {
        "user": user,
        "verification_required": True,
        "admin_approval_required": needs_approval,
        "message": message,
        # Development only: a real deployment emails this token instead of returning it.
        "verification_token": verification.token if settings.ENVIRONMENT != "production" else None,
    }


def verify_account(db: Session, raw_token: str) -> User:
    """Activate an account using its verification token (FR-A2).

    Args:
        db: The active database session.
        raw_token: The verification token from the emailed link.

    Returns:
        User: The updated account.
    """
    user = _consume_token(db, raw_token, PURPOSE_ACCOUNT_VERIFICATION)
    user.email_verified = True

    if UserRole(user.role) in ROLES_REQUIRING_APPROVAL:
        user.status = AccountStatus.PENDING_APPROVAL.value
    else:
        user.status = AccountStatus.ACTIVE.value

    record_audit(
        db,
        actor_id=user.id,
        action="account.verify",
        entity_type="user",
        entity_id=user.id,
        summary=f"Contact verified. Status set to {user.status}.",
    )
    db.commit()
    db.refresh(user)
    return user


def _reject_if_locked(user: User) -> None:
    """Refuse login while a lockout window is active (FR-A6).

    Args:
        user: The account attempting to sign in.

    Raises:
        AuthenticationError: When the account is still locked.
    """
    locked_until = _as_utc(user.locked_until)
    if locked_until and locked_until > _utc_now():
        remaining = int((locked_until - _utc_now()).total_seconds() // 60) + 1
        raise AuthenticationError(
            f"Too many failed attempts. Try again in about {remaining} minute(s)."
        )


def _register_failed_attempt(db: Session, user: User) -> None:
    """Count a failed login and lock the account when the limit is reached.

    Args:
        db: The active database session.
        user: The account that failed authentication.
    """
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
        user.locked_until = _utc_now() + timedelta(minutes=settings.ACCOUNT_LOCK_MINUTES)
        user.failed_login_attempts = 0
        record_audit(
            db,
            actor_id=user.id,
            action="account.lock",
            entity_type="user",
            entity_id=user.id,
            summary="Locked after consecutive failed sign in attempts.",
        )
    db.commit()


def _status_message(status: str) -> str:
    """Return the user facing explanation for a non active account status."""
    return {
        AccountStatus.PENDING_VERIFICATION.value: "Verify your account before signing in.",
        AccountStatus.PENDING_APPROVAL.value: "Your account is waiting for administrator approval.",
        AccountStatus.SUSPENDED.value: "This account is suspended. Contact the medical centre office.",
    }.get(status, "This account cannot sign in.")


def authenticate(db: Session, identifier: str, password: str) -> dict:
    """Verify credentials and issue a JWT session (FR-A4, FR-A6).

    The same message is returned for an unknown account and a wrong password so
    the endpoint cannot be used to discover which university IDs exist.

    Args:
        db: The active database session.
        identifier: University ID or registered email address.
        password: The submitted password.

    Returns:
        dict: The access token, its expiry and the signed in user.

    Raises:
        AuthenticationError: When the credentials or the account state prevent login.
    """
    handle = identifier.strip().lower()
    user = (
        db.query(User)
        .filter((func.lower(User.university_id) == handle) | (func.lower(User.email) == handle))
        .first()
    )

    if user is None:
        raise AuthenticationError("The university ID or password is incorrect.")

    _reject_if_locked(user)

    if not verify_password(password, user.password_hash):
        _register_failed_attempt(db, user)
        raise AuthenticationError("The university ID or password is incorrect.")

    if user.status != AccountStatus.ACTIVE.value:
        raise AuthenticationError(_status_message(user.status))

    user.failed_login_attempts = 0
    user.locked_until = None

    token, token_id, expires_at = create_access_token(subject=user.id, role=user.role)
    db.add(SessionToken(token_id=token_id, user_id=user.id, expires_at=expires_at))

    record_audit(
        db,
        actor_id=user.id,
        action="account.login",
        entity_type="user",
        entity_id=user.id,
        summary="Signed in successfully.",
    )
    db.commit()
    db.refresh(user)

    return {"access_token": token, "expires_at": expires_at.isoformat(), "user": user}


def logout(db: Session, user: User, token_id: str) -> None:
    """Revoke the current session (FR-A9, Consistency Note 11.4).

    Args:
        db: The active database session.
        user: The signed in user.
        token_id: The ``jti`` claim of the token being revoked.
    """
    session_token = (
        db.query(SessionToken)
        .filter(SessionToken.token_id == token_id, SessionToken.user_id == user.id)
        .first()
    )
    if session_token and session_token.revoked_at is None:
        session_token.revoked_at = _utc_now()

    record_audit(
        db,
        actor_id=user.id,
        action="account.logout",
        entity_type="user",
        entity_id=user.id,
        summary="Signed out and revoked the session.",
    )
    db.commit()


def start_password_reset(db: Session, identifier: str) -> str | None:
    """Issue a password reset token for a verified contact method (FR-A5).

    The caller always receives the same acknowledgement so the endpoint cannot
    be used to enumerate accounts.

    Args:
        db: The active database session.
        identifier: University ID or registered email address.

    Returns:
        str | None: The reset token outside production, otherwise ``None``.
    """
    handle = identifier.strip().lower()
    user = (
        db.query(User)
        .filter((func.lower(User.university_id) == handle) | (func.lower(User.email) == handle))
        .first()
    )
    if user is None:
        return None

    token = _issue_token(db, user, PURPOSE_PASSWORD_RESET)
    record_audit(
        db,
        actor_id=user.id,
        action="account.reset_requested",
        entity_type="user",
        entity_id=user.id,
        summary="Password reset link requested.",
    )
    db.commit()
    return token.token if settings.ENVIRONMENT != "production" else None


def complete_password_reset(db: Session, raw_token: str, new_password: str) -> User:
    """Set a new password and end every existing session (FR-A5).

    Args:
        db: The active database session.
        raw_token: The reset token from the emailed link.
        new_password: The replacement password, already policy checked.

    Returns:
        User: The updated account.
    """
    user = _consume_token(db, raw_token, PURPOSE_PASSWORD_RESET)

    user.password_hash = hash_password(new_password)
    user.failed_login_attempts = 0
    user.locked_until = None

    # A password change must end sessions opened with the previous password.
    active_sessions = (
        db.query(SessionToken)
        .filter(SessionToken.user_id == user.id, SessionToken.revoked_at.is_(None))
        .all()
    )
    for session_token in active_sessions:
        session_token.revoked_at = _utc_now()

    record_audit(
        db,
        actor_id=user.id,
        action="account.reset_completed",
        entity_type="user",
        entity_id=user.id,
        summary="Password reset completed and existing sessions revoked.",
    )
    db.commit()
    db.refresh(user)
    return user


def update_profile(db: Session, user: User, payload: UpdateProfileRequest) -> User:
    """Apply an own profile edit (FR-A8).

    Args:
        db: The active database session.
        user: The signed in user editing their own profile.
        payload: The fields to change. Unset fields are left untouched.

    Returns:
        User: The updated account.

    Raises:
        ValidationError: When the request contains no changes.
    """
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    if not changes:
        raise ValidationError("Provide at least one field to update.")

    for field, value in changes.items():
        setattr(user, field, value)

    record_audit(
        db,
        actor_id=user.id,
        action="account.profile_update",
        entity_type="user",
        entity_id=user.id,
        summary="Updated own profile fields: " + ", ".join(sorted(changes)),
    )
    db.commit()
    db.refresh(user)
    return user


def get_user_or_404(db: Session, user_id: int) -> User:
    """Fetch a user by identifier.

    Args:
        db: The active database session.
        user_id: The account identifier.

    Returns:
        User: The requested account.

    Raises:
        NotFoundError: When no account has that identifier.
    """
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("That account was not found.")
    return user
