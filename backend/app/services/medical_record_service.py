"""Business rules for Electronic Health Records (FR-D2 to FR-D5).

Two rules dominate this module:

* A patient reads their own record and nothing else (FR-D3).
* A doctor reads a patient's record only where a treatment relationship exists
  (FR-D4). A doctor account alone is never sufficient.

Every read and write of clinical data is written to the audit trail (NFR-B).
"""

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.constants import PATIENT_ROLES, AppointmentStatus, UserRole
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.models.appointment import Appointment
from app.models.medical_record import MedicalRecord, MedicalRecordVersion
from app.models.user import User
from app.schemas.medical_record import CreateRecordRequest, UpdateRecordRequest

#: Fields a doctor may edit after a record is created.
EDITABLE_FIELDS = ("title", "diagnosis", "symptoms", "examination", "treatment", "follow_up", "notes")


def doctor_has_treatment_relationship(db: Session, doctor_id: int, patient_id: int) -> bool:
    """Report whether a doctor is authorised to open a patient's record (FR-D4).

    Authorisation comes from one of two facts:

    * an appointment links the doctor to the patient, or
    * the doctor already authored a record for the patient.

    Args:
        db: The active database session.
        doctor_id: The doctor requesting access.
        patient_id: The patient whose record is requested.

    Returns:
        bool: ``True`` when a treatment relationship exists.
    """
    has_appointment = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.patient_id == patient_id,
            Appointment.status != AppointmentStatus.CANCELLED.value,
        )
        .first()
        is not None
    )
    if has_appointment:
        return True

    return (
        db.query(MedicalRecord)
        .filter(MedicalRecord.doctor_id == doctor_id, MedicalRecord.patient_id == patient_id)
        .first()
        is not None
    )


def ensure_can_read_patient_records(db: Session, viewer: User, patient_id: int) -> None:
    """Authorise a read of a patient's health record (FR-D3, FR-D4).

    Args:
        db: The active database session.
        viewer: The signed in user.
        patient_id: The patient whose record is requested.

    Raises:
        PermissionDeniedError: When the viewer has no right to the record.
    """
    if viewer.id == patient_id:
        return

    if viewer.role == UserRole.DOCTOR.value:
        if doctor_has_treatment_relationship(db, viewer.id, patient_id):
            return
        raise PermissionDeniedError(
            "You may only open records for patients you have treated or are scheduled to treat."
        )

    # Administrators oversee the system but do not read clinical content.
    raise PermissionDeniedError("Your role does not permit access to medical records.")


def _validate_patient(db: Session, patient_id: int) -> User:
    """Load a user and confirm they can hold a health record.

    Args:
        db: The active database session.
        patient_id: The candidate patient identifier.

    Returns:
        User: The patient account.

    Raises:
        NotFoundError: When the account is missing.
        ValidationError: When the account is not a patient role.
    """
    patient = db.get(User, patient_id)
    if patient is None:
        raise NotFoundError("That patient was not found.")
    if UserRole(patient.role) not in PATIENT_ROLES:
        raise ValidationError("Medical records can only be created for students, faculty or staff.")
    return patient


def create_record(db: Session, doctor: User, payload: CreateRecordRequest) -> MedicalRecord:
    """Add a clinical entry to a patient's health record (FR-D2, FR-D4).

    Args:
        db: The active database session.
        doctor: The signed in doctor authoring the entry.
        payload: The validated record request.

    Returns:
        MedicalRecord: The stored entry.

    Raises:
        PermissionDeniedError: When no treatment relationship exists.
        ValidationError: When the visit date is in the future or the linked
            appointment belongs to a different patient or doctor.
    """
    if doctor.role != UserRole.DOCTOR.value:
        raise PermissionDeniedError("Only a doctor can add a clinical record.")

    _validate_patient(db, payload.patient_id)

    if not doctor_has_treatment_relationship(db, doctor.id, payload.patient_id):
        raise PermissionDeniedError(
            "You may only add records for patients you have treated or are scheduled to treat."
        )

    if payload.visit_date > date.today():
        raise ValidationError("The visit date cannot be in the future.")

    if payload.appointment_id is not None:
        appointment = db.get(Appointment, payload.appointment_id)
        if appointment is None:
            raise ValidationError("The linked appointment was not found.")
        if appointment.patient_id != payload.patient_id or appointment.doctor_id != doctor.id:
            raise ValidationError("The linked appointment does not match this patient and doctor.")

    record = MedicalRecord(
        patient_id=payload.patient_id,
        doctor_id=doctor.id,
        appointment_id=payload.appointment_id,
        record_type=payload.record_type.value,
        visit_date=payload.visit_date,
        title=payload.title.strip(),
        symptoms=payload.symptoms,
        examination=payload.examination,
        diagnosis=payload.diagnosis.strip(),
        treatment=payload.treatment,
        follow_up=payload.follow_up,
        notes=payload.notes,
        is_confidential=payload.is_confidential,
        version=1,
    )
    db.add(record)
    db.flush()

    record_audit(
        db,
        actor_id=doctor.id,
        action="record.create",
        entity_type="medical_record",
        entity_id=record.id,
        summary=f"Created a {payload.record_type.value} entry for patient {payload.patient_id}.",
    )
    db.commit()
    db.refresh(record)
    return record


def get_record(db: Session, record_id: int, viewer: User) -> MedicalRecord:
    """Load one record the viewer is allowed to read, and log the access.

    Args:
        db: The active database session.
        record_id: The record identifier.
        viewer: The signed in user.

    Returns:
        MedicalRecord: The requested record.

    Raises:
        NotFoundError: When the record does not exist.
        PermissionDeniedError: When the viewer has no right to the record.
    """
    record = db.get(MedicalRecord, record_id)
    if record is None:
        raise NotFoundError("That medical record was not found.")

    ensure_can_read_patient_records(db, viewer, record.patient_id)

    record_audit(
        db,
        actor_id=viewer.id,
        action="record.view",
        entity_type="medical_record",
        entity_id=record.id,
        summary="Opened a medical record.",
    )
    db.commit()
    return record


def list_patient_records(
    db: Session, viewer: User, patient_id: int, record_type: str | None = None
) -> list[MedicalRecord]:
    """List a patient's clinical entries, newest visit first (FR-D2, FR-D3).

    Args:
        db: The active database session.
        viewer: The signed in user.
        patient_id: The patient whose timeline is requested.
        record_type: Optional record type filter.

    Returns:
        list[MedicalRecord]: The patient's entries.
    """
    ensure_can_read_patient_records(db, viewer, patient_id)

    query = db.query(MedicalRecord).filter(MedicalRecord.patient_id == patient_id)
    if record_type:
        query = query.filter(MedicalRecord.record_type == record_type)

    records = query.order_by(MedicalRecord.visit_date.desc(), MedicalRecord.id.desc()).all()

    record_audit(
        db,
        actor_id=viewer.id,
        action="record.list",
        entity_type="medical_record",
        entity_id=patient_id,
        summary=f"Listed {len(records)} entries for patient {patient_id}.",
    )
    db.commit()
    return records


def update_record(
    db: Session, record_id: int, doctor: User, payload: UpdateRecordRequest
) -> MedicalRecord:
    """Edit a record and snapshot the previous state (FR-D5).

    Only the authoring doctor may edit an entry, which keeps clinical
    accountability with the person who wrote it.

    Args:
        db: The active database session.
        record_id: The record to edit.
        doctor: The signed in doctor.
        payload: The fields to change.

    Returns:
        MedicalRecord: The updated record with an incremented version.

    Raises:
        PermissionDeniedError: When the doctor did not author the record.
        ValidationError: When the request contains no changes.
    """
    record = db.get(MedicalRecord, record_id)
    if record is None:
        raise NotFoundError("That medical record was not found.")

    if record.doctor_id != doctor.id:
        raise PermissionDeniedError("Only the doctor who authored this record can edit it.")

    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    change_note = changes.pop("change_note", None)
    applied = {field: value for field, value in changes.items() if field in EDITABLE_FIELDS}

    if not applied:
        raise ValidationError("Provide at least one field to update.")

    # Snapshot the current state before overwriting it (FR-D5).
    db.add(
        MedicalRecordVersion(
            record_id=record.id,
            version_number=record.version,
            title=record.title,
            symptoms=record.symptoms,
            examination=record.examination,
            diagnosis=record.diagnosis,
            treatment=record.treatment,
            follow_up=record.follow_up,
            notes=record.notes,
            edited_by=doctor.id,
            change_note=change_note,
        )
    )

    for field, value in applied.items():
        setattr(record, field, value)
    record.version += 1

    record_audit(
        db,
        actor_id=doctor.id,
        action="record.update",
        entity_type="medical_record",
        entity_id=record.id,
        summary=f"Edited fields: {', '.join(sorted(applied))}. New version {record.version}.",
    )
    db.commit()
    db.refresh(record)
    return record


def list_record_versions(db: Session, record_id: int, viewer: User) -> list[MedicalRecordVersion]:
    """List the historical snapshots of a record (FR-D5).

    Args:
        db: The active database session.
        record_id: The record whose history is requested.
        viewer: The signed in user.

    Returns:
        list[MedicalRecordVersion]: Snapshots, newest version first.
    """
    record = db.get(MedicalRecord, record_id)
    if record is None:
        raise NotFoundError("That medical record was not found.")

    ensure_can_read_patient_records(db, viewer, record.patient_id)

    return (
        db.query(MedicalRecordVersion)
        .filter(MedicalRecordVersion.record_id == record_id)
        .order_by(MedicalRecordVersion.version_number.desc())
        .all()
    )


def list_authorised_patients(db: Session, doctor: User) -> list[dict]:
    """List the patients the signed in doctor may open (FR-D4).

    Args:
        db: The active database session.
        doctor: The signed in doctor.

    Returns:
        list[dict]: One entry per authorised patient with record counts.
    """
    if doctor.role != UserRole.DOCTOR.value:
        raise PermissionDeniedError("Only a doctor can view the patient list.")

    from_appointments = {
        row.patient_id
        for row in db.query(Appointment.patient_id)
        .filter(
            Appointment.doctor_id == doctor.id,
            Appointment.status != AppointmentStatus.CANCELLED.value,
        )
        .distinct()
        .all()
    }
    from_records = {
        row.patient_id
        for row in db.query(MedicalRecord.patient_id)
        .filter(MedicalRecord.doctor_id == doctor.id)
        .distinct()
        .all()
    }

    patients = []
    for patient_id in sorted(from_appointments | from_records):
        patient = db.get(User, patient_id)
        if patient is None:
            continue

        stats = (
            db.query(func.count(MedicalRecord.id), func.max(MedicalRecord.visit_date))
            .filter(MedicalRecord.patient_id == patient_id)
            .one()
        )
        patients.append(
            {
                "patient_id": patient.id,
                "full_name": patient.full_name,
                "university_id": patient.university_id,
                "department": patient.department,
                "record_count": stats[0] or 0,
                "last_visit": stats[1],
            }
        )
    return patients


def to_detail_dict(db: Session, record: MedicalRecord) -> dict:
    """Expand a record with the display names the UI needs.

    Args:
        db: The active database session.
        record: The record to expand.

    Returns:
        dict: Record fields plus doctor and patient names.
    """
    doctor = db.get(User, record.doctor_id)
    patient = db.get(User, record.patient_id)

    return {
        "id": record.id,
        "patient_id": record.patient_id,
        "doctor_id": record.doctor_id,
        "appointment_id": record.appointment_id,
        "record_type": record.record_type,
        "visit_date": record.visit_date,
        "title": record.title,
        "symptoms": record.symptoms,
        "examination": record.examination,
        "diagnosis": record.diagnosis,
        "treatment": record.treatment,
        "follow_up": record.follow_up,
        "notes": record.notes,
        "is_confidential": record.is_confidential,
        "version": record.version,
        "doctor_name": doctor.full_name if doctor else None,
        "patient_name": patient.full_name if patient else None,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }
