"""Tests for Electronic Health Records (FR-D2 to FR-D5)."""

from datetime import date, time

import pytest

from app.core.constants import UserRole
from app.models.appointment import Appointment
from app.models.audit_log import AuditLog
from tests.conftest import auth_header, make_doctor, make_user


def link(db_session, doctor, patient):
    """Create the appointment that gives a doctor a treatment relationship."""
    db_session.add(Appointment(patient_id=patient.id, doctor_id=doctor.id, appointment_date=date.today(),
                               start_time=time(10, 0), end_time=time(10, 20), reason="Fever.", status="completed"))
    db_session.commit()


def body(patient_id, **extra):
    """Build a valid record payload."""
    return {"patient_id": patient_id, "visit_date": date.today().isoformat(), "title": "Viral fever",
            "diagnosis": "Viral fever with dehydration.", **extra}


@pytest.mark.api
def test_treating_doctor_creates_and_patient_reads(client, db_session):
    """FR-D2/D3: the doctor writes an entry and the patient sees it in their timeline."""
    doctor, patient = make_doctor(db_session), make_user(db_session, university_id="STU-2021-375")
    link(db_session, doctor, patient)
    created = client.post("/api/medical-records", json=body(patient.id), headers=auth_header(client, "DOC-2001"))
    assert created.status_code == 201 and created.json()["data"]["version"] == 1
    mine = client.get("/api/medical-records/my-records", headers=auth_header(client, "STU-2021-375"))
    assert mine.json()["data"][0]["title"] == "Viral fever"


@pytest.mark.api
def test_access_needs_a_treatment_relationship(client, db_session):
    """FR-D4: unrelated doctors, other patients and admins are all refused."""
    doctor, patient = make_doctor(db_session), make_user(db_session, university_id="STU-2021-375")
    make_doctor(db_session, university_id="DOC-2002")
    make_user(db_session, university_id="STU-2021-376")
    make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    assert client.post("/api/medical-records", json=body(patient.id), headers=auth_header(client, "DOC-2001")).status_code == 403
    link(db_session, doctor, patient)
    client.post("/api/medical-records", json=body(patient.id), headers=auth_header(client, "DOC-2001"))
    url = f"/api/medical-records/patients/{patient.id}"
    for who in ("DOC-2002", "STU-2021-376", "ADM-4001"):
        assert client.get(url, headers=auth_header(client, who)).status_code == 403


@pytest.mark.api
def test_editing_keeps_the_previous_version(client, db_session):
    """FR-D5: an edit snapshots the old state and bumps the version."""
    doctor, patient = make_doctor(db_session), make_user(db_session, university_id="STU-2021-375")
    link(db_session, doctor, patient)
    staff = auth_header(client, "DOC-2001")
    record = client.post("/api/medical-records", json=body(patient.id), headers=staff).json()["data"]
    edit = client.patch(f"/api/medical-records/{record['id']}", json={"diagnosis": "Dengue confirmed.", "change_note": "NS1"}, headers=staff)
    assert edit.json()["data"]["version"] == 2
    history = client.get(f"/api/medical-records/{record['id']}/versions", headers=staff).json()["data"]
    assert history[0]["snapshot"]["diagnosis"] == "Viral fever with dehydration."


@pytest.mark.api
def test_only_the_author_may_edit(client, db_session):
    """Clinical accountability stays with the doctor who wrote the entry."""
    doctor, patient = make_doctor(db_session), make_user(db_session, university_id="STU-2021-375")
    colleague = make_doctor(db_session, university_id="DOC-2002")
    link(db_session, doctor, patient)
    link(db_session, colleague, patient)
    record = client.post("/api/medical-records", json=body(patient.id), headers=auth_header(client, "DOC-2001")).json()["data"]
    edit = client.patch(f"/api/medical-records/{record['id']}", json={"notes": "x"}, headers=auth_header(client, "DOC-2002"))
    assert edit.status_code == 403


@pytest.mark.api
def test_views_are_audited_without_clinical_text(client, db_session):
    """NFR-B: every access is logged, but the audit table never holds a diagnosis."""
    doctor, patient = make_doctor(db_session), make_user(db_session, university_id="STU-2021-375")
    link(db_session, doctor, patient)
    record = client.post("/api/medical-records", json=body(patient.id), headers=auth_header(client, "DOC-2001")).json()["data"]
    client.get(f"/api/medical-records/{record['id']}", headers=auth_header(client, "STU-2021-375"))
    entries = db_session.query(AuditLog).filter(AuditLog.entity_type == "medical_record").all()
    assert {e.action for e in entries} >= {"record.create", "record.view"}
    assert all("dehydration" not in (e.summary or "") for e in entries)
