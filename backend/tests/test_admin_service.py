"""Tests for the admin dashboard and reporting (FR-J)."""

from datetime import date, time

import pytest

from app.core.constants import AccountStatus, UserRole
from app.models.appointment import Appointment
from app.models.doctor_profile import DoctorProfile
from tests.conftest import auth_header, make_doctor, make_user


def admin(client, db_session):
    """Create an administrator and return a header for them."""
    make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    return auth_header(client, "ADM-4001")


def appt(db_session, doctor, patient, status="completed"):
    """Insert an appointment for today."""
    db_session.add(Appointment(patient_id=patient.id, doctor_id=doctor.id, appointment_date=date.today(),
                               start_time=time(10, 0), end_time=time(10, 20), reason="x", status=status))
    db_session.commit()


@pytest.mark.api
def test_registration_approval_and_rejection(client, db_session):
    """FR-J1: approval activates and creates a doctor profile; rejection needs a reason."""
    headers = admin(client, db_session)
    doctor = make_user(db_session, university_id="DOC-9", role=UserRole.DOCTOR, status=AccountStatus.PENDING_APPROVAL)
    assert len(client.get("/api/admin/registrations/pending", headers=headers).json()["data"]) == 1
    url = f"/api/admin/registrations/{doctor.id}/decision"
    assert client.patch(url, json={"approve": False}, headers=headers).status_code == 400
    assert client.patch(url, json={"approve": True}, headers=headers).json()["data"]["status"] == "active"
    assert db_session.query(DoctorProfile).filter_by(user_id=doctor.id).first() is not None


@pytest.mark.api
def test_suspension_kills_the_session_and_admins_cannot_suspend_themselves(client, db_session):
    """FR-J2: a suspended user's token stops working at once."""
    headers = admin(client, db_session)
    student = make_user(db_session, university_id="STU-2021-360")
    theirs = auth_header(client, "STU-2021-360")
    assert client.get("/api/admin/users", headers=theirs).status_code == 403  # active, but not an admin
    body = {"suspend": True, "reason": "Policy breach."}
    assert client.patch(f"/api/admin/users/{student.id}/status", json=body, headers=headers).status_code == 200
    assert client.get("/api/admin/users", headers=theirs).status_code == 401  # suspended: session refused
    admin_id = client.get("/api/admin/users", params={"role": "admin"}, headers=headers).json()["data"][0]["id"]
    assert client.patch(f"/api/admin/users/{admin_id}/status", json=body, headers=headers).status_code == 400


@pytest.mark.api
def test_metrics_count_distinct_patients_and_skip_cancellations(client, db_session):
    """FR-J3: one patient seeing two doctors is one patient; cancelled means nobody came."""
    headers = admin(client, db_session)
    first, second = make_doctor(db_session), make_doctor(db_session, university_id="DOC-2002")
    patient, other = make_user(db_session, university_id="STU-2021-360"), make_user(db_session, university_id="STU-2021-370")
    appt(db_session, first, patient)
    appt(db_session, second, patient)
    appt(db_session, first, other, status="cancelled")
    data = client.get("/api/admin/dashboard", headers=headers).json()["data"]["metrics"]
    assert (data["appointments_today"], data["patients_today"], data["cancelled_today"]) == (3, 1, 1)


@pytest.mark.api
def test_report_includes_idle_doctors_and_exports_csv(client, db_session):
    """FR-J3/J4: workload lists every doctor, bad windows fail, and the CSV downloads."""
    headers = admin(client, db_session)
    busy = make_doctor(db_session)
    make_doctor(db_session, university_id="DOC-2002")
    patient = make_user(db_session, university_id="STU-2021-360")
    appt(db_session, busy, patient)
    appt(db_session, busy, patient, status="no_show")
    data = client.get("/api/admin/reports", headers=headers).json()["data"]
    assert len(data["doctor_workload"]) == 2 and data["doctor_workload"][0]["completion_rate"] == 50.0
    assert client.get("/api/admin/reports", params={"start": "2026-02-01", "end": "2026-01-01"}, headers=headers).status_code == 400
    export = client.get("/api/admin/reports/export", headers=headers)
    assert export.headers["content-type"].startswith("text/csv") and "Doctor Workload" in export.text


@pytest.mark.api
def test_settings_are_bounded_and_admin_only(client, db_session):
    """FR-J5: defaults apply, changes persist, out-of-range values and non-admins are refused."""
    headers = admin(client, db_session)
    make_user(db_session, university_id="PHR-3001", role=UserRole.PHARMACIST)
    assert client.get("/api/admin/settings", headers=headers).json()["data"]["daily_token_limit"] == 30
    changed = client.patch("/api/admin/settings", json={"daily_token_limit": 45}, headers=headers)
    assert changed.json()["data"]["daily_token_limit"] == 45
    assert client.patch("/api/admin/settings", json={"daily_token_limit": 5000}, headers=headers).status_code == 400
    assert client.patch("/api/admin/settings", json={"daily_token_limit": 40}, headers=auth_header(client, "PHR-3001")).status_code == 403
