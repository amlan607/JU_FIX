"""Project wide constants and enumerations.

Centralising these values avoids the hard coded strings that Coding Standard 3.1
forbids and keeps role names consistent between the Model, Controller and View.
"""

from enum import Enum


class UserRole(str, Enum):
    """The five roles defined by the SRS (FR-A7)."""

    STUDENT = "student"
    FACULTY = "faculty"
    DOCTOR = "doctor"
    PHARMACIST = "pharmacist"
    ADMIN = "admin"


class AccountStatus(str, Enum):
    """Lifecycle states of a user account."""

    PENDING_VERIFICATION = "pending_verification"
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    SUSPENDED = "suspended"


class AppointmentStatus(str, Enum):
    """Lifecycle states of an appointment (FR-C1 to FR-C7)."""

    BOOKED = "booked"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class CertificateStatus(str, Enum):
    """Lifecycle states of a medical certificate request (FR-F1 to FR-F4)."""

    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class PrescriptionStatus(str, Enum):
    """Lifecycle states of a digital prescription (FR-D1)."""

    DRAFT = "draft"
    ISSUED = "issued"
    DISPENSED = "dispensed"
    CANCELLED = "cancelled"


class RecordType(str, Enum):
    """Categories of clinical entry stored in the Electronic Health Record (FR-D2)."""

    CONSULTATION = "consultation"
    DIAGNOSIS = "diagnosis"
    LAB_RESULT = "lab_result"
    VACCINATION = "vaccination"
    NOTE = "note"


#: Roles whose registrations require an administrator decision before activation (FR-J1).
ROLES_REQUIRING_APPROVAL = {UserRole.DOCTOR, UserRole.PHARMACIST, UserRole.ADMIN}

#: Roles that may act as a patient in clinical workflows.
PATIENT_ROLES = {UserRole.STUDENT, UserRole.FACULTY}

#: ISO 8601 is the project wide date/time exchange format.
ISO_DATE_FORMAT = "%Y-%m-%d"
