"""Endpoint tests for the Electronic Health Record controller (FR-D)."""

from datetime import date, time

import pytest

from app.core.constants import AppointmentStatus, UserRole
from app.models.appointment import Appointment
from tests.conftest import auth_header, make_doctor, make_user


def link_appointment(db_session, doctor, patient) -> Appointment:
    """Create the treatment relationship required by FR-D4."""
    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=date.today(),
        start_time=time(10, 0),
        end_time=time(10, 20),
        reason="Fever and sore throat.",
        status=AppointmentStatus.COMPLETED.value,
    )
    db_session.add(appointment)
    db_session.commit()
    db_session.refresh(appointment)
    return appointment


def record_body(patient_id: int, **overrides) -> dict:
    """Build a valid create-record request body."""
    body = {
        "patient_id": patient_id,
        "visit_date": date.today().isoformat(),
        "title": "Acute viral fever",
        "diagnosis": "Viral fever with mild dehydration.",
        "symptoms": "Fever 102F for three days.",
        "treatment": "Paracetamol 500mg and rest.",
    }
    body.update(overrides)
    return body


@pytest.mark.api
def test_creating_a_record_requires_authentication(client):
    """An anonymous request never reaches clinical data."""
    assert client.post("/api/medical-records", json=record_body(1)).status_code == 401


@pytest.mark.api
def test_doctor_creates_a_record(client, db_session):
    """FR-D2: an authorised doctor adds an entry and receives 201."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)

    response = client.post(
        "/api/medical-records",
        json=record_body(patient.id),
        headers=auth_header(client, "DOC-2001"),
    )

    assert response.status_code == 201
    assert response.json()["data"]["version"] == 1
    assert response.json()["data"]["patient_name"] == "Test User"


@pytest.mark.api
def test_a_student_cannot_create_a_record(client, db_session):
    """Only doctors write clinical entries."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)

    response = client.post(
        "/api/medical-records",
        json=record_body(patient.id),
        headers=auth_header(client, "STU-2021-375"),
    )

    assert response.status_code == 403


@pytest.mark.api
def test_patient_reads_their_own_timeline(client, db_session):
    """FR-D3: a patient views their own consultation history."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)
    client.post(
        "/api/medical-records",
        json=record_body(patient.id),
        headers=auth_header(client, "DOC-2001"),
    )

    response = client.get("/api/medical-records/my-records", headers=auth_header(client, "STU-2021-375"))

    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
    assert response.json()["data"][0]["title"] == "Acute viral fever"


@pytest.mark.api
def test_a_patient_cannot_read_another_patients_timeline(client, db_session):
    """Direct object access is checked on the backend."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    make_user(db_session, university_id="STU-2021-376")
    link_appointment(db_session, doctor, patient)

    response = client.get(
        f"/api/medical-records/patients/{patient.id}",
        headers=auth_header(client, "STU-2021-376"),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


@pytest.mark.api
def test_an_unrelated_doctor_is_refused(client, db_session):
    """FR-D4: role alone does not open a patient's record."""
    doctor = make_doctor(db_session)
    make_doctor(db_session, university_id="DOC-2002")
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)

    response = client.get(
        f"/api/medical-records/patients/{patient.id}",
        headers=auth_header(client, "DOC-2002"),
    )

    assert response.status_code == 403


@pytest.mark.api
def test_doctor_patient_list_shows_only_their_caseload(client, db_session):
    """FR-D4: the doctor console lists authorised patients only."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    make_user(db_session, university_id="STU-2021-376")
    link_appointment(db_session, doctor, patient)

    response = client.get("/api/medical-records/patients", headers=auth_header(client, "DOC-2001"))

    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


@pytest.mark.api
def test_editing_a_record_returns_the_new_version(client, db_session):
    """FR-D5: an edit advances the version number."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)
    headers = auth_header(client, "DOC-2001")

    created = client.post(
        "/api/medical-records", json=record_body(patient.id), headers=headers
    ).json()["data"]

    response = client.patch(
        f"/api/medical-records/{created['id']}",
        json={"diagnosis": "Dengue fever confirmed.", "change_note": "NS1 positive."},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["version"] == 2


@pytest.mark.api
def test_version_history_is_returned(client, db_session):
    """FR-D5: the history endpoint exposes the superseded state."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    link_appointment(db_session, doctor, patient)
    headers = auth_header(client, "DOC-2001")

    created = client.post(
        "/api/medical-records", json=record_body(patient.id), headers=headers
    ).json()["data"]
    client.patch(
        f"/api/medical-records/{created['id']}",
        json={"diagnosis": "Dengue fever confirmed.", "change_note": "NS1 positive."},
        headers=headers,
    )

    response = client.get(f"/api/medical-records/{created['id']}/versions", headers=headers)

    assert response.status_code == 200
    history = response.json()["data"]
    assert len(history) == 1
    assert history[0]["change_note"] == "NS1 positive."
    assert history[0]["editor_name"] == "Dr. Test Doctor"


@pytest.mark.api
def test_an_admin_is_refused_clinical_content(client, db_session):
    """Least privilege: administrators manage accounts, not diagnoses."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-375")
    make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    link_appointment(db_session, doctor, patient)

    response = client.get(
        f"/api/medical-records/patients/{patient.id}", headers=auth_header(client, "ADM-4001")
    )

    assert response.status_code == 403


@pytest.mark.api
def test_a_missing_record_returns_404(client, db_session):
    """An unknown record identifier answers with 404 in the standard envelope."""
    make_user(db_session, university_id="STU-2021-375")

    response = client.get("/api/medical-records/9999", headers=auth_header(client, "STU-2021-375"))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
