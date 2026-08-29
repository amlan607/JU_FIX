"""Endpoint tests for the medical certificate controller (FR-F1 to FR-F4)."""

from datetime import date, time, timedelta

import pytest

from app.core.constants import AppointmentStatus
from app.models.appointment import Appointment
from tests.conftest import auth_header, make_doctor, make_user


def completed_appointment(db_session, doctor, patient) -> Appointment:
    """Create the completed consultation FR-F1 requires."""
    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=date.today(),
        start_time=time(10, 0),
        end_time=time(10, 20),
        reason="High fever and body ache.",
        status=AppointmentStatus.COMPLETED.value,
    )
    db_session.add(appointment)
    db_session.commit()
    db_session.refresh(appointment)
    return appointment


def certificate_body(appointment_id: int) -> dict:
    """Build a valid certificate request body."""
    return {
        "appointment_id": appointment_id,
        "reason": "Advised three days of bed rest after a viral fever.",
        "leave_start": date.today().isoformat(),
        "leave_end": (date.today() + timedelta(days=2)).isoformat(),
    }


@pytest.mark.api
def test_requesting_a_certificate_requires_authentication(client):
    """An anonymous request cannot create a certificate."""
    assert client.post("/api/certificates", json=certificate_body(1)).status_code == 401


@pytest.mark.api
def test_patient_requests_a_certificate(client, db_session):
    """FR-F1: the request is created against the completed consultation."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    appointment = completed_appointment(db_session, doctor, patient)

    response = client.post(
        "/api/certificates",
        json=certificate_body(appointment.id),
        headers=auth_header(client, "STU-2021-376"),
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["status"] == "submitted"
    assert data["leave_days"] == 3


@pytest.mark.api
def test_a_doctor_cannot_request_a_certificate(client, db_session):
    """Only patient roles request sick leave."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    appointment = completed_appointment(db_session, doctor, patient)

    response = client.post(
        "/api/certificates",
        json=certificate_body(appointment.id),
        headers=auth_header(client, "DOC-2001"),
    )

    assert response.status_code == 403


@pytest.mark.api
def test_doctor_review_queue_lists_the_request(client, db_session):
    """FR-F2: the request reaches the treating doctor's queue."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    appointment = completed_appointment(db_session, doctor, patient)
    client.post(
        "/api/certificates",
        json=certificate_body(appointment.id),
        headers=auth_header(client, "STU-2021-376"),
    )

    response = client.get("/api/certificates/review-queue", headers=auth_header(client, "DOC-2001"))

    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


@pytest.mark.api
def test_approval_returns_a_reference_id(client, db_session):
    """FR-F3: approval produces the downloadable, verifiable certificate."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    appointment = completed_appointment(db_session, doctor, patient)
    created = client.post(
        "/api/certificates",
        json=certificate_body(appointment.id),
        headers=auth_header(client, "STU-2021-376"),
    ).json()["data"]

    response = client.patch(
        f"/api/certificates/{created['id']}/decision",
        json={"approve": True, "remarks": "Fit to resume classes after rest."},
        headers=auth_header(client, "DOC-2001"),
    )

    assert response.status_code == 200
    assert response.json()["data"]["reference_id"].startswith("JUMC-")


@pytest.mark.api
def test_rejection_without_remarks_returns_400(client, db_session):
    """FR-F2: a refusal must carry a reason."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    appointment = completed_appointment(db_session, doctor, patient)
    created = client.post(
        "/api/certificates",
        json=certificate_body(appointment.id),
        headers=auth_header(client, "STU-2021-376"),
    ).json()["data"]

    response = client.patch(
        f"/api/certificates/{created['id']}/decision",
        json={"approve": False},
        headers=auth_header(client, "DOC-2001"),
    )

    assert response.status_code == 400


@pytest.mark.api
def test_verification_endpoint_is_public(client, db_session):
    """FR-F4: a department office verifies without a JU_FIX account."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    appointment = completed_appointment(db_session, doctor, patient)
    created = client.post(
        "/api/certificates",
        json=certificate_body(appointment.id),
        headers=auth_header(client, "STU-2021-376"),
    ).json()["data"]
    approved = client.patch(
        f"/api/certificates/{created['id']}/decision",
        json={"approve": True, "remarks": "Approved."},
        headers=auth_header(client, "DOC-2001"),
    ).json()["data"]

    response = client.get(
        "/api/certificates/verify", params={"reference": approved["reference_id"]}
    )

    assert response.status_code == 200
    assert response.json()["data"]["valid"] is True


@pytest.mark.api
def test_verification_does_not_leak_the_medical_reason(client, db_session):
    """The public payload confirms authenticity only."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    appointment = completed_appointment(db_session, doctor, patient)
    created = client.post(
        "/api/certificates",
        json=certificate_body(appointment.id),
        headers=auth_header(client, "STU-2021-376"),
    ).json()["data"]
    approved = client.patch(
        f"/api/certificates/{created['id']}/decision",
        json={"approve": True, "remarks": "Approved."},
        headers=auth_header(client, "DOC-2001"),
    ).json()["data"]

    response = client.get(
        "/api/certificates/verify", params={"reference": approved["reference_id"]}
    )

    assert "bed rest" not in response.text


@pytest.mark.api
def test_verifying_an_unknown_reference_reports_invalid(client):
    """A forged reference returns a clean negative result."""
    response = client.get("/api/certificates/verify", params={"reference": "JUMC-2026-000000"})

    assert response.status_code == 200
    assert response.json()["data"]["valid"] is False


@pytest.mark.api
def test_a_stranger_cannot_open_a_certificate(client, db_session):
    """Direct object access is refused on the backend."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-376")
    make_user(db_session, university_id="STU-2021-370")
    appointment = completed_appointment(db_session, doctor, patient)
    created = client.post(
        "/api/certificates",
        json=certificate_body(appointment.id),
        headers=auth_header(client, "STU-2021-376"),
    ).json()["data"]

    response = client.get(
        f"/api/certificates/{created['id']}", headers=auth_header(client, "STU-2021-370")
    )

    assert response.status_code == 403
