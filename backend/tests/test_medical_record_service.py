"""Unit tests for the Electronic Health Record business rules (FR-D2 to FR-D5)."""

from datetime import date, time, timedelta

import pytest

from app.core.constants import AppointmentStatus, RecordType, UserRole
from app.core.errors import NotFoundError, PermissionDeniedError, ValidationError
from app.models.appointment import Appointment
from app.schemas.medical_record import CreateRecordRequest, UpdateRecordRequest
from app.services import medical_record_service as service
from tests.conftest import make_doctor, make_user


def link_appointment(
    db_session,
    doctor,
    patient,
    status: AppointmentStatus = AppointmentStatus.COMPLETED,
) -> Appointment:
    """Create the appointment that establishes a treatment relationship (FR-D4)."""
    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=date.today(),
        start_time=time(10, 0),
        end_time=time(10, 20),
        reason="Fever and sore throat.",
        status=status.value,
    )
    db_session.add(appointment)
    db_session.commit()
    db_session.refresh(appointment)
    return appointment


def record_payload(patient_id: int, **overrides) -> CreateRecordRequest:
    """Build a valid clinical record payload."""
    data = {
        "patient_id": patient_id,
        "visit_date": date.today(),
        "title": "Acute viral fever",
        "diagnosis": "Viral fever with mild dehydration.",
        "symptoms": "Fever 102F for three days, headache.",
        "treatment": "Paracetamol 500mg, oral rehydration, rest.",
        "record_type": RecordType.CONSULTATION,
    }
    data.update(overrides)
    return CreateRecordRequest(**data)


@pytest.mark.unit
def test_doctor_with_an_appointment_has_a_treatment_relationship(db_session):
    """FR-D4: an appointment authorises the doctor."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)

    assert service.doctor_has_treatment_relationship(db_session, doctor.id, patient.id) is True


@pytest.mark.unit
def test_doctor_without_any_link_has_no_relationship(db_session):
    """FR-D4: holding a doctor account is not sufficient on its own."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")

    assert service.doctor_has_treatment_relationship(db_session, doctor.id, patient.id) is False


@pytest.mark.unit
def test_a_cancelled_appointment_does_not_grant_access(db_session):
    """A cancelled consultation never took place, so it authorises nothing."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient, AppointmentStatus.CANCELLED)

    assert service.doctor_has_treatment_relationship(db_session, doctor.id, patient.id) is False


@pytest.mark.unit
def test_doctor_can_create_a_record_for_a_treated_patient(db_session):
    """FR-D2: an authorised doctor adds a clinical entry."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)

    record = service.create_record(db_session, doctor, record_payload(patient.id))

    assert record.version == 1
    assert record.doctor_id == doctor.id


@pytest.mark.unit
def test_doctor_cannot_create_a_record_without_a_relationship(db_session):
    """FR-D4 is enforced on write as well as on read."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")

    with pytest.raises(PermissionDeniedError):
        service.create_record(db_session, doctor, record_payload(patient.id))


@pytest.mark.unit
def test_a_future_visit_date_is_refused(db_session):
    """A consultation cannot be recorded before it happens."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)

    with pytest.raises(ValidationError, match="future"):
        service.create_record(
            db_session,
            doctor,
            record_payload(patient.id, visit_date=date.today() + timedelta(days=1)),
        )


@pytest.mark.unit
def test_a_record_cannot_be_created_for_a_doctor_account(db_session):
    """Only patient roles hold a health record."""
    doctor = make_doctor(db_session)
    other_doctor = make_doctor(db_session, university_id="DOC-2002")
    link_appointment(db_session, doctor, other_doctor)

    with pytest.raises(ValidationError, match="students, faculty"):
        service.create_record(db_session, doctor, record_payload(other_doctor.id))


@pytest.mark.unit
def test_linking_another_patients_appointment_is_refused(db_session):
    """A record must not be attached to an unrelated consultation."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    other_patient = make_user(db_session, university_id="STU-2021-376")
    link_appointment(db_session, doctor, patient)
    other_appointment = link_appointment(db_session, doctor, other_patient)

    with pytest.raises(ValidationError, match="does not match"):
        service.create_record(
            db_session, doctor, record_payload(patient.id, appointment_id=other_appointment.id)
        )


@pytest.mark.unit
def test_patient_can_read_their_own_record(db_session):
    """FR-D3: a patient always has access to their own history."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)
    record = service.create_record(db_session, doctor, record_payload(patient.id))

    assert service.get_record(db_session, record.id, patient).id == record.id


@pytest.mark.unit
def test_another_patient_cannot_read_someone_elses_record(db_session):
    """Ownership scoping prevents cross patient access."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    stranger = make_user(db_session, university_id="STU-2021-376")
    link_appointment(db_session, doctor, patient)
    record = service.create_record(db_session, doctor, record_payload(patient.id))

    with pytest.raises(PermissionDeniedError):
        service.get_record(db_session, record.id, stranger)


@pytest.mark.unit
def test_an_unrelated_doctor_cannot_read_a_record(db_session):
    """FR-D4: role alone does not grant clinical access."""
    doctor = make_doctor(db_session)
    outsider = make_doctor(db_session, university_id="DOC-2002")
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)
    record = service.create_record(db_session, doctor, record_payload(patient.id))

    with pytest.raises(PermissionDeniedError):
        service.get_record(db_session, record.id, outsider)


@pytest.mark.unit
def test_an_admin_cannot_read_clinical_content(db_session):
    """Administrators manage accounts, not diagnoses (NFR-B, least privilege)."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    link_appointment(db_session, doctor, patient)
    record = service.create_record(db_session, doctor, record_payload(patient.id))

    with pytest.raises(PermissionDeniedError):
        service.get_record(db_session, record.id, admin)


@pytest.mark.unit
def test_editing_a_record_creates_a_version_snapshot(db_session):
    """FR-D5: the previous state is preserved before the edit is applied."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)
    record = service.create_record(db_session, doctor, record_payload(patient.id))

    service.update_record(
        db_session,
        record.id,
        doctor,
        UpdateRecordRequest(diagnosis="Dengue fever confirmed by NS1.", change_note="Lab result."),
    )

    versions = service.list_record_versions(db_session, record.id, doctor)
    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert versions[0].diagnosis == "Viral fever with mild dehydration."


@pytest.mark.unit
def test_editing_increments_the_version_number(db_session):
    """Each edit advances the record version."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)
    record = service.create_record(db_session, doctor, record_payload(patient.id))

    updated = service.update_record(
        db_session, record.id, doctor, UpdateRecordRequest(treatment="Add IV fluids.")
    )

    assert updated.version == 2


@pytest.mark.unit
def test_two_edits_produce_two_snapshots(db_session):
    """The history holds one row per superseded version."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)
    record = service.create_record(db_session, doctor, record_payload(patient.id))

    service.update_record(db_session, record.id, doctor, UpdateRecordRequest(notes="First edit."))
    service.update_record(db_session, record.id, doctor, UpdateRecordRequest(notes="Second edit."))

    versions = service.list_record_versions(db_session, record.id, doctor)
    assert [version.version_number for version in versions] == [2, 1]


@pytest.mark.unit
def test_only_the_authoring_doctor_may_edit(db_session):
    """Clinical accountability stays with the author."""
    author = make_doctor(db_session)
    colleague = make_doctor(db_session, university_id="DOC-2002")
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, author, patient)
    link_appointment(db_session, colleague, patient)
    record = service.create_record(db_session, author, record_payload(patient.id))

    with pytest.raises(PermissionDeniedError, match="authored"):
        service.update_record(db_session, record.id, colleague, UpdateRecordRequest(notes="Edit."))


@pytest.mark.unit
def test_an_empty_edit_is_refused(db_session):
    """A request that changes nothing is a validation error."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)
    record = service.create_record(db_session, doctor, record_payload(patient.id))

    with pytest.raises(ValidationError):
        service.update_record(db_session, record.id, doctor, UpdateRecordRequest())


@pytest.mark.unit
def test_a_missing_record_raises_not_found(db_session):
    """An unknown identifier is a 404, not a permission error."""
    patient = make_user(db_session, university_id="STU-2021-375")

    with pytest.raises(NotFoundError):
        service.get_record(db_session, 9999, patient)


@pytest.mark.unit
def test_records_are_listed_newest_visit_first(db_session):
    """The timeline reads from the most recent consultation."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)

    service.create_record(
        db_session, doctor, record_payload(patient.id, visit_date=date.today() - timedelta(days=10))
    )
    service.create_record(db_session, doctor, record_payload(patient.id, title="Recent visit"))

    records = service.list_patient_records(db_session, patient, patient.id)
    assert records[0].title == "Recent visit"


@pytest.mark.unit
def test_records_can_be_filtered_by_type(db_session):
    """The timeline filter narrows the entries by record type."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)

    service.create_record(db_session, doctor, record_payload(patient.id))
    service.create_record(
        db_session,
        doctor,
        record_payload(patient.id, title="Tetanus booster", record_type=RecordType.VACCINATION),
    )

    vaccinations = service.list_patient_records(
        db_session, patient, patient.id, RecordType.VACCINATION.value
    )
    assert len(vaccinations) == 1
    assert vaccinations[0].title == "Tetanus booster"


@pytest.mark.unit
def test_authorised_patient_list_includes_appointment_patients(db_session):
    """FR-D4: the doctor's patient list is built from their own caseload."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    make_user(db_session, university_id="STU-2021-376")
    link_appointment(db_session, doctor, patient)

    patients = service.list_authorised_patients(db_session, doctor)

    assert len(patients) == 1
    assert patients[0]["university_id"] == "STU-2021-375"


@pytest.mark.unit
def test_authorised_patient_list_reports_record_counts(db_session):
    """The list shows how many entries each patient already has."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)
    service.create_record(db_session, doctor, record_payload(patient.id))

    patients = service.list_authorised_patients(db_session, doctor)

    assert patients[0]["record_count"] == 1
    assert patients[0]["last_visit"] == date.today()


@pytest.mark.unit
def test_a_non_doctor_cannot_request_the_patient_list(db_session):
    """The caseload view belongs to doctors only."""
    patient = make_user(db_session, university_id="STU-2021-375")

    with pytest.raises(PermissionDeniedError):
        service.list_authorised_patients(db_session, patient)


@pytest.mark.unit
def test_viewing_a_record_writes_an_audit_entry(db_session):
    """NFR-B: every access to clinical data is traceable."""
    from app.models.audit_log import AuditLog

    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)
    record = service.create_record(db_session, doctor, record_payload(patient.id))

    service.get_record(db_session, record.id, patient)

    views = db_session.query(AuditLog).filter(AuditLog.action == "record.view").all()
    assert len(views) == 1
    assert views[0].actor_id == patient.id


@pytest.mark.unit
def test_the_audit_entry_holds_no_clinical_content(db_session):
    """The audit trail records who and what, never the diagnosis text."""
    from app.models.audit_log import AuditLog

    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)
    record = service.create_record(db_session, doctor, record_payload(patient.id))

    entries = db_session.query(AuditLog).filter(AuditLog.entity_id == record.id).all()

    assert all("Viral fever" not in (entry.summary or "") for entry in entries)
