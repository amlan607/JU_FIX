"""Service tests for notification storage and reminder sweeps (FR-H1 to FR-H3)."""

from datetime import date, datetime, time, timedelta, timezone

import pytest

from app.core.constants import AppointmentStatus, PrescriptionStatus
from app.models.appointment import Appointment
from app.models.notification import Notification
from app.models.prescription import Prescription, PrescriptionItem
from app.services import notification_service as service
from tests.conftest import make_doctor, make_user


def make_appointment(db_session, doctor, patient, appointment_date):
    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=appointment_date,
        start_time=time(10, 0),
        end_time=time(10, 20),
        reason="Routine consultation",
        status=AppointmentStatus.BOOKED.value,
    )
    db_session.add(appointment)
    db_session.commit()
    db_session.refresh(appointment)
    return appointment


def make_prescription(db_session, doctor, patient):
    prescription = Prescription(
        reference_code="RX-H370",
        patient_id=patient.id,
        doctor_id=doctor.id,
        diagnosis="Private diagnosis",
        status=PrescriptionStatus.ISSUED.value,
        valid_until=date.today() + timedelta(days=5),
        issued_at=datetime.now(timezone.utc),
    )
    prescription.items.append(
        PrescriptionItem(
            medicine_name="Amoxicillin", dosage="500mg", frequency="1+1+1", duration="7 days"
        )
    )
    db_session.add(prescription)
    db_session.commit()
    return prescription


@pytest.mark.unit
def test_notify_persists_a_notification(db_session):
    user = make_user(db_session)
    notification = service.notify(
        db_session,
        user_id=user.id,
        category="appointment_update",
        title=" Confirmed ",
        body=" Your appointment is confirmed. ",
    )
    assert notification.id is not None
    assert notification.title == "Confirmed"
    assert notification.is_read is False


@pytest.mark.unit
def test_notify_rejects_unknown_categories(db_session):
    user = make_user(db_session)
    with pytest.raises(Exception, match="Unknown notification category"):
        service.notify(db_session, user_id=user.id, category="unknown", title="x", body="y")


@pytest.mark.unit
def test_appointment_reminder_is_idempotent(db_session):
    doctor = make_doctor(db_session)
    patient = make_user(db_session)
    tomorrow = date.today() + timedelta(days=1)
    make_appointment(db_session, doctor, patient, tomorrow)
    now = datetime.combine(tomorrow, time(0), tzinfo=timezone.utc)
    assert service.run_appointment_reminders(db_session, now) == 1
    assert service.run_appointment_reminders(db_session, now) == 0


@pytest.mark.unit
def test_appointment_reminders_skip_cancelled_and_distant_bookings(db_session):
    doctor = make_doctor(db_session)
    patient = make_user(db_session)
    cancelled = make_appointment(db_session, doctor, patient, date.today() + timedelta(days=1))
    cancelled.status = AppointmentStatus.CANCELLED.value
    make_appointment(db_session, doctor, patient, date.today() + timedelta(days=10))
    db_session.commit()
    assert service.run_appointment_reminders(db_session, datetime.now(timezone.utc)) == 0


@pytest.mark.unit
def test_medicine_reminder_avoids_diagnosis_detail(db_session):
    doctor = make_doctor(db_session)
    patient = make_user(db_session)
    make_prescription(db_session, doctor, patient)
    assert service.run_medicine_reminders(db_session) == 1
    notification = db_session.query(Notification).one()
    assert "Private diagnosis" not in notification.body
    assert "Amoxicillin" in notification.body


@pytest.mark.unit
def test_medicine_reminder_is_once_per_day(db_session):
    doctor = make_doctor(db_session)
    patient = make_user(db_session)
    make_prescription(db_session, doctor, patient)
    assert service.run_medicine_reminders(db_session) == 1
    assert service.run_medicine_reminders(db_session) == 0


@pytest.mark.unit
def test_notification_list_is_scoped_and_readable(db_session):
    user = make_user(db_session)
    other = make_user(db_session, university_id="STU-2021-371")
    notification = service.notify(
        db_session, user_id=user.id, category="security", title="Sign in", body="Account accessed."
    )
    assert len(service.list_for_user(db_session, other)["notifications"]) == 0
    service.mark_read(db_session, notification.id, user)
    assert service.list_for_user(db_session, user)["unread_count"] == 0
