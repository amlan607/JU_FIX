"""HTTP controller for digital prescriptions (FR-D1, FR-D3)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.constants import UserRole
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.responses import success_response as ok
from app.models.user import User
from app.schemas.prescription import CreatePrescriptionRequest, DispenseRequest
from app.services import prescription_service as service

router = APIRouter(prefix="/prescriptions", tags=["Digital Prescription Management"])
Patient = Depends(require_roles(UserRole.STUDENT, UserRole.FACULTY))
Doctor = Depends(require_roles(UserRole.DOCTOR))
Pharmacist = Depends(require_roles(UserRole.PHARMACIST))


@router.post("", status_code=status.HTTP_201_CREATED)
def create(payload: CreatePrescriptionRequest, db: Session = Depends(get_db), user: User = Doctor) -> dict:
    """Create a prescription draft (FR-D1)."""
    return ok(service.to_response_dict(db, service.create_prescription(db, user, payload)))


@router.get("/my-prescriptions")
def my_prescriptions(db: Session = Depends(get_db), user: User = Patient) -> dict:
    """List the patient's issued prescriptions (FR-D3)."""
    return ok([service.to_response_dict(db, p) for p in service.list_for_patient(db, user)])


@router.get("/written")
def written(db: Session = Depends(get_db), user: User = Doctor) -> dict:
    """List the prescriptions the doctor has written."""
    return ok([service.to_response_dict(db, p) for p in service.list_for_doctor(db, user)])


@router.get("/pharmacy-queue")
def pharmacy_queue(state: str | None = Query(default=None, alias="status"), db: Session = Depends(get_db),
                   user: User = Pharmacist) -> dict:
    """List prescriptions waiting at the pharmacy counter."""
    return ok([service.to_response_dict(db, p) for p in service.list_pharmacy_queue(db, user, state)])


@router.get("/{prescription_id}")
def get(prescription_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    """Return one prescription the caller may see (FR-D3)."""
    return ok(service.to_response_dict(db, service.get_prescription_for_user(db, prescription_id, user)))


@router.patch("/{prescription_id}/issue")
def issue(prescription_id: int, db: Session = Depends(get_db), user: User = Doctor) -> dict:
    """Publish a draft to the patient and the pharmacy (FR-D1)."""
    return ok(service.to_response_dict(db, service.issue_prescription(db, prescription_id, user)))


@router.patch("/{prescription_id}/dispense")
def dispense(prescription_id: int, payload: DispenseRequest, db: Session = Depends(get_db),
             user: User = Pharmacist) -> dict:
    """Record that the medicines were dispensed."""
    return ok(service.to_response_dict(db, service.dispense_prescription(db, prescription_id, user, payload.note)))
