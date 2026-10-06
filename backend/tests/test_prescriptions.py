"""Tests for digital prescription management (FR-D1, FR-D3, FR-D4)."""

from datetime import date, time

import pytest

from app.core.constants import UserRole
from app.models.appointment import Appointment
from tests.conftest import auth_header, make_doctor, make_user

ITEM = {"medicine_name": "Amoxicillin", "dosage": "500mg", "frequency": "1+1+1", "duration": "7 days"}


def setup(db_session, treated=True):
    """Create a doctor, a patient, a pharmacist and (optionally) their appointment."""
    doctor, patient = make_doctor(db_session), make_user(db_session, university_id="STU-2021-364")
    make_user(db_session, university_id="PHR-3001", role=UserRole.PHARMACIST)
    if treated:
        db_session.add(Appointment(patient_id=patient.id, doctor_id=doctor.id, appointment_date=date.today(),
                                   start_time=time(10, 0), end_time=time(10, 20), reason="Sore throat.", status="completed"))
        db_session.commit()
    return patient


def draft(client, patient):
    """Create a draft as the doctor."""
    body = {"patient_id": patient.id, "diagnosis": "Pharyngitis.", "items": [ITEM]}
    return client.post("/api/prescriptions", json=body, headers=auth_header(client, "DOC-2001"))


@pytest.mark.api
def test_doctor_creates_a_draft_only_for_a_treated_patient(client, db_session):
    """FR-D1/D4: items and a reference code are stored; strangers cannot be prescribed for."""
    patient = setup(db_session, treated=False)
    assert draft(client, patient).status_code == 403
    db_session.add(Appointment(patient_id=patient.id, doctor_id=1, appointment_date=date.today(), start_time=time(9, 0),
                               end_time=time(9, 20), reason="x", status="booked"))
    db_session.commit()
    created = draft(client, patient)
    assert created.status_code == 201
    assert created.json()["data"]["reference_code"].startswith("RX-")


@pytest.mark.api
def test_patient_sees_a_prescription_only_after_it_is_issued(client, db_session):
    """FR-D3: a draft is invisible (404); an issued one is listed; a stranger gets 403."""
    patient = setup(db_session)
    make_user(db_session, university_id="STU-2021-370")
    created = draft(client, patient).json()["data"]
    mine = auth_header(client, "STU-2021-364")
    assert client.get(f"/api/prescriptions/{created['id']}", headers=mine).status_code == 404
    client.patch(f"/api/prescriptions/{created['id']}/issue", headers=auth_header(client, "DOC-2001"))
    assert len(client.get("/api/prescriptions/my-prescriptions", headers=mine).json()["data"]) == 1
    assert client.get(f"/api/prescriptions/{created['id']}", headers=auth_header(client, "STU-2021-370")).status_code == 403
