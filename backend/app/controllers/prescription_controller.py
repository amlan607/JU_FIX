"""HTTP controller for digital prescription management (FR-D1, FR-D3)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.constants import UserRole
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.responses import success_response
from app.models.user import User
from app.schemas.prescription import (
    CreatePrescriptionRequest,
    DispensePrescriptionRequest,
    UpdatePrescriptionRequest,
)
from app.services import prescription_service

router = APIRouter(prefix="/prescriptions", tags=["Digital Prescription Management"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_prescription(
    payload: CreatePrescriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR)),
) -> dict:
    """Create a prescription draft (FR-D1)."""
    prescription = prescription_service.create_prescription(db, current_user, payload)
    return success_response(prescription_service.to_response_dict(db, prescription))


@router.get("/my-prescriptions")
def list_my_prescriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT, UserRole.FACULTY)),
) -> dict:
    """List the signed in patient's issued prescriptions (FR-D3)."""
    prescriptions = prescription_service.list_for_patient(db, current_user)
    return success_response(
        [prescription_service.to_response_dict(db, item) for item in prescriptions]
    )


@router.get("/written")
def list_written_prescriptions(
    prescription_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR)),
) -> dict:
    """List the prescriptions written by the signed in doctor."""
    prescriptions = prescription_service.list_for_doctor(db, current_user, prescription_status)
    return success_response(
        [prescription_service.to_response_dict(db, item) for item in prescriptions]
    )


@router.get("/pharmacy-queue")
def list_pharmacy_queue(
    prescription_status: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.PHARMACIST)),
) -> dict:
    """List prescriptions waiting at the pharmacy counter."""
    prescriptions = prescription_service.list_pharmacy_queue(db, current_user, prescription_status)
    return success_response(
        [prescription_service.to_response_dict(db, item) for item in prescriptions]
    )


@router.get("/lookup")
def lookup_by_reference(
    reference_code: str = Query(alias="code", min_length=4, max_length=30),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.PHARMACIST)),
) -> dict:
    """Find an issued prescription by the code printed on it."""
    prescription = prescription_service.find_by_reference(db, reference_code, current_user)
    return success_response(prescription_service.to_response_dict(db, prescription))


@router.get("/{prescription_id}")
def get_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return one prescription the signed in user is allowed to see (FR-D3)."""
    prescription = prescription_service.get_prescription_for_user(db, prescription_id, current_user)
    return success_response(prescription_service.to_response_dict(db, prescription))


@router.patch("/{prescription_id}")
def update_prescription(
    prescription_id: int,
    payload: UpdatePrescriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR)),
) -> dict:
    """Edit a draft prescription before it is issued."""
    prescription = prescription_service.update_prescription(
        db, prescription_id, current_user, payload
    )
    return success_response(prescription_service.to_response_dict(db, prescription))


@router.patch("/{prescription_id}/issue")
def issue_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR)),
) -> dict:
    """Publish a draft to the patient and the pharmacy (FR-D1, FR-D3)."""
    prescription = prescription_service.issue_prescription(db, prescription_id, current_user)
    return success_response(prescription_service.to_response_dict(db, prescription))


@router.patch("/{prescription_id}/cancel")
def cancel_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR)),
) -> dict:
    """Cancel a prescription that has not been dispensed."""
    prescription = prescription_service.cancel_prescription(db, prescription_id, current_user)
    return success_response(prescription_service.to_response_dict(db, prescription))


@router.patch("/{prescription_id}/dispense")
def dispense_prescription(
    prescription_id: int,
    payload: DispensePrescriptionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.PHARMACIST)),
) -> dict:
    """Record that the pharmacy has dispensed the medicines."""
    prescription = prescription_service.dispense_prescription(
        db, prescription_id, current_user, payload.note
    )
    return success_response(prescription_service.to_response_dict(db, prescription))
