"""Request and response schemas for accounts and authentication (FR-A)."""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.core.constants import UserRole
from app.schemas.common import ORMModel

#: Bangladeshi mobile numbers: optional +88 country code then 01XXXXXXXXX.
BD_PHONE_PATTERN = re.compile(r"^(?:\+?88)?01[3-9]\d{8}$")

#: Password rules from FR-A3.
PASSWORD_MIN_LENGTH = 8
PASSWORD_RULES = (
    (re.compile(r"[A-Z]"), "one uppercase letter"),
    (re.compile(r"[a-z]"), "one lowercase letter"),
    (re.compile(r"\d"), "one digit"),
    (re.compile(r"[^A-Za-z0-9]"), "one special character"),
)


def validate_password_strength(password: str) -> str:
    """Enforce the password policy defined by FR-A3.

    Args:
        password: The candidate password.

    Returns:
        str: The same password when it satisfies every rule.

    Raises:
        ValueError: When the password is too short or misses a character class.
    """
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long.")

    missing = [label for pattern, label in PASSWORD_RULES if not pattern.search(password)]
    if missing:
        raise ValueError("Password must contain at least " + ", ".join(missing) + ".")
    return password


class RegisterRequest(BaseModel):
    """Payload for creating an account (FR-A1, FR-A3).

    At least one of ``email`` or ``phone`` must be supplied so the account has a
    contact method that verification and password reset can use.
    """

    university_id: str = Field(min_length=3, max_length=30)
    full_name: str = Field(min_length=2, max_length=120)
    password: str
    email: EmailStr | None = None
    phone: str | None = None
    role: UserRole = UserRole.STUDENT
    department: str | None = Field(default=None, max_length=120)
    designation: str | None = Field(default=None, max_length=120)

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        """Apply the FR-A3 password policy."""
        return validate_password_strength(value)

    @field_validator("phone")
    @classmethod
    def check_phone(cls, value: str | None) -> str | None:
        """Reject phone numbers that are not valid Bangladeshi mobile numbers."""
        if value and not BD_PHONE_PATTERN.match(value.replace(" ", "")):
            raise ValueError("Enter a valid Bangladeshi mobile number, for example 01712345678.")
        return value

    @model_validator(mode="after")
    def check_contact_present(self) -> "RegisterRequest":
        """Require at least one contact method (FR-A1)."""
        if not self.email and not self.phone:
            raise ValueError("Provide an email address or a phone number.")
        return self


class LoginRequest(BaseModel):
    """Payload for signing in (FR-A4).

    ``identifier`` accepts either the university ID or the registered email so
    the login screen needs only one field.
    """

    identifier: str = Field(min_length=3, max_length=160)
    password: str = Field(min_length=1)


class VerifyAccountRequest(BaseModel):
    """Payload for activating an account with a verification token (FR-A2)."""

    token: str = Field(min_length=6, max_length=64)


class ForgotPasswordRequest(BaseModel):
    """Payload for starting a password reset (FR-A5)."""

    identifier: str = Field(min_length=3, max_length=160)


class ResetPasswordRequest(BaseModel):
    """Payload for completing a password reset (FR-A5)."""

    token: str = Field(min_length=6, max_length=64)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def check_password(cls, value: str) -> str:
        """Apply the FR-A3 password policy to the replacement password."""
        return validate_password_strength(value)


class UpdateProfileRequest(BaseModel):
    """Payload for editing an own profile (FR-A8)."""

    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = None
    department: str | None = Field(default=None, max_length=120)
    designation: str | None = Field(default=None, max_length=120)
    photo_url: str | None = Field(default=None, max_length=255)

    @field_validator("phone")
    @classmethod
    def check_phone(cls, value: str | None) -> str | None:
        """Reject phone numbers that are not valid Bangladeshi mobile numbers."""
        if value and not BD_PHONE_PATTERN.match(value.replace(" ", "")):
            raise ValueError("Enter a valid Bangladeshi mobile number, for example 01712345678.")
        return value


class UserResponse(ORMModel):
    """Public view of a user account.

    The password hash, lockout counters and internal timestamps are deliberately
    excluded so the API returns only the minimum necessary information (NFR-B).
    """

    id: int
    university_id: str
    full_name: str
    email: str | None
    phone: str | None
    role: str
    status: str
    department: str | None
    designation: str | None
    photo_url: str | None
    email_verified: bool


class LoginResponse(BaseModel):
    """Successful login payload carrying the JWT and the signed in user."""

    access_token: str
    token_type: str = "bearer"
    expires_at: str
    user: UserResponse


class RegisterResponse(BaseModel):
    """Registration result including the next step for the user."""

    user: UserResponse
    verification_required: bool
    admin_approval_required: bool
    message: str
    verification_token: str | None = None
