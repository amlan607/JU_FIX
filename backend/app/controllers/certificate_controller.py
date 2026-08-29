"""HTTP controller for medical certificates and sick leave (FR-F1 to FR-F4)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.constants import UserRole
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.responses import success_response
from app.models.user import User
from app.schemas.certificate import CreateCertificateRequest, DecideCertificateRequest
from app.services import certificate_service

router = APIRouter(prefix="/certificates", tags=["Medical Certificate and Sick Leave"])


@router.get("/verify")
def verify_certificate(
    reference_id: str = Query(alias="reference", min_length=4, max_length=30),
    db: Session = Depends(get_db),
) -> dict:
    """Verify a certificate by its public reference (FR-F4).

    This endpoint is intentionally unauthenticated so a department office can
    check a certificate a student hands them. It discloses no clinical detail.
    """
    return success_response(certificate_service.verify_certificate(db, reference_id))


@router.post("", status_code=status.HTTP_201_CREATED)
def request_certificate(
    payload: CreateCertificateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT, UserRole.FACULTY)),
) -> dict:
    """Request a medical certificate after a consultation (FR-F1)."""
    certificate = certificate_service.request_certificate(db, current_user, payload)
    return success_response(certificate_service.to_response_dict(db, certificate))


@router.get("")
def list_my_certificates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT, UserRole.FACULTY)),
) -> dict:
    """List the signed in patient's certificate requests."""
    certificates = certificate_service.list_for_patient(db, current_user)
    return success_response(
        [certificate_service.to_response_dict(db, item) for item in certificates]
    )


@router.get("/review-queue")
def list_review_queue(
    certificate_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR)),
) -> dict:
    """List the certificate requests waiting for this doctor (FR-F2)."""
    certificates = certificate_service.list_for_doctor(db, current_user, certificate_status)
    return success_response(
        [certificate_service.to_response_dict(db, item) for item in certificates]
    )


@router.get("/{certificate_id}")
def get_certificate(
    certificate_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return one certificate request the signed in user may see."""
    certificate = certificate_service.get_certificate_for_user(db, certificate_id, current_user)
    return success_response(certificate_service.to_response_dict(db, certificate))


@router.patch("/{certificate_id}/decision")
def decide_certificate(
    certificate_id: int,
    payload: DecideCertificateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR)),
) -> dict:
    """Approve or reject a certificate request with remarks (FR-F2, FR-F3)."""
    certificate = certificate_service.decide_certificate(
        db, certificate_id, current_user, payload.approve, payload.remarks
    )
    return success_response(certificate_service.to_response_dict(db, certificate))
