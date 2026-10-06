"""Business rules for Electronic Health Records (FR-D2 to FR-D5)."""

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.constants import PATIENT_ROLES, AppointmentStatus, UserRole
from app.core.errors import PermissionDeniedError, ValidationError
from app.core.utils import get_or_404
from app.models.appointment import Appointment
from app.models.medical_record import MedicalRecord, MedicalRecordVersion
from app.models.user import User
from app.schemas.medical_record import CreateRecordRequest, UpdateRecordRequest

FIELDS = ("title", "symptoms", "examination", "diagnosis", "treatment", "follow_up", "notes")


def has_relationship(db: Session, doctor_id: int, patient_id: int) -> bool:
    """FR-D4: a doctor is authorised through a live appointment or an entry they wrote."""
    booked = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id, Appointment.patient_id == patient_id,
        Appointment.status != AppointmentStatus.CANCELLED.value,
    ).first()
    authored = db.query(MedicalRecord).filter_by(doctor_id=doctor_id, patient_id=patient_id).first()
    return booked is not None or authored is not None


def _authorise(db: Session, viewer: User, patient_id: int) -> None:
    """Allow the patient or a treating doctor. Administrators never read clinical content."""
    if viewer.id == patient_id:
        return
    if viewer.role == UserRole.DOCTOR.value and has_relationship(db, viewer.id, patient_id):
        return
    raise PermissionDeniedError("You do not have access to this medical record.")


def create(db: Session, doctor: User, payload: CreateRecordRequest) -> MedicalRecord:
    """Add a clinical entry for a patient the doctor treats (FR-D2, FR-D4)."""
    patient = get_or_404(db, User, payload.patient_id, "That patient was not found.")
    if UserRole(patient.role) not in PATIENT_ROLES:
        raise ValidationError("Records can only be created for students, faculty or staff.")
    if not has_relationship(db, doctor.id, patient.id):
        raise PermissionDeniedError("You may only add records for patients you treat.")
    if payload.visit_date > date.today():
        raise ValidationError("The visit date cannot be in the future.")
    record = MedicalRecord(doctor_id=doctor.id, **payload.model_dump())
    db.add(record)
    db.flush()
    record_audit(db, actor_id=doctor.id, action="record.create", entity_type="medical_record", entity_id=record.id)
    db.commit()
    return record


def get(db: Session, record_id: int, viewer: User) -> MedicalRecord:
    """Open one entry and write the access to the audit trail (FR-D3, NFR-B)."""
    record = get_or_404(db, MedicalRecord, record_id, "That medical record was not found.")
    _authorise(db, viewer, record.patient_id)
    record_audit(db, actor_id=viewer.id, action="record.view", entity_type="medical_record", entity_id=record.id)
    db.commit()
    return record


def timeline(db: Session, viewer: User, patient_id: int) -> list[MedicalRecord]:
    """List a patient's entries, newest visit first (FR-D2, FR-D3)."""
    _authorise(db, viewer, patient_id)
    return db.query(MedicalRecord).filter_by(patient_id=patient_id).order_by(
        MedicalRecord.visit_date.desc(), MedicalRecord.id.desc()).all()


def update(db: Session, record_id: int, doctor: User, payload: UpdateRecordRequest) -> MedicalRecord:
    """Edit an entry after snapshotting its previous state (FR-D5)."""
    record = get_or_404(db, MedicalRecord, record_id, "That medical record was not found.")
    if record.doctor_id != doctor.id:
        raise PermissionDeniedError("Only the doctor who wrote this entry can edit it.")
    changes = payload.model_dump(exclude_none=True)
    note = changes.pop("change_note", None)
    if not changes:
        raise ValidationError("Provide at least one field to update.")
    snapshot = {field: getattr(record, field) for field in FIELDS}
    db.add(MedicalRecordVersion(record_id=record.id, version_number=record.version, snapshot=snapshot,
                                edited_by=doctor.id, change_note=note))
    for field, value in changes.items():
        setattr(record, field, value)
    record.version += 1
    record_audit(db, actor_id=doctor.id, action="record.update", entity_type="medical_record", entity_id=record.id)
    db.commit()
    return record


def versions(db: Session, record_id: int, viewer: User) -> list[MedicalRecordVersion]:
    """List the superseded states of an entry, newest first (FR-D5)."""
    record = get_or_404(db, MedicalRecord, record_id, "That medical record was not found.")
    _authorise(db, viewer, record.patient_id)
    return db.query(MedicalRecordVersion).filter_by(record_id=record_id).order_by(
        MedicalRecordVersion.version_number.desc()).all()


def caseload(db: Session, doctor: User) -> list[dict]:
    """List the patients this doctor is authorised to open (FR-D4)."""
    booked = db.query(Appointment.patient_id).filter(
        Appointment.doctor_id == doctor.id, Appointment.status != AppointmentStatus.CANCELLED.value)
    written = db.query(MedicalRecord.patient_id).filter(MedicalRecord.doctor_id == doctor.id)
    ids = {row[0] for row in booked} | {row[0] for row in written}
    return [
        {"patient_id": u.id, "full_name": u.full_name, "university_id": u.university_id,
         "record_count": db.query(func.count(MedicalRecord.id)).filter(MedicalRecord.patient_id == u.id).scalar()}
        for u in db.query(User).filter(User.id.in_(ids)).order_by(User.full_name)
    ]


def to_dict(db: Session, record: MedicalRecord) -> dict:
    """Expand an entry with the author's name."""
    fields = ("id", "patient_id", "doctor_id", "appointment_id", "record_type", "visit_date", *FIELDS, "version")
    return {f: getattr(record, f) for f in fields} | {"doctor_name": db.get(User, record.doctor_id).full_name}
