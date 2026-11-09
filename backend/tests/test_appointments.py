"""Tests for appointment booking and scheduling (FR-C)."""

from datetime import date, timedelta

import pytest

from app.core.constants import UserRole
from tests.conftest import auth_header, make_doctor, make_user


def day(offset: int = 1) -> str:
    """Return the next open (non-Friday) date as ISO 8601."""
    when = date.today() + timedelta(days=offset)
    while when.weekday() == 4:
        when += timedelta(days=1)
    return when.isoformat()


def book(client, doctor, who, when=None, start="10:00:00"):
    """Book a slot as ``who``."""
    body = {"doctor_id": doctor.id, "appointment_date": when or day(), "start_time": start, "reason": "Fever."}
    return client.post("/api/appointments", json=body, headers=auth_header(client, who))


@pytest.mark.api
def test_patient_books_and_sees_the_booking(client, db_session):
    """FR-C1: a booking appears in the patient's own list with the doctor's name."""
    doctor = make_doctor(db_session)
    make_user(db_session, university_id="STU-2021-350")
    assert book(client, doctor, "STU-2021-350").status_code == 201
    listed = client.get("/api/appointments", headers=auth_header(client, "STU-2021-350")).json()["data"]
    assert listed[0]["doctor_name"] == "Dr. Test Doctor"


@pytest.mark.api
def test_double_booking_is_blocked_and_a_cancelled_slot_frees_up(client, db_session):
    """FR-C2: one slot, one patient; cancelling releases it."""
    doctor = make_doctor(db_session)
    make_user(db_session, university_id="STU-2021-350")
    make_user(db_session, university_id="STU-2021-370")
    first = book(client, doctor, "STU-2021-350").json()["data"]
    assert book(client, doctor, "STU-2021-370").status_code == 409
    cancel = client.patch(f"/api/appointments/{first['id']}/cancel", json={}, headers=auth_header(client, "STU-2021-350"))
    assert cancel.status_code == 200
    assert book(client, doctor, "STU-2021-370").status_code == 201


@pytest.mark.api
def test_invalid_dates_and_times_are_rejected(client, db_session):
    """Past dates, Fridays and off-grid times are all 400."""
    doctor = make_doctor(db_session)
    make_user(db_session, university_id="STU-2021-350")
    friday = date.today() + timedelta(days=1)
    while friday.weekday() != 4:
        friday += timedelta(days=1)
    past = (date.today() - timedelta(days=1)).isoformat()
    assert book(client, doctor, "STU-2021-350", when=past).status_code == 400
    assert book(client, doctor, "STU-2021-350", when=friday.isoformat()).status_code == 400
    assert book(client, doctor, "STU-2021-350", start="10:07:00").status_code == 400


@pytest.mark.api
def test_patient_can_reschedule_only_until_the_doctor_confirms(client, db_session):
    """FR-C3: reschedule works while booked and is refused after confirmation."""
    doctor = make_doctor(db_session)
    make_user(db_session, university_id="STU-2021-350")
    appointment = book(client, doctor, "STU-2021-350").json()["data"]
    url, patient = f"/api/appointments/{appointment['id']}", auth_header(client, "STU-2021-350")
    move = {"appointment_date": day(), "start_time": "11:00:00"}
    assert client.patch(f"{url}/reschedule", json=move, headers=patient).json()["data"]["start_time"] == "11:00:00"
    client.patch(f"{url}/status?status=confirmed", headers=auth_header(client, "DOC-2001"))
    assert client.patch(f"{url}/reschedule", json=move, headers=patient).status_code == 400


@pytest.mark.api
def test_doctor_status_flow_and_access_rules(client, db_session):
    """FR-C7: valid transitions pass, jumps fail, and roles are enforced."""
    doctor = make_doctor(db_session)
    make_user(db_session, university_id="STU-2021-350")
    make_user(db_session, university_id="PHR-3001", role=UserRole.PHARMACIST)
    appointment = book(client, doctor, "STU-2021-350").json()["data"]
    url, staff = f"/api/appointments/{appointment['id']}/status", auth_header(client, "DOC-2001")
    assert client.patch(f"{url}?status=completed", headers=staff).status_code == 400
    assert client.patch(f"{url}?status=confirmed", headers=staff).status_code == 200
    assert client.patch(f"{url}?status=completed", headers=staff).json()["data"]["status"] == "completed"
    assert book(client, doctor, "PHR-3001").status_code == 403
    assert client.get("/api/appointments/doctor-schedule", headers=staff).json()["data"][0]["patient_name"]
