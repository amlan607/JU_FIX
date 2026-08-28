"""Business rules for digital prescription management (FR-D1, FR-D3, FR-D4).

A prescription moves through a deliberate lifecycle:

``draft`` -> ``issued`` -> ``dispensed``

A draft is private to the prescribing doctor and can still be edited. Issuing
publishes it to the patient and the pharmacy and freezes the medicine list, so a
dispensed prescription always matches what the patient was shown.
"""

from datetime import date, datetime, timedelta, timezone
from secrets import randbelow

from sqlalchemy.orm import Session

from app.core.audit import record_audit
from app.core.constants import PATIENT_ROLES, AppointmentStatus, PrescriptionStatus, UserRole
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.models.appointment import Appointment
from app.models.medical_record import MedicalRecord
from app.models.prescription import Prescription, PrescriptionItem
from app.models.user import User
from app.schemas.prescription import CreatePrescriptionRequest, UpdatePrescriptionRequest

#: Statuses a pharmacist is allowed to see in the dispensing queue.
PHARMACY_VISIBLE_STATUSES = (PrescriptionStatus.ISSUED.value, PrescriptionStatus.DISPENSED.value)


def _utc_now() -> datetime:
    """Return the current timezone aware UTC time."""
    return datetime.now(timezone.utc)


def generate_reference_code(db: Session) -> str:
    """Build a unique human readable prescription reference.

    The format is ``RX-YYYYMMDD-NNNNNN``, which is short enough to read out at
    the pharmacy counter while staying unique per day.

    Args:
        db: The active database session.

    Returns:
        str: A reference code that is not yet used.
    """
    while True:
        candidate = f"RX-{date.today():%Y%m%d}-{randbelow(1_000_000):06d}"
        exists = db.query(Prescription).filter(Prescription.reference_code == candidate).first()
        if exists is None:
            return candidate


def _has_treatment_relationship(db: Session, doctor_id: int, patient_id: int) -> bool:
    """Report whether a doctor may prescribe for a patient (FR-D4).

    Args:
        db: The active database session.
        doctor_id: The prescribing doctor.
        patient_id: The patient receiving the prescription.

    Returns:
        bool: ``True`` when an appointment or an authored record links them.
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


def _validate_patient(db: Session, patient_id: int) -> User:
    """Load a patient account and confirm it can receive a prescription.

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
        raise ValidationError("Prescriptions can only be written for students, faculty or staff.")
    return patient


def _replace_items(db: Session, prescription: Prescription, items) -> None:
    """Replace every medicine line on a prescription.

    Args:
        db: The active database session.
        prescription: The prescription being edited.
        items: The new medicine lines.
    """
    for existing in list(prescription.items):
        db.delete(existing)
    prescription.items.clear()

    for item in items:
        prescription.items.append(
            PrescriptionItem(
                medicine_name=item.medicine_name.strip(),
                dosage=item.dosage.strip(),
                frequency=item.frequency.strip(),
                duration=item.duration.strip(),
                instructions=(item.instructions or "").strip() or None,
            )
        )


def create_prescription(
    db: Session, doctor: User, payload: CreatePrescriptionRequest
) -> Prescription:
    """Create a prescription draft (FR-D1).

    Args:
        db: The active database session.
        doctor: The signed in doctor.
        payload: The validated prescription request.

    Returns:
        Prescription: The stored draft.

    Raises:
        PermissionDeniedError: When the caller is not the patient's doctor.
        ValidationError: When a linked appointment or record does not match.
    """
    if doctor.role != UserRole.DOCTOR.value:
        raise PermissionDeniedError("Only a doctor can write a prescription.")

    _validate_patient(db, payload.patient_id)

    if not _has_treatment_relationship(db, doctor.id, payload.patient_id):
        raise PermissionDeniedError(
            "You may only prescribe for patients you have treated or are scheduled to treat."
        )

    if payload.appointment_id is not None:
        appointment = db.get(Appointment, payload.appointment_id)
        if appointment is None:
            raise ValidationError("The linked appointment was not found.")
        if appointment.patient_id != payload.patient_id or appointment.doctor_id != doctor.id:
            raise ValidationError("The linked appointment does not match this patient and doctor.")

    if payload.record_id is not None:
        record = db.get(MedicalRecord, payload.record_id)
        if record is None:
            raise ValidationError("The linked medical record was not found.")
        if record.patient_id != payload.patient_id:
            raise ValidationError("The linked medical record belongs to a different patient.")

    prescription = Prescription(
        reference_code=generate_reference_code(db),
        patient_id=payload.patient_id,
        doctor_id=doctor.id,
        appointment_id=payload.appointment_id,
        record_id=payload.record_id,
        diagnosis=payload.diagnosis.strip(),
        advice=(payload.advice or "").strip() or None,
        status=PrescriptionStatus.DRAFT.value,
        valid_until=date.today() + timedelta(days=payload.valid_days),
    )
    _replace_items(db, prescription, payload.items)
    db.add(prescription)
    db.flush()

    record_audit(
        db,
        actor_id=doctor.id,
        action="prescription.create",
        entity_type="prescription",
        entity_id=prescription.id,
        summary=f"Created draft {prescription.reference_code} with {len(payload.items)} item(s).",
    )
    db.commit()
    db.refresh(prescription)
    return prescription


def get_prescription_for_user(db: Session, prescription_id: int, viewer: User) -> Prescription:
    """Load a prescription the viewer is allowed to see (FR-D3, FR-D4).

    Args:
        db: The active database session.
        prescription_id: The prescription identifier.
        viewer: The signed in user.

    Returns:
        Prescription: The requested prescription.

    Raises:
        NotFoundError: When the prescription does not exist.
        PermissionDeniedError: When the viewer has no right to it.
    """
    prescription = db.get(Prescription, prescription_id)
    if prescription is None:
        raise NotFoundError("That prescription was not found.")

    is_patient = prescription.patient_id == viewer.id
    is_author = prescription.doctor_id == viewer.id
    is_pharmacist = viewer.role == UserRole.PHARMACIST.value

    # A patient never sees a draft; it is not a prescription until it is issued.
    if is_patient and prescription.status == PrescriptionStatus.DRAFT.value:
        raise NotFoundError("That prescription was not found.")

    # A pharmacist works the dispensing queue and sees issued prescriptions only.
    if is_pharmacist and prescription.status not in PHARMACY_VISIBLE_STATUSES:
        raise PermissionDeniedError("Only issued prescriptions are visible at the pharmacy.")

    if not (is_patient or is_author or is_pharmacist):
        raise PermissionDeniedError("You do not have access to this prescription.")

    return prescription


def update_prescription(
    db: Session, prescription_id: int, doctor: User, payload: UpdatePrescriptionRequest
) -> Prescription:
    """Edit a draft prescription before it is issued.

    Args:
        db: The active database session.
        prescription_id: The draft to edit.
        doctor: The signed in doctor.
        payload: The fields to change.

    Returns:
        Prescription: The updated draft.

    Raises:
        PermissionDeniedError: When the doctor did not write the draft.
        ValidationError: When the prescription is no longer a draft or nothing changed.
    """
    prescription = db.get(Prescription, prescription_id)
    if prescription is None:
        raise NotFoundError("That prescription was not found.")

    if prescription.doctor_id != doctor.id:
        raise PermissionDeniedError("Only the prescribing doctor can edit this prescription.")

    if prescription.status != PrescriptionStatus.DRAFT.value:
        raise ValidationError("An issued prescription cannot be edited. Cancel and write a new one.")

    changed = False
    if payload.diagnosis is not None:
        prescription.diagnosis = payload.diagnosis.strip()
        changed = True
    if payload.advice is not None:
        prescription.advice = payload.advice.strip() or None
        changed = True
    if payload.items is not None:
        _replace_items(db, prescription, payload.items)
        changed = True

    if not changed:
        raise ValidationError("Provide at least one field to update.")

    record_audit(
        db,
        actor_id=doctor.id,
        action="prescription.update",
        entity_type="prescription",
        entity_id=prescription.id,
        summary=f"Edited draft {prescription.reference_code}.",
    )
    db.commit()
    db.refresh(prescription)
    return prescription


def issue_prescription(db: Session, prescription_id: int, doctor: User) -> Prescription:
    """Publish a draft to the patient and the pharmacy (FR-D1, FR-D3).

    Args:
        db: The active database session.
        prescription_id: The draft to issue.
        doctor: The signed in doctor.

    Returns:
        Prescription: The issued prescription.

    Raises:
        PermissionDeniedError: When the doctor did not write the draft.
        ValidationError: When it is not a draft or has no medicines.
    """
    prescription = db.get(Prescription, prescription_id)
    if prescription is None:
        raise NotFoundError("That prescription was not found.")

    if prescription.doctor_id != doctor.id:
        raise PermissionDeniedError("Only the prescribing doctor can issue this prescription.")

    if prescription.status != PrescriptionStatus.DRAFT.value:
        raise ValidationError("This prescription has already been issued.")

    if not prescription.items:
        raise ValidationError("Add at least one medicine before issuing the prescription.")

    prescription.status = PrescriptionStatus.ISSUED.value
    prescription.issued_at = _utc_now()

    record_audit(
        db,
        actor_id=doctor.id,
        action="prescription.issue",
        entity_type="prescription",
        entity_id=prescription.id,
        summary=f"Issued {prescription.reference_code} to patient {prescription.patient_id}.",
    )
    db.commit()
    db.refresh(prescription)
    return prescription


def cancel_prescription(db: Session, prescription_id: int, doctor: User) -> Prescription:
    """Cancel a prescription that has not been dispensed.

    Args:
        db: The active database session.
        prescription_id: The prescription to cancel.
        doctor: The signed in doctor.

    Returns:
        Prescription: The cancelled prescription.

    Raises:
        ValidationError: When the medicines have already been dispensed.
    """
    prescription = db.get(Prescription, prescription_id)
    if prescription is None:
        raise NotFoundError("That prescription was not found.")

    if prescription.doctor_id != doctor.id:
        raise PermissionDeniedError("Only the prescribing doctor can cancel this prescription.")

    if prescription.status == PrescriptionStatus.DISPENSED.value:
        raise ValidationError("A dispensed prescription cannot be cancelled.")

    prescription.status = PrescriptionStatus.CANCELLED.value

    record_audit(
        db,
        actor_id=doctor.id,
        action="prescription.cancel",
        entity_type="prescription",
        entity_id=prescription.id,
        summary=f"Cancelled {prescription.reference_code}.",
    )
    db.commit()
    db.refresh(prescription)
    return prescription


def dispense_prescription(
    db: Session, prescription_id: int, pharmacist: User, note: str | None = None
) -> Prescription:
    """Record that the pharmacy has dispensed the medicines.

    Args:
        db: The active database session.
        prescription_id: The prescription being dispensed.
        pharmacist: The signed in pharmacist.
        note: Optional counter note, for example a substitution.

    Returns:
        Prescription: The dispensed prescription.

    Raises:
        PermissionDeniedError: When the caller is not a pharmacist.
        ValidationError: When the prescription is not issued or has expired.
    """
    if pharmacist.role != UserRole.PHARMACIST.value:
        raise PermissionDeniedError("Only a pharmacist can dispense a prescription.")

    prescription = db.get(Prescription, prescription_id)
    if prescription is None:
        raise NotFoundError("That prescription was not found.")

    if prescription.status == PrescriptionStatus.DISPENSED.value:
        raise ValidationError("This prescription has already been dispensed.")

    if prescription.status != PrescriptionStatus.ISSUED.value:
        raise ValidationError("Only an issued prescription can be dispensed.")

    if prescription.valid_until is not None and prescription.valid_until < date.today():
        raise ValidationError("This prescription has expired. Ask the patient to see the doctor.")

    prescription.status = PrescriptionStatus.DISPENSED.value
    prescription.dispensed_by = pharmacist.id
    prescription.dispensed_at = _utc_now()
    prescription.pharmacist_note = (note or "").strip() or None

    record_audit(
        db,
        actor_id=pharmacist.id,
        action="prescription.dispense",
        entity_type="prescription",
        entity_id=prescription.id,
        summary=f"Dispensed {prescription.reference_code}.",
    )
    db.commit()
    db.refresh(prescription)
    return prescription


def find_by_reference(db: Session, reference_code: str, pharmacist: User) -> Prescription:
    """Look up an issued prescription by the code printed on it.

    Args:
        db: The active database session.
        reference_code: The reference code presented at the counter.
        pharmacist: The signed in pharmacist.

    Returns:
        Prescription: The matching prescription.

    Raises:
        PermissionDeniedError: When the caller is not a pharmacist.
        NotFoundError: When no issued prescription carries that code.
    """
    if pharmacist.role != UserRole.PHARMACIST.value:
        raise PermissionDeniedError("Only a pharmacist can search the dispensing queue.")

    prescription = (
        db.query(Prescription)
        .filter(
            Prescription.reference_code == reference_code.strip().upper(),
            Prescription.status.in_(PHARMACY_VISIBLE_STATUSES),
        )
        .first()
    )
    if prescription is None:
        raise NotFoundError("No issued prescription matches that reference code.")
    return prescription


def list_for_patient(db: Session, patient: User) -> list[Prescription]:
    """List a patient's issued prescriptions, newest first (FR-D3).

    Args:
        db: The active database session.
        patient: The signed in patient.

    Returns:
        list[Prescription]: Prescriptions visible to the patient.
    """
    return (
        db.query(Prescription)
        .filter(
            Prescription.patient_id == patient.id,
            Prescription.status != PrescriptionStatus.DRAFT.value,
        )
        .order_by(Prescription.id.desc())
        .all()
    )


def list_for_doctor(db: Session, doctor: User, status: str | None = None) -> list[Prescription]:
    """List the prescriptions written by a doctor.

    Args:
        db: The active database session.
        doctor: The signed in doctor.
        status: Optional status filter.

    Returns:
        list[Prescription]: The doctor's prescriptions, newest first.
    """
    query = db.query(Prescription).filter(Prescription.doctor_id == doctor.id)
    if status:
        query = query.filter(Prescription.status == status)
    return query.order_by(Prescription.id.desc()).all()


def list_pharmacy_queue(db: Session, pharmacist: User, status: str | None = None) -> list[Prescription]:
    """List prescriptions waiting at the pharmacy counter.

    Args:
        db: The active database session.
        pharmacist: The signed in pharmacist.
        status: Optional status filter within the pharmacy visible set.

    Returns:
        list[Prescription]: Issued and dispensed prescriptions, newest first.

    Raises:
        PermissionDeniedError: When the caller is not a pharmacist.
    """
    if pharmacist.role != UserRole.PHARMACIST.value:
        raise PermissionDeniedError("Only a pharmacist can view the dispensing queue.")

    query = db.query(Prescription).filter(Prescription.status.in_(PHARMACY_VISIBLE_STATUSES))
    if status:
        if status not in PHARMACY_VISIBLE_STATUSES:
            raise ValidationError("That status is not visible at the pharmacy.")
        query = query.filter(Prescription.status == status)

    return query.order_by(Prescription.issued_at.desc()).all()


def to_response_dict(db: Session, prescription: Prescription) -> dict:
    """Expand a prescription with the names the UI needs.

    Args:
        db: The active database session.
        prescription: The prescription to expand.

    Returns:
        dict: Prescription fields, medicine lines and display names.
    """
    patient = db.get(User, prescription.patient_id)
    doctor = db.get(User, prescription.doctor_id)
    dispenser = db.get(User, prescription.dispensed_by) if prescription.dispensed_by else None

    return {
        "id": prescription.id,
        "reference_code": prescription.reference_code,
        "patient_id": prescription.patient_id,
        "doctor_id": prescription.doctor_id,
        "appointment_id": prescription.appointment_id,
        "record_id": prescription.record_id,
        "diagnosis": prescription.diagnosis,
        "advice": prescription.advice,
        "status": prescription.status,
        "issued_at": prescription.issued_at,
        "valid_until": prescription.valid_until,
        "dispensed_at": prescription.dispensed_at,
        "pharmacist_note": prescription.pharmacist_note,
        "items": [
            {
                "id": item.id,
                "medicine_name": item.medicine_name,
                "dosage": item.dosage,
                "frequency": item.frequency,
                "duration": item.duration,
                "instructions": item.instructions,
            }
            for item in prescription.items
        ],
        "patient_name": patient.full_name if patient else None,
        "patient_university_id": patient.university_id if patient else None,
        "doctor_name": doctor.full_name if doctor else None,
        "dispensed_by_name": dispenser.full_name if dispenser else None,
    }
