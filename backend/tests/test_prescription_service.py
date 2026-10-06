"""Unit tests for the digital prescription business rules (FR-D1, FR-D3)."""

from datetime import date, time, timedelta

import pytest

from app.core.constants import AppointmentStatus, PrescriptionStatus, UserRole
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.models.appointment import Appointment
from app.schemas.prescription import (
    CreatePrescriptionRequest,
    PrescriptionItemRequest,
    UpdatePrescriptionRequest,
)
from app.services import prescription_service as service
from tests.conftest import make_doctor, make_user


def link_appointment(db_session, doctor, patient) -> Appointment:
    """Create the treatment relationship required by FR-D4."""
    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=date.today(),
        start_time=time(10, 0),
        end_time=time(10, 20),
        reason="Fever and cough.",
        status=AppointmentStatus.COMPLETED.value,
    )
    db_session.add(appointment)
    db_session.commit()
    db_session.refresh(appointment)
    return appointment


def prescription_payload(patient_id: int, **overrides) -> CreatePrescriptionRequest:
    """Build a valid prescription request with one medicine."""
    data = {
        "patient_id": patient_id,
        "diagnosis": "Acute bacterial pharyngitis.",
        "items": [
            PrescriptionItemRequest(
                medicine_name="Amoxicillin",
                dosage="500mg",
                frequency="1+1+1",
                duration="7 days",
                instructions="Take after meals.",
            )
        ],
        "advice": "Drink warm fluids and rest.",
    }
    data.update(overrides)
    return CreatePrescriptionRequest(**data)


def issued_prescription(db_session, doctor, patient):
    """Create and issue a prescription, returning it."""
    link_appointment(db_session, doctor, patient)
    draft = service.create_prescription(db_session, doctor, prescription_payload(patient.id))
    return service.issue_prescription(db_session, draft.id, doctor)


@pytest.mark.unit
def test_reference_codes_are_unique(db_session):
    """Two prescriptions never share a reference code."""
    first = service.generate_reference_code(db_session)
    second = service.generate_reference_code(db_session)

    assert first.startswith("RX-")
    assert first != second


@pytest.mark.unit
def test_doctor_creates_a_draft_with_items(db_session):
    """FR-D1: a prescription carries medicines, dosage and instructions."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    link_appointment(db_session, doctor, patient)

    prescription = service.create_prescription(db_session, doctor, prescription_payload(patient.id))

    assert prescription.status == PrescriptionStatus.DRAFT.value
    assert len(prescription.items) == 1
    assert prescription.items[0].medicine_name == "Amoxicillin"


@pytest.mark.unit
def test_a_draft_sets_a_validity_window(db_session):
    """A prescription expires so an old one cannot be dispensed indefinitely."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    link_appointment(db_session, doctor, patient)

    prescription = service.create_prescription(
        db_session, doctor, prescription_payload(patient.id, valid_days=10)
    )

    assert prescription.valid_until == date.today() + timedelta(days=10)


@pytest.mark.unit
def test_a_doctor_without_a_relationship_cannot_prescribe(db_session):
    """FR-D4 governs prescribing as well as record access."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")

    with pytest.raises(PermissionDeniedError):
        service.create_prescription(db_session, doctor, prescription_payload(patient.id))


@pytest.mark.unit
def test_a_prescription_cannot_be_written_for_a_pharmacist(db_session):
    """Only patient roles receive prescriptions."""
    doctor = make_doctor(db_session)
    pharmacist = make_user(db_session, university_id="PHR-3001", role=UserRole.PHARMACIST)
    link_appointment(db_session, doctor, pharmacist)

    with pytest.raises(ValidationError, match="students, faculty"):
        service.create_prescription(db_session, doctor, prescription_payload(pharmacist.id))


@pytest.mark.unit
def test_a_prescription_requires_at_least_one_medicine():
    """An empty medicine list is rejected by the schema."""
    with pytest.raises(ValueError):
        CreatePrescriptionRequest(patient_id=1, diagnosis="Fever.", items=[])


@pytest.mark.unit
def test_a_patient_cannot_see_a_draft(db_session):
    """A draft is not a prescription until the doctor issues it."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    link_appointment(db_session, doctor, patient)
    draft = service.create_prescription(db_session, doctor, prescription_payload(patient.id))

    with pytest.raises(NotFoundError):
        service.get_prescription_for_user(db_session, draft.id, patient)


@pytest.mark.unit
def test_issuing_publishes_the_prescription_to_the_patient(db_session):
    """FR-D3: an issued prescription becomes visible to the patient."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    prescription = issued_prescription(db_session, doctor, patient)

    assert prescription.status == PrescriptionStatus.ISSUED.value
    assert prescription.issued_at is not None
    assert service.get_prescription_for_user(db_session, prescription.id, patient).id == prescription.id


@pytest.mark.unit
def test_a_prescription_cannot_be_issued_twice(db_session):
    """Issuing is a one way transition."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    prescription = issued_prescription(db_session, doctor, patient)

    with pytest.raises(ValidationError, match="already been issued"):
        service.issue_prescription(db_session, prescription.id, doctor)


@pytest.mark.unit
def test_an_issued_prescription_cannot_be_edited(db_session):
    """Freezing the medicine list keeps the patient copy and the pharmacy copy identical."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    prescription = issued_prescription(db_session, doctor, patient)

    with pytest.raises(ValidationError, match="cannot be edited"):
        service.update_prescription(
            db_session, prescription.id, doctor, UpdatePrescriptionRequest(advice="Changed advice.")
        )


@pytest.mark.unit
def test_a_draft_can_be_edited(db_session):
    """A draft is still the doctor's working copy."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    link_appointment(db_session, doctor, patient)
    draft = service.create_prescription(db_session, doctor, prescription_payload(patient.id))

    updated = service.update_prescription(
        db_session, draft.id, doctor, UpdatePrescriptionRequest(advice="Complete the full course.")
    )

    assert updated.advice == "Complete the full course."


@pytest.mark.unit
def test_editing_replaces_the_medicine_list(db_session):
    """Submitting a new item list replaces the previous one entirely."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    link_appointment(db_session, doctor, patient)
    draft = service.create_prescription(db_session, doctor, prescription_payload(patient.id))

    updated = service.update_prescription(
        db_session,
        draft.id,
        doctor,
        UpdatePrescriptionRequest(
            items=[
                PrescriptionItemRequest(
                    medicine_name="Azithromycin",
                    dosage="250mg",
                    frequency="1+0+0",
                    duration="5 days",
                )
            ]
        ),
    )

    assert len(updated.items) == 1
    assert updated.items[0].medicine_name == "Azithromycin"


@pytest.mark.unit
def test_another_doctor_cannot_edit_the_draft(db_session):
    """Only the prescribing doctor owns the draft."""
    author = make_doctor(db_session)
    colleague = make_doctor(db_session, university_id="DOC-2002")
    patient = make_user(db_session, university_id="STU-2021-364")
    link_appointment(db_session, author, patient)
    draft = service.create_prescription(db_session, author, prescription_payload(patient.id))

    with pytest.raises(PermissionDeniedError):
        service.update_prescription(
            db_session, draft.id, colleague, UpdatePrescriptionRequest(advice="Edit.")
        )


@pytest.mark.unit
def test_pharmacist_dispenses_an_issued_prescription(db_session):
    """The dispensing event records who handed over the medicines."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    pharmacist = make_user(db_session, university_id="PHR-3001", role=UserRole.PHARMACIST)
    prescription = issued_prescription(db_session, doctor, patient)

    dispensed = service.dispense_prescription(db_session, prescription.id, pharmacist, "Full course given.")

    assert dispensed.status == PrescriptionStatus.DISPENSED.value
    assert dispensed.dispensed_by == pharmacist.id
    assert dispensed.pharmacist_note == "Full course given."


@pytest.mark.unit
def test_a_prescription_cannot_be_dispensed_twice(db_session):
    """Double dispensing would hand out the medicines twice."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    pharmacist = make_user(db_session, university_id="PHR-3001", role=UserRole.PHARMACIST)
    prescription = issued_prescription(db_session, doctor, patient)
    service.dispense_prescription(db_session, prescription.id, pharmacist)

    with pytest.raises(ValidationError, match="already been dispensed"):
        service.dispense_prescription(db_session, prescription.id, pharmacist)


@pytest.mark.unit
def test_a_draft_cannot_be_dispensed(db_session):
    """The pharmacy only handles prescriptions the doctor has issued."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    pharmacist = make_user(db_session, university_id="PHR-3001", role=UserRole.PHARMACIST)
    link_appointment(db_session, doctor, patient)
    draft = service.create_prescription(db_session, doctor, prescription_payload(patient.id))

    with pytest.raises(ValidationError, match="issued prescription"):
        service.dispense_prescription(db_session, draft.id, pharmacist)


@pytest.mark.unit
def test_an_expired_prescription_cannot_be_dispensed(db_session):
    """The validity window is enforced at the counter."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    pharmacist = make_user(db_session, university_id="PHR-3001", role=UserRole.PHARMACIST)
    prescription = issued_prescription(db_session, doctor, patient)

    prescription.valid_until = date.today() - timedelta(days=1)
    db_session.commit()

    with pytest.raises(ValidationError, match="expired"):
        service.dispense_prescription(db_session, prescription.id, pharmacist)


@pytest.mark.unit
def test_a_doctor_cannot_dispense(db_session):
    """Separation of duties: prescribing and dispensing are different roles."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    prescription = issued_prescription(db_session, doctor, patient)

    with pytest.raises(PermissionDeniedError):
        service.dispense_prescription(db_session, prescription.id, doctor)


@pytest.mark.unit
def test_a_dispensed_prescription_cannot_be_cancelled(db_session):
    """Once the medicines are handed over the record is final."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    pharmacist = make_user(db_session, university_id="PHR-3001", role=UserRole.PHARMACIST)
    prescription = issued_prescription(db_session, doctor, patient)
    service.dispense_prescription(db_session, prescription.id, pharmacist)

    with pytest.raises(ValidationError, match="cannot be cancelled"):
        service.cancel_prescription(db_session, prescription.id, doctor)


@pytest.mark.unit
def test_lookup_by_reference_finds_an_issued_prescription(db_session):
    """The pharmacy counter searches by the printed code."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    pharmacist = make_user(db_session, university_id="PHR-3001", role=UserRole.PHARMACIST)
    prescription = issued_prescription(db_session, doctor, patient)

    found = service.find_by_reference(db_session, prescription.reference_code, pharmacist)

    assert found.id == prescription.id


@pytest.mark.unit
def test_lookup_ignores_a_draft(db_session):
    """A draft is invisible to the pharmacy even by reference code."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    pharmacist = make_user(db_session, university_id="PHR-3001", role=UserRole.PHARMACIST)
    link_appointment(db_session, doctor, patient)
    draft = service.create_prescription(db_session, doctor, prescription_payload(patient.id))

    with pytest.raises(NotFoundError):
        service.find_by_reference(db_session, draft.reference_code, pharmacist)


@pytest.mark.unit
def test_patient_list_excludes_drafts(db_session):
    """FR-D3: the patient sees issued prescriptions only."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    link_appointment(db_session, doctor, patient)
    service.create_prescription(db_session, doctor, prescription_payload(patient.id))
    issued = service.create_prescription(db_session, doctor, prescription_payload(patient.id))
    service.issue_prescription(db_session, issued.id, doctor)

    visible = service.list_for_patient(db_session, patient)

    assert len(visible) == 1
    assert visible[0].status == PrescriptionStatus.ISSUED.value


@pytest.mark.unit
def test_a_stranger_cannot_open_a_prescription(db_session):
    """Ownership is checked on the backend."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    stranger = make_user(db_session, university_id="STU-2021-370")
    prescription = issued_prescription(db_session, doctor, patient)

    with pytest.raises(PermissionDeniedError):
        service.get_prescription_for_user(db_session, prescription.id, stranger)


@pytest.mark.unit
def test_pharmacy_queue_lists_issued_prescriptions(db_session):
    """The dispensing queue shows what is waiting at the counter."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    pharmacist = make_user(db_session, university_id="PHR-3001", role=UserRole.PHARMACIST)
    issued_prescription(db_session, doctor, patient)

    queue = service.list_pharmacy_queue(db_session, pharmacist)

    assert len(queue) == 1


@pytest.mark.unit
def test_a_student_cannot_open_the_pharmacy_queue(db_session):
    """The queue belongs to the pharmacy role."""
    patient = make_user(db_session, university_id="STU-2021-364")

    with pytest.raises(PermissionDeniedError):
        service.list_pharmacy_queue(db_session, patient)
