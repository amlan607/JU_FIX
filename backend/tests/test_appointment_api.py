"""Endpoint tests for the appointment booking controller (FR-C)."""

from datetime import date, timedelta

import pytest

from app.core.constants import UserRole
from tests.conftest import auth_header, make_doctor, make_user


def next_working_day(offset: int = 1) -> str:
    """Return the next non Friday date as an ISO 8601 string."""
    candidate = date.today() + timedelta(days=offset)
    while candidate.weekday() == 4:
        candidate += timedelta(days=1)
    return candidate.isoformat()


@pytest.mark.api
def test_doctor_list_requires_authentication(client):
    """Every appointment endpoint is behind authentication."""
    assert client.get("/api/appointments/doctors").status_code == 401


@pytest.mark.api
def test_doctor_list_returns_bookable_doctors(client, db_session):
    """FR-C1: the search screen lists doctors with their speciality."""
    make_doctor(db_session, speciality="Paediatrics")
    make_user(db_session, university_id="STU-2021-370")
    headers = auth_header(client, "STU-2021-370")

    response = client.get("/api/appointments/doctors", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"][0]["speciality"] == "Paediatrics"


@pytest.mark.api
def test_availability_returns_the_slot_grid(client, db_session):
    """FR-C1: the slot selection screen receives a full grid."""
    doctor = make_doctor(db_session)
    make_user(db_session, university_id="STU-2021-370")
    headers = auth_header(client, "STU-2021-370")

    response = client.get(
        "/api/appointments/availability",
        params={"doctor_id": doctor.id, "date": next_working_day()},
        headers=headers,
    )

    assert response.status_code == 200
    slots = response.json()["data"]["slots"]
    assert len(slots) > 0
    assert {"start_time", "end_time", "available"} <= slots[0].keys()


@pytest.mark.api
def test_patient_books_an_appointment(client, db_session):
    """FR-C1: a booking returns 201 with the doctor name expanded."""
    doctor = make_doctor(db_session)
    make_user(db_session, university_id="STU-2021-370")
    headers = auth_header(client, "STU-2021-370")

    response = client.post(
        "/api/appointments",
        json={
            "doctor_id": doctor.id,
            "appointment_date": next_working_day(),
            "start_time": "10:00:00",
            "reason": "Persistent fever for three days.",
        },
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["data"]["doctor_name"] == "Dr. Test Doctor"


@pytest.mark.api
def test_double_booking_returns_409(client, db_session):
    """FR-C2 surfaces as an HTTP 409 conflict."""
    doctor = make_doctor(db_session)
    make_user(db_session, university_id="STU-2021-370")
    make_user(db_session, university_id="STU-2021-350")
    when = next_working_day()

    payload = {
        "doctor_id": doctor.id,
        "appointment_date": when,
        "start_time": "10:00:00",
        "reason": "Persistent fever for three days.",
    }

    client.post("/api/appointments", json=payload, headers=auth_header(client, "STU-2021-370"))
    second = client.post(
        "/api/appointments", json=payload, headers=auth_header(client, "STU-2021-350")
    )

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "conflict"


@pytest.mark.api
def test_a_pharmacist_cannot_book(client, db_session):
    """RBAC is enforced on the backend, not by hiding a button."""
    doctor = make_doctor(db_session)
    make_user(db_session, university_id="PHR-3001", role=UserRole.PHARMACIST)
    headers = auth_header(client, "PHR-3001")

    response = client.post(
        "/api/appointments",
        json={
            "doctor_id": doctor.id,
            "appointment_date": next_working_day(),
            "start_time": "10:00:00",
            "reason": "Persistent fever for three days.",
        },
        headers=headers,
    )

    assert response.status_code == 403


@pytest.mark.api
def test_patient_sees_only_their_own_appointments(client, db_session):
    """Ownership scoping is applied in the query, not in the view."""
    doctor = make_doctor(db_session)
    make_user(db_session, university_id="STU-2021-370")
    make_user(db_session, university_id="STU-2021-350")
    when = next_working_day()

    client.post(
        "/api/appointments",
        json={
            "doctor_id": doctor.id,
            "appointment_date": when,
            "start_time": "10:00:00",
            "reason": "Persistent fever for three days.",
        },
        headers=auth_header(client, "STU-2021-370"),
    )

    other = client.get("/api/appointments", headers=auth_header(client, "STU-2021-350"))

    assert other.status_code == 200
    assert other.json()["data"] == []


@pytest.mark.api
def test_reschedule_moves_the_booking(client, db_session):
    """FR-C3: a booking can be moved before the doctor confirms it."""
    doctor = make_doctor(db_session)
    make_user(db_session, university_id="STU-2021-370")
    headers = auth_header(client, "STU-2021-370")
    when = next_working_day()

    created = client.post(
        "/api/appointments",
        json={
            "doctor_id": doctor.id,
            "appointment_date": when,
            "start_time": "10:00:00",
            "reason": "Persistent fever for three days.",
        },
        headers=headers,
    ).json()["data"]

    response = client.patch(
        f"/api/appointments/{created['id']}/reschedule",
        json={"appointment_date": when, "start_time": "11:00:00"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["start_time"] == "11:00:00"


@pytest.mark.api
def test_cancel_sets_the_cancelled_status(client, db_session):
    """FR-C3: cancelling records the status and the reason."""
    doctor = make_doctor(db_session)
    make_user(db_session, university_id="STU-2021-370")
    headers = auth_header(client, "STU-2021-370")

    created = client.post(
        "/api/appointments",
        json={
            "doctor_id": doctor.id,
            "appointment_date": next_working_day(),
            "start_time": "10:00:00",
            "reason": "Persistent fever for three days.",
        },
        headers=headers,
    ).json()["data"]

    response = client.patch(
        f"/api/appointments/{created['id']}/cancel",
        json={"reason": "Feeling better."},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "cancelled"


@pytest.mark.api
def test_a_stranger_cannot_open_another_patients_booking(client, db_session):
    """Direct object access is checked on the backend."""
    doctor = make_doctor(db_session)
    make_user(db_session, university_id="STU-2021-370")
    make_user(db_session, university_id="STU-2021-350")

    created = client.post(
        "/api/appointments",
        json={
            "doctor_id": doctor.id,
            "appointment_date": next_working_day(),
            "start_time": "10:00:00",
            "reason": "Persistent fever for three days.",
        },
        headers=auth_header(client, "STU-2021-370"),
    ).json()["data"]

    response = client.get(
        f"/api/appointments/{created['id']}", headers=auth_header(client, "STU-2021-350")
    )

    assert response.status_code == 403


@pytest.mark.api
def test_doctor_schedule_lists_assigned_bookings(client, db_session):
    """FR-C7: the doctor console lists the day's consultations."""
    doctor = make_doctor(db_session)
    make_user(db_session, university_id="STU-2021-370")
    when = next_working_day()

    client.post(
        "/api/appointments",
        json={
            "doctor_id": doctor.id,
            "appointment_date": when,
            "start_time": "10:00:00",
            "reason": "Persistent fever for three days.",
        },
        headers=auth_header(client, "STU-2021-370"),
    )

    response = client.get(
        "/api/appointments/doctor-schedule",
        params={"date": when},
        headers=auth_header(client, "DOC-2001"),
    )

    assert response.status_code == 200
    assert len(response.json()["data"]) == 1
    assert response.json()["data"][0]["patient_name"] == "Test User"


@pytest.mark.api
def test_booking_a_past_date_returns_400(client, db_session):
    """A past date is a validation error, not a server error."""
    doctor = make_doctor(db_session)
    make_user(db_session, university_id="STU-2021-370")

    response = client.post(
        "/api/appointments",
        json={
            "doctor_id": doctor.id,
            "appointment_date": (date.today() - timedelta(days=2)).isoformat(),
            "start_time": "10:00:00",
            "reason": "Persistent fever for three days.",
        },
        headers=auth_header(client, "STU-2021-370"),
    )

    assert response.status_code == 400
