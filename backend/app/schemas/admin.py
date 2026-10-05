"""Request schemas for the admin dashboard and reporting (FR-J1 to FR-J5)."""

from pydantic import BaseModel, Field, model_validator


class RegistrationDecision(BaseModel):
    """Approve or reject a registration; a rejection needs a reason (FR-J1)."""

    approve: bool
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def need_reason_to_reject(self) -> "RegistrationDecision":
        """Require a reason whenever a registration is refused."""
        if not self.approve and not (self.reason or "").strip():
            raise ValueError("Provide a reason for rejecting this registration.")
        return self


class AccountAction(BaseModel):
    """Suspend or reactivate an account; a suspension needs a reason (FR-J2)."""

    suspend: bool
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def need_reason_to_suspend(self) -> "AccountAction":
        """Require a reason whenever an account is suspended."""
        if self.suspend and not (self.reason or "").strip():
            raise ValueError("Provide a reason for suspending this account.")
        return self


class SettingsRequest(BaseModel):
    """Operational settings, each bounded to a sensible range (FR-J5)."""

    daily_token_limit: int | None = Field(default=None, ge=1, le=200)
    slot_duration_minutes: int | None = Field(default=None, ge=5, le=120)
    reminder_hours_before: int | None = Field(default=None, ge=1, le=72)
    max_advance_booking_days: int | None = Field(default=None, ge=1, le=180)
