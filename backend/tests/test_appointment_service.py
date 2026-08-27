"""Unit tests for the appointment booking business rules (FR-C)."""

from datetime import date, time, timedelta

import pytest

from app.core.constants import AppointmentStatus, UserRole
from app.core.errors import ConflictError, PermissionDeniedError, ValidationError
from app.schemas.appointment import BookAppointmentRequest
from app.services import appointment_service
from tests.conftest import make_doctor, make_user


def next_working_day(offset: int = 1) -> date:
    """Return the next non Friday date at least ``offset`` days ahead."""
    candidate = date.today() + timedelta(days=offset)
    while candidate.weekday() == 4:
        candidate += timedelta(days=1)
    return candidate


def booking(doctor_id: int, when: date, start: time = time(10, 0)) -> BookAppointmentRequest:
    """Build a valid booking payload."""
    return BookAppointmentRequest(
        doctor_id=doctor_id,
        appointment_date=when,
        start_time=start,
        reason="Persistent fever and headache for three days.",
    )


@pytest.mark.unit
def test_slot_grid_uses_the_doctor_consultation_length():
    """A 20 minute doctor gets 20 minute slots."""
    grid = appointment_service.build_slot_grid(20)

    assert grid[0] == (time(9, 0), time(9, 20))
    assert grid[1] == (time(9, 20), time(9, 40))


@pytest.mark.unit
def test_slot_grid_excludes_the_lunch_break():
    """No slot may start inside the 13:00 to 14:00 break."""
    starts = [start for start, _ in appointment_service.build_slot_grid(30)]

    assert time(13, 0) not in starts
    assert time(13, 30) not in starts
    assert time(14, 0) in starts


@pytest.mark.unit
def test_slot_grid_stays_inside_opening_hours():
    """The last slot must end by closing time."""
    grid = appointment_service.build_slot_grid(30)

    assert grid[0][0] >= appointment_service.CLINIC_OPENS_AT
    assert grid[-1][1] <= appointment_service.CLINIC_CLOSES_AT


@pytest.mark.unit
def test_slot_grid_rejects_a_non_positive_length():
    """A zero or negative slot length is a configuration error."""
    with pytest.raises(ValidationError):
        appointment_service.build_slot_grid(0)


@pytest.mark.unit
def test_patient_can_book_an_available_slot(db_session):
    """FR-C1: a student books a doctor, date, slot and reason."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-370")

    appointment = appointment_service.book_appointment(
        db_session, patient, booking(doctor.id, next_working_day())
    )

    assert appointment.status == AppointmentStatus.BOOKED.value
    assert appointment.start_time == time(10, 0)
    assert appointment.end_time == time(10, 20)


@pytest.mark.unit
def test_double_booking_the_same_slot_is_refused(db_session):
    """FR-C2: one doctor cannot hold two bookings in the same slot."""
    doctor = make_doctor(db_session)
    first = make_user(db_session, university_id="STU-2021-370")
    second = make_user(db_session, university_id="STU-2021-350")
    when = next_working_day()

    appointment_service.book_appointment(db_session, first, booking(doctor.id, when))

    with pytest.raises(ConflictError):
        appointment_service.book_appointment(db_session, second, booking(doctor.id, when))


@pytest.mark.unit
def test_a_cancelled_slot_becomes_bookable_again(db_session):
    """FR-C2 applies to active bookings only."""
    doctor = make_doctor(db_session)
    first = make_user(db_session, university_id="STU-2021-370")
    second = make_user(db_session, university_id="STU-2021-350")
    when = next_working_day()

    original = appointment_service.book_appointment(db_session, first, booking(doctor.id, when))
    appointment_service.cancel_appointment(db_session, original.id, first, "Recovered.")

    replacement = appointment_service.book_appointment(db_session, second, booking(doctor.id, when))
    assert replacement.status == AppointmentStatus.BOOKED.value


@pytest.mark.unit
def test_booking_in_the_past_is_refused(db_session):
    """A consultation cannot be booked for a date that has passed."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-370")

    with pytest.raises(ValidationError, match="past date"):
        appointment_service.book_appointment(
            db_session, patient, booking(doctor.id, date.today() - timedelta(days=1))
        )


@pytest.mark.unit
def test_booking_too_far_ahead_is_refused(db_session):
    """Bookings are limited to the configured advance window."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-370")
    far_future = date.today() + timedelta(days=appointment_service.MAX_ADVANCE_DAYS + 5)

    with pytest.raises(ValidationError, match="days ahead"):
        appointment_service.book_appointment(db_session, patient, booking(doctor.id, far_future))


@pytest.mark.unit
def test_booking_on_friday_is_refused(db_session):
    """The medical centre is closed on Friday."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-370")

    friday = date.today() + timedelta(days=1)
    while friday.weekday() != 4:
        friday += timedelta(days=1)

    with pytest.raises(ValidationError, match="Friday"):
        appointment_service.book_appointment(db_session, patient, booking(doctor.id, friday))


@pytest.mark.unit
def test_booking_a_time_outside_the_grid_is_refused(db_session):
    """A time that is not a slot boundary is rejected."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-370")

    with pytest.raises(ValidationError, match="consultation slots"):
        appointment_service.book_appointment(
            db_session, patient, booking(doctor.id, next_working_day(), time(10, 7))
        )


@pytest.mark.unit
def test_a_doctor_cannot_book_an_appointment(db_session):
    """FR-C1 restricts booking to student and faculty roles."""
    doctor = make_doctor(db_session)
    other_doctor = make_doctor(db_session, university_id="DOC-2002")

    with pytest.raises(PermissionDeniedError):
        appointment_service.book_appointment(
            db_session, other_doctor, booking(doctor.id, next_working_day())
        )


@pytest.mark.unit
def test_patient_cannot_book_the_same_doctor_twice_in_one_day(db_session):
    """A duplicate same day booking with one doctor is refused."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-370")
    when = next_working_day()

    appointment_service.book_appointment(db_session, patient, booking(doctor.id, when))

    with pytest.raises(ConflictError, match="already have an appointment"):
        appointment_service.book_appointment(db_session, patient, booking(doctor.id, when, time(11, 0)))


@pytest.mark.unit
def test_availability_marks_a_booked_slot_unavailable(db_session):
    """FR-C2 is visible on the slot selection screen."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-370")
    when = next_working_day()

    appointment_service.book_appointment(db_session, patient, booking(doctor.id, when))
    grid = appointment_service.get_available_slots(db_session, doctor.id, when)

    booked = next(slot for slot in grid["slots"] if slot["start_time"] == "10:00")
    assert booked["available"] is False


@pytest.mark.unit
def test_patient_can_reschedule_a_booking(db_session):
    """FR-C3: a booking may be moved before the doctor confirms it."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-370")
    when = next_working_day()
    appointment = appointment_service.book_appointment(db_session, patient, booking(doctor.id, when))

    moved = appointment_service.reschedule_appointment(
        db_session, appointment.id, patient, when, time(11, 0)
    )

    assert moved.start_time == time(11, 0)
    assert moved.end_time == time(11, 20)


@pytest.mark.unit
def test_confirmed_booking_cannot_be_rescheduled_by_the_patient(db_session):
    """FR-C3 allows patient changes only before confirmation."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-370")
    when = next_working_day()
    appointment = appointment_service.book_appointment(db_session, patient, booking(doctor.id, when))

    appointment_service.update_status(db_session, appointment.id, doctor, AppointmentStatus.CONFIRMED)

    with pytest.raises(ValidationError, match="confirmed"):
        appointment_service.reschedule_appointment(
            db_session, appointment.id, patient, when, time(11, 0)
        )


@pytest.mark.unit
def test_rescheduling_into_a_taken_slot_is_refused(db_session):
    """A reschedule cannot create the double booking FR-C2 forbids."""
    doctor = make_doctor(db_session)
    first = make_user(db_session, university_id="STU-2021-370")
    second = make_user(db_session, university_id="STU-2021-350")
    when = next_working_day()

    appointment_service.book_appointment(db_session, first, booking(doctor.id, when, time(10, 0)))
    theirs = appointment_service.book_appointment(
        db_session, second, booking(doctor.id, when, time(11, 0))
    )

    with pytest.raises(ConflictError):
        appointment_service.reschedule_appointment(db_session, theirs.id, second, when, time(10, 0))


@pytest.mark.unit
def test_a_patient_cannot_reschedule_another_patients_booking(db_session):
    """Ownership is enforced on the backend."""
    doctor = make_doctor(db_session)
    owner = make_user(db_session, university_id="STU-2021-370")
    stranger = make_user(db_session, university_id="STU-2021-350")
    when = next_working_day()
    appointment = appointment_service.book_appointment(db_session, owner, booking(doctor.id, when))

    with pytest.raises(PermissionDeniedError):
        appointment_service.reschedule_appointment(
            db_session, appointment.id, stranger, when, time(11, 0)
        )


@pytest.mark.unit
def test_a_stranger_cannot_read_a_booking(db_session):
    """Only the patient, the assigned doctor and an admin may read a booking."""
    doctor = make_doctor(db_session)
    owner = make_user(db_session, university_id="STU-2021-370")
    stranger = make_user(db_session, university_id="STU-2021-350")
    appointment = appointment_service.book_appointment(
        db_session, owner, booking(doctor.id, next_working_day())
    )

    with pytest.raises(PermissionDeniedError):
        appointment_service.get_appointment_for_user(db_session, appointment.id, stranger)


@pytest.mark.unit
def test_admin_can_read_any_booking(db_session):
    """An administrator has oversight of every booking."""
    doctor = make_doctor(db_session)
    owner = make_user(db_session, university_id="STU-2021-370")
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    appointment = appointment_service.book_appointment(
        db_session, owner, booking(doctor.id, next_working_day())
    )

    assert appointment_service.get_appointment_for_user(db_session, appointment.id, admin).id == appointment.id


@pytest.mark.unit
def test_doctor_can_confirm_then_complete(db_session):
    """FR-C7: the assigned doctor advances the booking through its lifecycle."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-370")
    appointment = appointment_service.book_appointment(
        db_session, patient, booking(doctor.id, next_working_day())
    )

    confirmed = appointment_service.update_status(
        db_session, appointment.id, doctor, AppointmentStatus.CONFIRMED
    )
    assert confirmed.status == AppointmentStatus.CONFIRMED.value

    completed = appointment_service.update_status(
        db_session, appointment.id, doctor, AppointmentStatus.COMPLETED
    )
    assert completed.status == AppointmentStatus.COMPLETED.value


@pytest.mark.unit
def test_an_invalid_status_transition_is_refused(db_session):
    """A booked appointment cannot jump straight to completed."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-370")
    appointment = appointment_service.book_appointment(
        db_session, patient, booking(doctor.id, next_working_day())
    )

    with pytest.raises(ValidationError):
        appointment_service.update_status(
            db_session, appointment.id, doctor, AppointmentStatus.COMPLETED
        )


@pytest.mark.unit
def test_an_unassigned_doctor_cannot_change_the_status(db_session):
    """Only the assigned doctor controls the booking."""
    doctor = make_doctor(db_session)
    other = make_doctor(db_session, university_id="DOC-2002")
    patient = make_user(db_session, university_id="STU-2021-370")
    appointment = appointment_service.book_appointment(
        db_session, patient, booking(doctor.id, next_working_day())
    )

    with pytest.raises(PermissionDeniedError):
        appointment_service.update_status(
            db_session, appointment.id, other, AppointmentStatus.CONFIRMED
        )


@pytest.mark.unit
def test_cancelling_twice_is_refused(db_session):
    """A cancelled booking cannot be cancelled again."""
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-370")
    appointment = appointment_service.book_appointment(
        db_session, patient, booking(doctor.id, next_working_day())
    )

    appointment_service.cancel_appointment(db_session, appointment.id, patient)

    with pytest.raises(ValidationError):
        appointment_service.cancel_appointment(db_session, appointment.id, patient)


@pytest.mark.unit
def test_list_doctors_returns_only_active_doctors(db_session):
    """The booking search shows bookable doctors only."""
    make_doctor(db_session, university_id="DOC-2001", speciality="Paediatrics")
    make_user(db_session, university_id="STU-2021-370")

    doctors = appointment_service.list_doctors(db_session)

    assert len(doctors) == 1
    assert doctors[0]["speciality"] == "Paediatrics"


@pytest.mark.unit
def test_list_doctors_filters_by_speciality(db_session):
    """The speciality filter narrows the search results."""
    make_doctor(db_session, university_id="DOC-2001", speciality="Paediatrics")
    make_doctor(db_session, university_id="DOC-2002", speciality="General Medicine")

    assert len(appointment_service.list_doctors(db_session, "paediat")) == 1
