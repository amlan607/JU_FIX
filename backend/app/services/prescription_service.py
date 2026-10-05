"""Business rules for digital prescriptions (FR-D1, FR-D3, FR-D4).

Lifecycle: draft -> issued -> dispensed. A draft is private to its doctor; issuing
publishes it to the patient and the pharmacy.
"""

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.constants import PATIENT_ROLES, AppointmentStatus, PrescriptionStatus, UserRole
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.core.utils import get_or_404, unique_code, utc_now
from app.models.appointment import Appointment
from app.models.prescription import Prescription, PrescriptionItem
from app.models.user import User
from app.schemas.prescription import CreatePrescriptionRequest

DRAFT, ISSUED, DISPENSED = (s.value for s in (PrescriptionStatus.DRAFT, PrescriptionStatus.ISSUED, PrescriptionStatus.DISPENSED))
PHARMACY_VISIBLE = (ISSUED, DISPENSED)


def create_prescription(db: Session, doctor: User, payload: CreatePrescriptionRequest) -> Prescription:
    """Create a draft for a patient the doctor treats (FR-D1, FR-D4)."""
    patient = get_or_404(db, User, payload.patient_id, "That patient was not found.")
    if UserRole(patient.role) not in PATIENT_ROLES:
        raise ValidationError("Prescriptions can only be written for students, faculty or staff.")
    if not db.query(Appointment).filter(
        Appointment.doctor_id == doctor.id, Appointment.patient_id == patient.id,
        Appointment.status != AppointmentStatus.CANCELLED.value,
    ).first():
        raise PermissionDeniedError("You may only prescribe for patients you treat.")
    prescription = Prescription(
        reference_code=unique_code(db, Prescription.reference_code, "RX", "%Y%m%d"),
        patient_id=patient.id, doctor_id=doctor.id, appointment_id=payload.appointment_id,
        record_id=payload.record_id, diagnosis=payload.diagnosis.strip(), advice=payload.advice,
        valid_until=date.today() + timedelta(days=payload.valid_days),
        items=[PrescriptionItem(**item.model_dump()) for item in payload.items],
    )
    db.add(prescription)
    db.flush()
    record_audit(db, actor_id=doctor.id, action="prescription.create", entity_type="prescription", entity_id=prescription.id)
    db.commit()
    return prescription


def issue_prescription(db: Session, prescription_id: int, doctor: User) -> Prescription:
    """Publish a draft; the medicine list is final from this point (FR-D1, FR-D3)."""
    prescription = get_or_404(db, Prescription, prescription_id, "That prescription was not found.")
    if prescription.doctor_id != doctor.id:
        raise PermissionDeniedError("Only the prescribing doctor can issue this prescription.")
    if prescription.status != DRAFT:
        raise ValidationError("This prescription has already been issued.")
    prescription.status, prescription.issued_at = ISSUED, utc_now()
    record_audit(db, actor_id=doctor.id, action="prescription.issue", entity_type="prescription", entity_id=prescription.id)
    db.commit()
    return prescription


def get_prescription_for_user(db: Session, prescription_id: int, viewer: User) -> Prescription:
    """Load a prescription the viewer may see (FR-D3, FR-D4)."""
    prescription = get_or_404(db, Prescription, prescription_id, "That prescription was not found.")
    if viewer.id == prescription.patient_id and prescription.status == DRAFT:
        raise NotFoundError("That prescription was not found.")  # a draft is not yet a prescription
    is_pharmacist = viewer.role == UserRole.PHARMACIST.value and prescription.status in PHARMACY_VISIBLE
    if viewer.id not in (prescription.patient_id, prescription.doctor_id) and not is_pharmacist:
        raise PermissionDeniedError("You do not have access to this prescription.")
    return prescription


def list_for_patient(db: Session, patient: User) -> list[Prescription]:
    """List a patient's issued prescriptions, newest first (FR-D3)."""
    return db.query(Prescription).filter(Prescription.patient_id == patient.id, Prescription.status != DRAFT).order_by(
        Prescription.id.desc()).all()


def list_for_doctor(db: Session, doctor: User) -> list[Prescription]:
    """List the prescriptions a doctor has written, newest first."""
    return db.query(Prescription).filter_by(doctor_id=doctor.id).order_by(Prescription.id.desc()).all()


def list_pharmacy_queue(db: Session, pharmacist: User, status: str | None = None) -> list[Prescription]:
    """List issued and dispensed prescriptions waiting at the counter."""
    statuses = (status,) if status in PHARMACY_VISIBLE else PHARMACY_VISIBLE
    return db.query(Prescription).filter(Prescription.status.in_(statuses)).order_by(Prescription.issued_at.desc()).all()


def dispense_prescription(db: Session, prescription_id: int, pharmacist: User, note: str | None = None) -> Prescription:
    """Record that the pharmacy handed over the medicines."""
    if pharmacist.role != UserRole.PHARMACIST.value:
        raise PermissionDeniedError("Only a pharmacist can dispense a prescription.")
    prescription = get_or_404(db, Prescription, prescription_id, "That prescription was not found.")
    if prescription.status == DISPENSED:
        raise ValidationError("This prescription has already been dispensed.")
    if prescription.status != ISSUED:
        raise ValidationError("Only an issued prescription can be dispensed.")
    if prescription.valid_until and prescription.valid_until < date.today():
        raise ValidationError("This prescription has expired. Ask the patient to see the doctor.")
    prescription.status, prescription.dispensed_by = DISPENSED, pharmacist.id
    prescription.dispensed_at, prescription.pharmacist_note = utc_now(), note
    record_audit(db, actor_id=pharmacist.id, action="prescription.dispense", entity_type="prescription", entity_id=prescription.id)
    db.commit()
    return prescription


def to_response_dict(db: Session, prescription: Prescription) -> dict:
    """Expand a prescription with its medicines and the names the screens need."""
    fields = ("id", "reference_code", "patient_id", "doctor_id", "diagnosis", "advice", "status", "issued_at",
              "valid_until", "dispensed_at", "pharmacist_note")
    items = [{c: getattr(i, c) for c in ("id", "medicine_name", "dosage", "frequency", "duration", "instructions")}
             for i in prescription.items]
    return {f: getattr(prescription, f) for f in fields} | {
        "items": items,
        "patient_name": db.get(User, prescription.patient_id).full_name,
        "doctor_name": db.get(User, prescription.doctor_id).full_name,
    }
