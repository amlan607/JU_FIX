"""Business rules for medical certificates and sick leave (FR-F1 to FR-F4).

A certificate is only meaningful if it is tied to a real consultation, so a
request must reference a completed appointment between the patient and the
doctor being asked to sign it (FR-F1).

Approval produces a unique reference ID and a digital signature. The signature
is an HMAC over the certificate's immutable fields, keyed with the application
secret, which lets a third party verify authenticity through the public endpoint
without the medical centre disclosing the diagnosis (FR-F3, FR-F4).
"""

import hashlib
import hmac
from datetime import date, datetime, timezone
from secrets import randbelow

from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.config import settings
from app.core.constants import PATIENT_ROLES, AppointmentStatus, CertificateStatus, UserRole
from app.core.errors import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.models.appointment import Appointment
from app.models.certificate import CertificateRequest
from app.models.user import User
from app.schemas.certificate import CreateCertificateRequest

#: Longest sick leave a single certificate may cover.
MAX_LEAVE_DAYS = 30

#: Statuses that still block a second request for the same consultation.
BLOCKING_STATUSES = (CertificateStatus.SUBMITTED.value, CertificateStatus.APPROVED.value)


def _utc_now() -> datetime:
    """Return the current timezone aware UTC time."""
    return datetime.now(timezone.utc)


def generate_reference_id(db: Session) -> str:
    """Build a unique public reference for an approved certificate.

    The format ``JUMC-YYYY-NNNNNN`` is short enough to be typed by a department
    office staff member into the verification page.

    Args:
        db: The active database session.

    Returns:
        str: A reference that is not yet in use.
    """
    while True:
        candidate = f"JUMC-{date.today():%Y}-{randbelow(1_000_000):06d}"
        exists = (
            db.query(CertificateRequest)
            .filter(CertificateRequest.reference_id == candidate)
            .first()
        )
        if exists is None:
            return candidate


def build_signature(certificate: CertificateRequest, patient: User, doctor: User) -> str:
    """Derive the digital signature for an approved certificate (FR-F3).

    The signature covers only fields that must never change after issue. Any
    later alteration produces a different hash, so verification fails.

    Args:
        certificate: The approved certificate.
        patient: The patient the certificate is issued to.
        doctor: The doctor who approved it.

    Returns:
        str: A hexadecimal HMAC-SHA256 digest.
    """
    payload = "|".join(
        [
            certificate.reference_id or "",
            patient.university_id,
            doctor.university_id,
            certificate.leave_start.isoformat(),
            certificate.leave_end.isoformat(),
            str(certificate.appointment_id),
        ]
    )
    return hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def request_certificate(
    db: Session, patient: User, payload: CreateCertificateRequest
) -> CertificateRequest:
    """Create a certificate request after a consultation (FR-F1).

    Args:
        db: The active database session.
        patient: The signed in student or faculty member.
        payload: The validated request.

    Returns:
        CertificateRequest: The submitted request.

    Raises:
        PermissionDeniedError: When the caller is not a patient or not the
            patient on the referenced appointment.
        ValidationError: When the consultation has not been completed or the
            leave period is unreasonable.
        ConflictError: When a request for that consultation is already open.
    """
    if UserRole(patient.role) not in PATIENT_ROLES:
        raise PermissionDeniedError("Only students and faculty or staff can request a certificate.")

    appointment = db.get(Appointment, payload.appointment_id)
    if appointment is None:
        raise NotFoundError("That appointment was not found.")

    if appointment.patient_id != patient.id:
        raise PermissionDeniedError("You can only request a certificate for your own consultation.")

    # FR-F1: a certificate follows a consultation that actually took place.
    if appointment.status != AppointmentStatus.COMPLETED.value:
        raise ValidationError(
            "A certificate can only be requested after the consultation has been completed."
        )

    if payload.leave_start < appointment.appointment_date:
        raise ValidationError("The leave period cannot begin before the consultation date.")

    leave_days = (payload.leave_end - payload.leave_start).days + 1
    if leave_days > MAX_LEAVE_DAYS:
        raise ValidationError(
            f"A single certificate can cover at most {MAX_LEAVE_DAYS} days. "
            "Ask the doctor about an extension."
        )

    existing = (
        db.query(CertificateRequest)
        .filter(
            CertificateRequest.appointment_id == payload.appointment_id,
            CertificateRequest.status.in_(BLOCKING_STATUSES),
        )
        .first()
    )
    if existing is not None:
        raise ConflictError("A certificate request for this consultation is already open.")

    certificate = CertificateRequest(
        patient_id=patient.id,
        doctor_id=appointment.doctor_id,
        appointment_id=appointment.id,
        reason=payload.reason.strip(),
        leave_start=payload.leave_start,
        leave_end=payload.leave_end,
        status=CertificateStatus.SUBMITTED.value,
    )
    db.add(certificate)
    db.flush()

    record_audit(
        db,
        actor_id=patient.id,
        action="certificate.request",
        entity_type="certificate_request",
        entity_id=certificate.id,
        summary=f"Requested {leave_days} day(s) of sick leave from doctor {appointment.doctor_id}.",
    )
    db.commit()
    db.refresh(certificate)
    return certificate


def decide_certificate(
    db: Session, certificate_id: int, doctor: User, approve: bool, remarks: str | None
) -> CertificateRequest:
    """Approve or reject a certificate request (FR-F2, FR-F3).

    Approval assigns the reference ID and the signature that make the document
    verifiable.

    Args:
        db: The active database session.
        certificate_id: The request being decided.
        doctor: The signed in doctor.
        approve: ``True`` to approve, ``False`` to reject.
        remarks: The doctor's remarks. Required on rejection.

    Returns:
        CertificateRequest: The decided request.

    Raises:
        PermissionDeniedError: When the doctor was not the treating doctor.
        ValidationError: When the request has already been decided.
    """
    certificate = db.get(CertificateRequest, certificate_id)
    if certificate is None:
        raise NotFoundError("That certificate request was not found.")

    if doctor.role != UserRole.DOCTOR.value:
        raise PermissionDeniedError("Only a doctor can decide a certificate request.")

    if certificate.doctor_id != doctor.id:
        raise PermissionDeniedError(
            "Only the doctor who conducted the consultation can decide this request."
        )

    if certificate.status != CertificateStatus.SUBMITTED.value:
        raise ValidationError("This request has already been decided.")

    if not approve and not (remarks or "").strip():
        raise ValidationError("Provide remarks explaining why the request is rejected.")

    certificate.doctor_remarks = (remarks or "").strip() or None
    certificate.decided_at = _utc_now()

    if approve:
        patient = db.get(User, certificate.patient_id)
        certificate.status = CertificateStatus.APPROVED.value
        certificate.reference_id = generate_reference_id(db)
        certificate.signature = build_signature(certificate, patient, doctor)
        action = "certificate.approve"
        summary = f"Approved certificate {certificate.reference_id}."
    else:
        certificate.status = CertificateStatus.REJECTED.value
        action = "certificate.reject"
        summary = "Rejected the certificate request."

    record_audit(
        db,
        actor_id=doctor.id,
        action=action,
        entity_type="certificate_request",
        entity_id=certificate.id,
        summary=summary,
    )
    db.commit()
    db.refresh(certificate)
    return certificate


def get_certificate_for_user(db: Session, certificate_id: int, viewer: User) -> CertificateRequest:
    """Load a certificate request the viewer may see.

    Args:
        db: The active database session.
        certificate_id: The request identifier.
        viewer: The signed in user.

    Returns:
        CertificateRequest: The requested record.

    Raises:
        PermissionDeniedError: When the viewer is neither the patient nor the doctor.
    """
    certificate = db.get(CertificateRequest, certificate_id)
    if certificate is None:
        raise NotFoundError("That certificate request was not found.")

    if viewer.id not in {certificate.patient_id, certificate.doctor_id}:
        raise PermissionDeniedError("You do not have access to this certificate request.")

    return certificate


def list_for_patient(db: Session, patient: User) -> list[CertificateRequest]:
    """List the signed in patient's certificate requests, newest first."""
    return (
        db.query(CertificateRequest)
        .filter(CertificateRequest.patient_id == patient.id)
        .order_by(CertificateRequest.id.desc())
        .all()
    )


def list_for_doctor(db: Session, doctor: User, status: str | None = None) -> list[CertificateRequest]:
    """List the certificate requests addressed to a doctor (FR-F2).

    Args:
        db: The active database session.
        doctor: The signed in doctor.
        status: Optional status filter.

    Returns:
        list[CertificateRequest]: Requests, oldest submission first so the queue
        is worked in the order it arrived.
    """
    if doctor.role != UserRole.DOCTOR.value:
        raise PermissionDeniedError("Only a doctor can review certificate requests.")

    query = db.query(CertificateRequest).filter(CertificateRequest.doctor_id == doctor.id)
    if status:
        query = query.filter(CertificateRequest.status == status)
    return query.order_by(CertificateRequest.created_at).all()


def verify_certificate(db: Session, reference_id: str) -> dict:
    """Verify a certificate by its public reference (FR-F4).

    This endpoint is public, so the payload confirms authenticity and the leave
    window only. The medical reason is never disclosed.

    Args:
        db: The active database session.
        reference_id: The reference printed on the certificate.

    Returns:
        dict: The verification result.
    """
    certificate = (
        db.query(CertificateRequest)
        .filter(
            CertificateRequest.reference_id == reference_id.strip().upper(),
            CertificateRequest.status == CertificateStatus.APPROVED.value,
        )
        .first()
    )

    if certificate is None:
        return {
            "valid": False,
            "message": "No approved certificate matches that reference ID.",
        }

    patient = db.get(User, certificate.patient_id)
    doctor = db.get(User, certificate.doctor_id)

    expected = build_signature(certificate, patient, doctor)
    if not hmac.compare_digest(expected, certificate.signature or ""):
        # The stored data no longer matches the signature taken at approval.
        return {
            "valid": False,
            "reference_id": certificate.reference_id,
            "message": "This certificate failed the authenticity check. Contact the medical centre.",
        }

    return {
        "valid": True,
        "reference_id": certificate.reference_id,
        "patient_name": patient.full_name,
        "patient_university_id": patient.university_id,
        "issued_by": doctor.full_name,
        "leave_start": certificate.leave_start,
        "leave_end": certificate.leave_end,
        "leave_days": certificate.leave_days,
        "issued_on": certificate.decided_at,
        "message": "This is a genuine certificate issued by the JU Medical Centre.",
    }


def to_response_dict(db: Session, certificate: CertificateRequest) -> dict:
    """Expand a certificate request with the names the UI needs."""
    patient = db.get(User, certificate.patient_id)
    doctor = db.get(User, certificate.doctor_id)

    return {
        "id": certificate.id,
        "reference_id": certificate.reference_id,
        "patient_id": certificate.patient_id,
        "doctor_id": certificate.doctor_id,
        "appointment_id": certificate.appointment_id,
        "reason": certificate.reason,
        "leave_start": certificate.leave_start,
        "leave_end": certificate.leave_end,
        "leave_days": certificate.leave_days,
        "status": certificate.status,
        "doctor_remarks": certificate.doctor_remarks,
        "decided_at": certificate.decided_at,
        "created_at": certificate.created_at,
        "patient_name": patient.full_name if patient else None,
        "patient_university_id": patient.university_id if patient else None,
        "doctor_name": doctor.full_name if doctor else None,
    }
