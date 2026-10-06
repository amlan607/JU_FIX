"""Endpoint tests for the digital prescription controller (FR-D1, FR-D3)."""

from datetime import date, time

import pytest

from app.core.constants import AppointmentStatus, UserRole
from app.models.appointment import Appointment
from tests.conftest import auth_header, make_doctor, make_user


def link_appointment(db_session, doctor, patient) -> None:
    """Create the treatment relationship required by FR-D4."""
    db_session.add(
        Appointment(
            patient_id=patient.id,
            doctor_id=doctor.id,
            appointment_date=date.today(),
            start_time=time(10, 0),
            end_time=time(10, 20),
            reason="Fever and cough.",
            status=AppointmentStatus.COMPLETED.value,
        )
    )
    db_session.commit()


def prescription_body(patient_id: int) -> dict:
    """Build a valid create-prescription request body."""
    return {
        "patient_id": patient_id,
        "diagnosis": "Acute bacterial pharyngitis.",
        "advice": "Drink warm fluids and rest.",
        "items": [
            {
                "medicine_name": "Amoxicillin",
                "dosage": "500mg",
                "frequency": "1+1+1",
                "duration": "7 days",
                "instructions": "Take after meals.",
            }
        ],
    }


@pytest.mark.api
def test_creating_a_prescription_requires_authentication(client):
    """An anonymous request cannot write a prescription."""
    assert client.post("/api/prescriptions", json=prescription_body(1)).status_code == 401


@pytest.mark.api
def test_doctor_creates_a_draft(client, db_session):
    """FR-D1: the draft carries a reference code and the medicine lines."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    link_appointment(db_session, doctor, patient)

    response = client.post(
        "/api/prescriptions", json=prescription_body(patient.id), headers=auth_header(client, "DOC-2001")
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["status"] == "draft"
    assert data["reference_code"].startswith("RX-")
    assert data["items"][0]["medicine_name"] == "Amoxicillin"


@pytest.mark.api
def test_a_student_cannot_write_a_prescription(client, db_session):
    """Only doctors prescribe."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    link_appointment(db_session, doctor, patient)

    response = client.post(
        "/api/prescriptions",
        json=prescription_body(patient.id),
        headers=auth_header(client, "STU-2021-364"),
    )

    assert response.status_code == 403


@pytest.mark.api
def test_issue_then_patient_sees_it(client, db_session):
    """FR-D3: the patient list shows the prescription once it is issued."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    link_appointment(db_session, doctor, patient)
    doctor_headers = auth_header(client, "DOC-2001")

    created = client.post(
        "/api/prescriptions", json=prescription_body(patient.id), headers=doctor_headers
    ).json()["data"]

    before = client.get(
        "/api/prescriptions/my-prescriptions", headers=auth_header(client, "STU-2021-364")
    )
    assert before.json()["data"] == []

    client.patch(f"/api/prescriptions/{created['id']}/issue", headers=doctor_headers)

    after = client.get(
        "/api/prescriptions/my-prescriptions", headers=auth_header(client, "STU-2021-364")
    )
    assert len(after.json()["data"]) == 1
    assert after.json()["data"][0]["status"] == "issued"


@pytest.mark.api
def test_pharmacy_queue_shows_issued_prescriptions(client, db_session):
    """The pharmacist sees what is waiting to be dispensed."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    make_user(db_session, university_id="PHR-3001", role=UserRole.PHARMACIST)
    link_appointment(db_session, doctor, patient)
    doctor_headers = auth_header(client, "DOC-2001")

    created = client.post(
        "/api/prescriptions", json=prescription_body(patient.id), headers=doctor_headers
    ).json()["data"]
    client.patch(f"/api/prescriptions/{created['id']}/issue", headers=doctor_headers)

    response = client.get("/api/prescriptions/pharmacy-queue", headers=auth_header(client, "PHR-3001"))

    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


@pytest.mark.api
def test_dispensing_records_the_pharmacist(client, db_session):
    """The dispensing event names who handed over the medicines."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    make_user(db_session, university_id="PHR-3001", role=UserRole.PHARMACIST, full_name="Habibur Rahman")
    link_appointment(db_session, doctor, patient)
    doctor_headers = auth_header(client, "DOC-2001")

    created = client.post(
        "/api/prescriptions", json=prescription_body(patient.id), headers=doctor_headers
    ).json()["data"]
    client.patch(f"/api/prescriptions/{created['id']}/issue", headers=doctor_headers)

    response = client.patch(
        f"/api/prescriptions/{created['id']}/dispense",
        json={"note": "Full course handed over."},
        headers=auth_header(client, "PHR-3001"),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "dispensed"
    assert data["dispensed_by_name"] == "Habibur Rahman"


@pytest.mark.api
def test_lookup_by_reference_code(client, db_session):
    """The counter finds a prescription by the printed code."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    make_user(db_session, university_id="PHR-3001", role=UserRole.PHARMACIST)
    link_appointment(db_session, doctor, patient)
    doctor_headers = auth_header(client, "DOC-2001")

    created = client.post(
        "/api/prescriptions", json=prescription_body(patient.id), headers=doctor_headers
    ).json()["data"]
    client.patch(f"/api/prescriptions/{created['id']}/issue", headers=doctor_headers)

    response = client.get(
        "/api/prescriptions/lookup",
        params={"code": created["reference_code"]},
        headers=auth_header(client, "PHR-3001"),
    )

    assert response.status_code == 200
    assert response.json()["data"]["id"] == created["id"]


@pytest.mark.api
def test_an_unknown_reference_code_returns_404(client, db_session):
    """A wrong code is a clean 404 in the standard envelope."""
    make_user(db_session, university_id="PHR-3001", role=UserRole.PHARMACIST)

    response = client.get(
        "/api/prescriptions/lookup",
        params={"code": "RX-20260101-000000"},
        headers=auth_header(client, "PHR-3001"),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.api
def test_a_stranger_cannot_open_a_prescription(client, db_session):
    """Direct object access is refused on the backend."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    make_user(db_session, university_id="STU-2021-370")
    link_appointment(db_session, doctor, patient)
    doctor_headers = auth_header(client, "DOC-2001")

    created = client.post(
        "/api/prescriptions", json=prescription_body(patient.id), headers=doctor_headers
    ).json()["data"]
    client.patch(f"/api/prescriptions/{created['id']}/issue", headers=doctor_headers)

    response = client.get(
        f"/api/prescriptions/{created['id']}", headers=auth_header(client, "STU-2021-370")
    )

    assert response.status_code == 403


@pytest.mark.api
def test_editing_an_issued_prescription_returns_400(client, db_session):
    """The frozen medicine list is enforced through the API."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-364")
    link_appointment(db_session, doctor, patient)
    doctor_headers = auth_header(client, "DOC-2001")

    created = client.post(
        "/api/prescriptions", json=prescription_body(patient.id), headers=doctor_headers
    ).json()["data"]
    client.patch(f"/api/prescriptions/{created['id']}/issue", headers=doctor_headers)

    response = client.patch(
        f"/api/prescriptions/{created['id']}",
        json={"advice": "Changed advice."},
        headers=doctor_headers,
    )

    assert response.status_code == 400
