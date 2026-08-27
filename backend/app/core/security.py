"""Password hashing and JSON Web Token helpers.

Passwords are stored only as bcrypt hashes (FR-A3, Consistency Note 11.3).
Access tokens carry a ``jti`` claim so that logout can revoke a single session
rather than relying on the client discarding the token (Consistency Note 11.4).
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

_password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash for ``plain_password``.

    Args:
        plain_password: The raw password supplied by the user.

    Returns:
        str: The bcrypt hash safe to persist in the database.
    """
    return _password_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check ``plain_password`` against a stored bcrypt hash.

    Args:
        plain_password: The raw password supplied at login.
        hashed_password: The bcrypt hash stored on the user record.

    Returns:
        bool: ``True`` when the password matches, otherwise ``False``.
    """
    try:
        return _password_context.verify(plain_password, hashed_password)
    except ValueError:
        # A malformed or truncated hash must never raise into the request cycle.
        return False


def create_access_token(subject: str, role: str, expires_minutes: int | None = None) -> tuple[str, str, datetime]:
    """Create a signed JWT access token.

    Args:
        subject: The user identifier placed in the ``sub`` claim.
        role: The user role placed in the ``role`` claim for fast RBAC checks.
        expires_minutes: Optional override for the token lifetime.

    Returns:
        tuple[str, str, datetime]: The encoded token, its ``jti`` and its expiry.
    """
    minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at + timedelta(minutes=minutes)
    token_id = str(uuid4())

    payload = {
        "sub": str(subject),
        "role": role,
        "jti": token_id,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, token_id, expires_at


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token.

    Args:
        token: The encoded JWT string taken from the Authorization header.

    Returns:
        dict | None: The decoded claims, or ``None`` when the token is invalid
        or expired. Returning ``None`` keeps signature errors out of the logs
        (Coding Standard 3.6).
    """
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
