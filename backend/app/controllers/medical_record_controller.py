"""HTTP controller for Electronic Health Records (FR-D2 to FR-D5)."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.constants import UserRole
from app.core.database import get_db
from app.core.deps import get_current_user, require_roles
from app.core.responses import success_response
from app.models.user import User
from app.schemas.medical_record import CreateRecordRequest, UpdateRecordRequest
from app.services import medical_record_service

router = APIRouter(prefix="/medical-records", tags=["Electronic Health Records"])


@router.get("/my-records")
def list_own_records(
    record_type: str | None = Query(default=None, alias="type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.STUDENT, UserRole.FACULTY)),
) -> dict:
    """Return the signed in patient's own health record timeline (FR-D3)."""
    records = medical_record_service.list_patient_records(
        db, current_user, current_user.id, record_type
    )
    return success_response(
        [medical_record_service.to_detail_dict(db, record) for record in records]
    )


@router.get("/patients")
def list_authorised_patients(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR)),
) -> dict:
    """List the patients this doctor is authorised to open (FR-D4)."""
    return success_response(medical_record_service.list_authorised_patients(db, current_user))


@router.get("/patients/{patient_id}")
def list_patient_records(
    patient_id: int,
    record_type: str | None = Query(default=None, alias="type"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return one patient's health record timeline (FR-D3, FR-D4)."""
    records = medical_record_service.list_patient_records(db, current_user, patient_id, record_type)
    return success_response(
        [medical_record_service.to_detail_dict(db, record) for record in records]
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_record(
    payload: CreateRecordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR)),
) -> dict:
    """Add a clinical entry to a patient's health record (FR-D2, FR-D4)."""
    record = medical_record_service.create_record(db, current_user, payload)
    return success_response(medical_record_service.to_detail_dict(db, record))


@router.get("/{record_id}")
def get_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return one clinical entry in full (FR-D3, FR-D4)."""
    record = medical_record_service.get_record(db, record_id, current_user)
    return success_response(medical_record_service.to_detail_dict(db, record))


@router.patch("/{record_id}")
def update_record(
    record_id: int,
    payload: UpdateRecordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.DOCTOR)),
) -> dict:
    """Edit a clinical entry, snapshotting the previous version (FR-D5)."""
    record = medical_record_service.update_record(db, record_id, current_user, payload)
    return success_response(medical_record_service.to_detail_dict(db, record))


@router.get("/{record_id}/versions")
def list_record_versions(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Return the edit history of a clinical entry (FR-D5)."""
    versions = medical_record_service.list_record_versions(db, record_id, current_user)
    editors = {}
    payload = []
    for version in versions:
        if version.edited_by not in editors:
            editor = db.get(User, version.edited_by)
            editors[version.edited_by] = editor.full_name if editor else None
        payload.append(
            {
                "id": version.id,
                "record_id": version.record_id,
                "version_number": version.version_number,
                "title": version.title,
                "diagnosis": version.diagnosis,
                "symptoms": version.symptoms,
                "treatment": version.treatment,
                "change_note": version.change_note,
                "edited_by": version.edited_by,
                "editor_name": editors[version.edited_by],
                "created_at": version.created_at,
            }
        )
    return success_response(payload)
