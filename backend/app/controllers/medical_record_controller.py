"""HTTP controller for Electronic Health Records (FR-D2 to FR-D5)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.constants import UserRole
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.responses import success_response as ok
from app.models.user import User
from app.schemas.medical_record import CreateRecordRequest, UpdateRecordRequest
from app.services import medical_record_service as service

router = APIRouter(prefix="/medical-records", tags=["Electronic Health Records"])
Patient = Depends(require_roles(UserRole.STUDENT, UserRole.FACULTY))
Doctor = Depends(require_roles(UserRole.DOCTOR))


@router.get("/my-records")
def my_records(db: Session = Depends(get_db), user: User = Patient) -> dict:
    """Return the patient's own timeline (FR-D3)."""
    return ok([service.to_dict(db, r) for r in service.timeline(db, user, user.id)])


@router.get("/patients")
def caseload(db: Session = Depends(get_db), user: User = Doctor) -> dict:
    """List the patients the doctor may open (FR-D4)."""
    return ok(service.caseload(db, user))


@router.get("/patients/{patient_id}")
def patient_timeline(patient_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    """Return one patient's timeline to the patient or a treating doctor (FR-D3, FR-D4)."""
    return ok([service.to_dict(db, r) for r in service.timeline(db, user, patient_id)])


@router.post("", status_code=status.HTTP_201_CREATED)
def create(payload: CreateRecordRequest, db: Session = Depends(get_db), user: User = Doctor) -> dict:
    """Add a clinical entry (FR-D2)."""
    return ok(service.to_dict(db, service.create(db, user, payload)))


@router.get("/{record_id}")
def get(record_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    """Return one entry in full (FR-D3, FR-D4)."""
    return ok(service.to_dict(db, service.get(db, record_id, user)))


@router.patch("/{record_id}")
def update(record_id: int, payload: UpdateRecordRequest, db: Session = Depends(get_db), user: User = Doctor) -> dict:
    """Edit an entry, keeping the previous version (FR-D5)."""
    return ok(service.to_dict(db, service.update(db, record_id, user, payload)))


@router.get("/{record_id}/versions")
def versions(record_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    """Return the edit history of an entry (FR-D5)."""
    rows = service.versions(db, record_id, user)
    return ok([{"version_number": v.version_number, "snapshot": v.snapshot, "change_note": v.change_note,
                "edited_by": v.edited_by, "created_at": v.created_at} for v in rows])
