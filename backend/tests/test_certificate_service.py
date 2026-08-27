"""Unit tests for the medical certificate business rules (FR-F1 to FR-F4)."""

from datetime import date, time, timedelta

import pytest

from app.core.constants import AppointmentStatus, CertificateStatus, UserRole
from app.core.errors import ConflictError, PermissionDeniedError, ValidationError
from app.models.appointment import Appointment
from app.schemas.certificate import CreateCertificateRequest, DecideCertificateRequest
from app.services import certificate_service as service
from tests.conftest import make_doctor, make_user


def completed_appointment(
    db_session, doctor, patient, status: AppointmentStatus = AppointmentStatus.COMPLETED
) -> Appointment:
    """Create the consultation a certificate request must reference."""
    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=date.today(),
        start_time=time(10, 0),
        end_time=time(10, 20),
        reason="High fever and body ache.",
        status=status.value,
    )
    db_session.add(appointment)
    db_session.commit()
    db_session.refresh(appointment)
    return appointment


def certificate_payload(appointment_id: int, **overrides) -> CreateCertificateRequest:
    """Build a valid certificate request payload."""
    data = {
        "appointment_id": appointment_id,
        "reason": "Advised three days of bed rest after a viral fever.",
        "leave_start": date.today(),
        "leave_end": date.today() + timedelta(days=2),
    }
    data.update(overrides)
    return CreateCertificateRequest(**data)


def approved_certificate(db_session, doctor, patient):
    """Create and approve a certificate, returning it."""
    appointment = completed_appointment(db_session, doctor, patient)
    request = service.request_certificate(db_session, patient, certificate_payload(appointment.id))
    return service.decide_certificate(db_session, request.id, doctor, True, "Fit to resume after rest.")


@pytest.mark.unit
def test_patient_requests_a_certificate_after_a_consultation(db_session):
    """FR-F1: the request is tied to a completed consultation."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    appointment = completed_appointment(db_session, doctor, patient)

    request = service.request_certificate(db_session, patient, certificate_payload(appointment.id))

    assert request.status == CertificateStatus.SUBMITTED.value
    assert request.doctor_id == doctor.id
    assert request.leave_days == 3


@pytest.mark.unit
def test_a_certificate_cannot_precede_the_consultation(db_session):
    """FR-F1: the consultation must have taken place first."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    appointment = completed_appointment(db_session, doctor, patient, AppointmentStatus.BOOKED)

    with pytest.raises(ValidationError, match="completed"):
        service.request_certificate(db_session, patient, certificate_payload(appointment.id))


@pytest.mark.unit
def test_a_patient_cannot_request_against_someone_elses_appointment(db_session):
    """Ownership of the consultation is checked on the backend."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    stranger = make_user(db_session, university_id="STU-2021-370")
    appointment = completed_appointment(db_session, doctor, patient)

    with pytest.raises(PermissionDeniedError):
        service.request_certificate(db_session, stranger, certificate_payload(appointment.id))


@pytest.mark.unit
def test_leave_cannot_start_before_the_consultation(db_session):
    """Backdating leave beyond the consultation date is refused."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    appointment = completed_appointment(db_session, doctor, patient)

    with pytest.raises(ValidationError, match="before the consultation"):
        service.request_certificate(
            db_session,
            patient,
            certificate_payload(
                appointment.id,
                leave_start=date.today() - timedelta(days=5),
                leave_end=date.today(),
            ),
        )


@pytest.mark.unit
def test_an_over_long_leave_period_is_refused(db_session):
    """A single certificate covers a bounded period."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    appointment = completed_appointment(db_session, doctor, patient)

    with pytest.raises(ValidationError, match="at most"):
        service.request_certificate(
            db_session,
            patient,
            certificate_payload(
                appointment.id, leave_end=date.today() + timedelta(days=service.MAX_LEAVE_DAYS + 5)
            ),
        )


@pytest.mark.unit
def test_an_end_date_before_the_start_date_is_refused():
    """The schema rejects an inverted leave window."""
    with pytest.raises(ValueError):
        CreateCertificateRequest(
            appointment_id=1,
            reason="Advised bed rest after a viral fever.",
            leave_start=date.today(),
            leave_end=date.today() - timedelta(days=1),
        )


@pytest.mark.unit
def test_a_duplicate_open_request_is_refused(db_session):
    """One consultation produces one open certificate request."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    appointment = completed_appointment(db_session, doctor, patient)
    service.request_certificate(db_session, patient, certificate_payload(appointment.id))

    with pytest.raises(ConflictError):
        service.request_certificate(db_session, patient, certificate_payload(appointment.id))


@pytest.mark.unit
def test_a_rejected_request_can_be_resubmitted(db_session):
    """A refusal does not permanently block the consultation."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    appointment = completed_appointment(db_session, doctor, patient)
    first = service.request_certificate(db_session, patient, certificate_payload(appointment.id))
    service.decide_certificate(db_session, first.id, doctor, False, "Symptoms do not require leave.")

    second = service.request_certificate(db_session, patient, certificate_payload(appointment.id))

    assert second.status == CertificateStatus.SUBMITTED.value


@pytest.mark.unit
def test_approval_assigns_a_reference_and_signature(db_session):
    """FR-F3: an approved certificate is digitally signed and identifiable."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")

    certificate = approved_certificate(db_session, doctor, patient)

    assert certificate.status == CertificateStatus.APPROVED.value
    assert certificate.reference_id.startswith("JUMC-")
    assert len(certificate.signature) == 64


@pytest.mark.unit
def test_rejection_requires_remarks(db_session):
    """FR-F2: a refusal must explain itself."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    appointment = completed_appointment(db_session, doctor, patient)
    request = service.request_certificate(db_session, patient, certificate_payload(appointment.id))

    with pytest.raises(ValidationError, match="remarks"):
        service.decide_certificate(db_session, request.id, doctor, False, None)


@pytest.mark.unit
def test_rejection_records_the_remarks(db_session):
    """The patient can read why the request was refused."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    appointment = completed_appointment(db_session, doctor, patient)
    request = service.request_certificate(db_session, patient, certificate_payload(appointment.id))

    decided = service.decide_certificate(
        db_session, request.id, doctor, False, "Symptoms are mild and do not require leave."
    )

    assert decided.status == CertificateStatus.REJECTED.value
    assert decided.doctor_remarks == "Symptoms are mild and do not require leave."
    assert decided.reference_id is None


@pytest.mark.unit
def test_a_rejected_request_never_gets_a_signature(db_session):
    """Only an approved certificate is signed."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    appointment = completed_appointment(db_session, doctor, patient)
    request = service.request_certificate(db_session, patient, certificate_payload(appointment.id))

    decided = service.decide_certificate(db_session, request.id, doctor, False, "Not required.")

    assert decided.signature is None


@pytest.mark.unit
def test_only_the_treating_doctor_may_decide(db_session):
    """A colleague cannot sign off another doctor's consultation."""
    doctor = make_doctor(db_session)
    colleague = make_doctor(db_session, university_id="DOC-2002")
    patient = make_user(db_session, university_id="STU-2021-376")
    appointment = completed_appointment(db_session, doctor, patient)
    request = service.request_certificate(db_session, patient, certificate_payload(appointment.id))

    with pytest.raises(PermissionDeniedError):
        service.decide_certificate(db_session, request.id, colleague, True, "Approved.")


@pytest.mark.unit
def test_a_request_cannot_be_decided_twice(db_session):
    """A decision is final."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    certificate = approved_certificate(db_session, doctor, patient)

    with pytest.raises(ValidationError, match="already been decided"):
        service.decide_certificate(db_session, certificate.id, doctor, False, "Changed my mind.")


@pytest.mark.unit
def test_verification_confirms_a_genuine_certificate(db_session):
    """FR-F4: a valid reference verifies successfully."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376", full_name="Shadman Rahman")
    certificate = approved_certificate(db_session, doctor, patient)

    result = service.verify_certificate(db_session, certificate.reference_id)

    assert result["valid"] is True
    assert result["patient_name"] == "Shadman Rahman"
    assert result["leave_days"] == 3


@pytest.mark.unit
def test_verification_never_discloses_the_medical_reason(db_session):
    """FR-F4 confirms authenticity without revealing clinical detail."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    certificate = approved_certificate(db_session, doctor, patient)

    result = service.verify_certificate(db_session, certificate.reference_id)

    assert "reason" not in result
    assert "bed rest" not in str(result)


@pytest.mark.unit
def test_verification_rejects_an_unknown_reference(db_session):
    """A forged reference does not verify."""
    result = service.verify_certificate(db_session, "JUMC-2026-999999")

    assert result["valid"] is False


@pytest.mark.unit
def test_verification_rejects_a_pending_request(db_session):
    """Only an approved certificate is verifiable."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    appointment = completed_appointment(db_session, doctor, patient)
    service.request_certificate(db_session, patient, certificate_payload(appointment.id))

    assert service.verify_certificate(db_session, "JUMC-2026-000001")["valid"] is False


@pytest.mark.unit
def test_verification_fails_after_the_record_is_tampered_with(db_session):
    """The signature detects a change to the issued leave window."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    certificate = approved_certificate(db_session, doctor, patient)

    certificate.leave_end = certificate.leave_end + timedelta(days=10)
    db_session.commit()

    result = service.verify_certificate(db_session, certificate.reference_id)

    assert result["valid"] is False
    assert "authenticity" in result["message"]


@pytest.mark.unit
def test_reference_ids_are_unique(db_session):
    """Two certificates never share a reference."""
    assert service.generate_reference_id(db_session) != service.generate_reference_id(db_session)


@pytest.mark.unit
def test_a_stranger_cannot_open_a_certificate(db_session):
    """Direct object access is checked on the backend."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    stranger = make_user(db_session, university_id="STU-2021-370")
    certificate = approved_certificate(db_session, doctor, patient)

    with pytest.raises(PermissionDeniedError):
        service.get_certificate_for_user(db_session, certificate.id, stranger)


@pytest.mark.unit
def test_the_review_queue_is_scoped_to_the_doctor(db_session):
    """FR-F2: a doctor reviews only their own consultations."""
    doctor = make_doctor(db_session)
    colleague = make_doctor(db_session, university_id="DOC-2002")
    patient = make_user(db_session, university_id="STU-2021-376")
    appointment = completed_appointment(db_session, doctor, patient)
    service.request_certificate(db_session, patient, certificate_payload(appointment.id))

    assert len(service.list_for_doctor(db_session, doctor)) == 1
    assert len(service.list_for_doctor(db_session, colleague)) == 0


@pytest.mark.unit
def test_a_student_cannot_open_the_review_queue(db_session):
    """The review queue belongs to doctors."""
    patient = make_user(db_session, university_id="STU-2021-376")

    with pytest.raises(PermissionDeniedError):
        service.list_for_doctor(db_session, patient)


@pytest.mark.unit
def test_a_pharmacist_cannot_request_a_certificate(db_session):
    """Only patient roles request sick leave."""
    doctor = make_doctor(db_session)
    pharmacist = make_user(db_session, university_id="PHR-3001", role=UserRole.PHARMACIST)
    appointment = completed_appointment(db_session, doctor, pharmacist)

    with pytest.raises(PermissionDeniedError):
        service.request_certificate(db_session, pharmacist, certificate_payload(appointment.id))


@pytest.mark.unit
def test_decision_schema_requires_remarks_on_rejection():
    """The schema blocks a bare rejection before it reaches the service."""
    with pytest.raises(ValueError):
        DecideCertificateRequest(approve=False, remarks="   ")
