"""Request and response schemas for the admin dashboard and reporting (FR-J)."""

from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

from app.core.constants import AccountStatus, UserRole


class PendingRegistration(BaseModel):
    """A registration awaiting an administrator decision (FR-J1)."""

    user_id: int
    university_id: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    role: str
    department: str | None = None
    designation: str | None = None
    requested_at: datetime | None = None


class ApprovalDecisionRequest(BaseModel):
    """Payload for approving or rejecting a registration (FR-J1)."""

    approve: bool
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_reason_on_rejection(self) -> "ApprovalDecisionRequest":
        """FR-J1 requires a reason whenever a registration is refused."""
        if not self.approve and not (self.reason or "").strip():
            raise ValueError("Provide a reason for rejecting this registration.")
        return self


class AccountActionRequest(BaseModel):
    """Payload for suspending or reactivating an account (FR-J2)."""

    suspend: bool
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_reason_on_suspension(self) -> "AccountActionRequest":
        """A suspension must be justified so the audit trail is meaningful."""
        if self.suspend and not (self.reason or "").strip():
            raise ValueError("Provide a reason for suspending this account.")
        return self


class ManagedUser(BaseModel):
    """An account row on the user management screen (FR-J2)."""

    user_id: int
    university_id: str
    full_name: str
    email: str | None = None
    role: str
    status: str
    department: str | None = None
    created_at: datetime | None = None


class DashboardMetrics(BaseModel):
    """Headline operational figures for the admin dashboard (FR-J3)."""

    report_date: date
    patients_today: int
    appointments_today: int
    completed_today: int
    cancelled_today: int
    no_show_today: int
    prescriptions_issued_today: int
    certificates_pending: int
    pending_registrations: int
    active_users: int
    suspended_users: int


class DoctorWorkloadRow(BaseModel):
    """One doctor's workload over the reporting window (FR-J3)."""

    doctor_id: int
    doctor_name: str
    speciality: str | None = None
    total_appointments: int
    completed: int
    cancelled: int
    no_show: int
    completion_rate: float


class DailyVolumeRow(BaseModel):
    """Appointment volume for one calendar day (FR-J3)."""

    day: date
    total: int
    completed: int
    cancelled: int
    no_show: int
    unique_patients: int


class AnalyticsReport(BaseModel):
    """The exportable platform report (FR-J4)."""

    start_date: date
    end_date: date
    generated_at: datetime
    total_appointments: int
    total_patients_seen: int
    total_prescriptions: int
    total_certificates_approved: int
    daily_volumes: list[DailyVolumeRow]
    doctor_workload: list[DoctorWorkloadRow]


class SystemSettingsResponse(BaseModel):
    """The administrator configurable operational settings (FR-J5)."""

    daily_token_limit: int
    slot_duration_minutes: int
    reminder_hours_before: int
    max_advance_booking_days: int


class UpdateSettingsRequest(BaseModel):
    """Payload for changing the operational settings (FR-J5)."""

    daily_token_limit: int | None = Field(default=None, ge=1, le=200)
    slot_duration_minutes: int | None = Field(default=None, ge=5, le=120)
    reminder_hours_before: int | None = Field(default=None, ge=1, le=72)
    max_advance_booking_days: int | None = Field(default=None, ge=1, le=180)

    @model_validator(mode="after")
    def require_at_least_one_change(self) -> "UpdateSettingsRequest":
        """Reject a request that changes nothing."""
        if not self.model_dump(exclude_none=True):
            raise ValueError("Provide at least one setting to update.")
        return self


#: Roles an administrator may filter the user list by.
FILTERABLE_ROLES = {role.value for role in UserRole}

#: Statuses an administrator may filter the user list by.
FILTERABLE_STATUSES = {status.value for status in AccountStatus}
