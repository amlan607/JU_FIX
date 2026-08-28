"""Unit tests for the admin dashboard and reporting rules (FR-J1 to FR-J5)."""

from datetime import date, time, timedelta

import pytest

from app.core.constants import AccountStatus, AppointmentStatus, UserRole
from app.core.errors import PermissionDeniedError, ValidationError
from app.models.appointment import Appointment
from app.models.doctor_profile import DoctorProfile
from app.services import admin_service as service
from tests.conftest import make_doctor, make_user


def appointment(
    db_session, doctor, patient, when: date, status: AppointmentStatus = AppointmentStatus.COMPLETED
) -> Appointment:
    """Insert an appointment used to build the reporting figures."""
    row = Appointment(
        patient_id=patient.id,
        doctor_id=doctor.id,
        appointment_date=when,
        start_time=time(10, 0),
        end_time=time(10, 20),
        reason="Routine consultation.",
        status=status.value,
    )
    db_session.add(row)
    db_session.commit()
    return row


@pytest.mark.unit
def test_a_student_cannot_open_the_dashboard(db_session):
    """FR-J: every administrator endpoint is role restricted."""
    student = make_user(db_session, university_id="STU-2021-360")

    with pytest.raises(PermissionDeniedError):
        service.get_dashboard_metrics(db_session, student)


@pytest.mark.unit
def test_a_doctor_cannot_open_the_dashboard(db_session):
    """Clinical roles do not manage the platform."""
    doctor = make_doctor(db_session)

    with pytest.raises(PermissionDeniedError):
        service.list_users(db_session, doctor)


@pytest.mark.unit
def test_pending_registrations_lists_awaiting_accounts(db_session):
    """FR-J1: only accounts awaiting approval appear in the queue."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    make_user(
        db_session,
        university_id="DOC-9001",
        role=UserRole.DOCTOR,
        status=AccountStatus.PENDING_APPROVAL,
    )
    make_user(db_session, university_id="STU-2021-360")

    pending = service.list_pending_registrations(db_session, admin)

    assert len(pending) == 1
    assert pending[0]["university_id"] == "DOC-9001"


@pytest.mark.unit
def test_approving_a_doctor_activates_the_account(db_session):
    """FR-J1: approval makes the account usable."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    doctor = make_user(
        db_session,
        university_id="DOC-9001",
        role=UserRole.DOCTOR,
        status=AccountStatus.PENDING_APPROVAL,
    )

    updated = service.decide_registration(db_session, admin, doctor.id, True, None)

    assert updated.status == AccountStatus.ACTIVE.value


@pytest.mark.unit
def test_approving_a_doctor_creates_a_clinical_profile(db_session):
    """An approved doctor must be bookable straight away."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    doctor = make_user(
        db_session,
        university_id="DOC-9001",
        role=UserRole.DOCTOR,
        status=AccountStatus.PENDING_APPROVAL,
    )

    service.decide_registration(db_session, admin, doctor.id, True, None)

    profile = db_session.query(DoctorProfile).filter(DoctorProfile.user_id == doctor.id).first()
    assert profile is not None


@pytest.mark.unit
def test_rejecting_a_registration_requires_a_reason(db_session):
    """FR-J1: a refusal must be explained."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    doctor = make_user(
        db_session,
        university_id="DOC-9001",
        role=UserRole.DOCTOR,
        status=AccountStatus.PENDING_APPROVAL,
    )

    with pytest.raises(ValidationError, match="reason"):
        service.decide_registration(db_session, admin, doctor.id, False, None)


@pytest.mark.unit
def test_rejection_is_recorded_in_the_audit_trail(db_session):
    """The reason is stored so the decision is traceable."""
    from app.models.audit_log import AuditLog

    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    doctor = make_user(
        db_session,
        university_id="DOC-9001",
        role=UserRole.DOCTOR,
        status=AccountStatus.PENDING_APPROVAL,
    )

    service.decide_registration(db_session, admin, doctor.id, False, "Credentials not verified.")

    entry = db_session.query(AuditLog).filter(AuditLog.action == "registration.reject").first()
    assert "Credentials not verified." in entry.summary


@pytest.mark.unit
def test_an_already_active_account_cannot_be_approved_again(db_session):
    """Only a pending registration can be decided."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    doctor = make_doctor(db_session)

    with pytest.raises(ValidationError, match="not awaiting approval"):
        service.decide_registration(db_session, admin, doctor.id, True, None)


@pytest.mark.unit
def test_suspending_an_account_requires_a_reason(db_session):
    """FR-J2: a suspension must be justified."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    student = make_user(db_session, university_id="STU-2021-360")

    with pytest.raises(ValidationError, match="reason"):
        service.set_account_status(db_session, admin, student.id, True, None)


@pytest.mark.unit
def test_suspend_then_reactivate(db_session):
    """FR-J2: an account can be suspended and later restored."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    student = make_user(db_session, university_id="STU-2021-360")

    suspended = service.set_account_status(db_session, admin, student.id, True, "Policy breach.")
    assert suspended.status == AccountStatus.SUSPENDED.value

    restored = service.set_account_status(db_session, admin, student.id, False, None)
    assert restored.status == AccountStatus.ACTIVE.value


@pytest.mark.unit
def test_an_admin_cannot_suspend_their_own_account(db_session):
    """Guarding against locking the last administrator out."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)

    with pytest.raises(ValidationError, match="your own account"):
        service.set_account_status(db_session, admin, admin.id, True, "Testing.")


@pytest.mark.unit
def test_suspending_an_already_suspended_account_is_refused(db_session):
    """A no-op action is reported rather than silently accepted."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    student = make_user(
        db_session, university_id="STU-2021-360", status=AccountStatus.SUSPENDED
    )

    with pytest.raises(ValidationError, match="already"):
        service.set_account_status(db_session, admin, student.id, True, "Again.")


@pytest.mark.unit
def test_user_list_can_be_filtered_by_role(db_session):
    """FR-J2: the management screen filters by role."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    make_doctor(db_session)
    make_user(db_session, university_id="STU-2021-360")

    doctors = service.list_users(db_session, admin, role=UserRole.DOCTOR.value)

    assert len(doctors) == 1
    assert doctors[0]["role"] == "doctor"


@pytest.mark.unit
def test_user_list_can_be_searched_by_name(db_session):
    """The search box matches names and university IDs."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    make_user(db_session, university_id="STU-2021-360", full_name="Amlan Dutta Rahul")
    make_user(db_session, university_id="STU-2021-370", full_name="Oywon Islam")

    results = service.list_users(db_session, admin, search="amlan")

    assert len(results) == 1
    assert results[0]["full_name"] == "Amlan Dutta Rahul"


@pytest.mark.unit
def test_dashboard_counts_todays_appointments(db_session):
    """FR-J3: the dashboard reports daily appointment volume."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-360")
    appointment(db_session, doctor, patient, date.today())

    metrics = service.get_dashboard_metrics(db_session, admin)

    assert metrics["appointments_today"] == 1
    assert metrics["completed_today"] == 1


@pytest.mark.unit
def test_dashboard_counts_unique_patients(db_session):
    """FR-J3: the daily patient count is distinct, not per appointment."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    doctor = make_doctor(db_session)
    other_doctor = make_doctor(db_session, university_id="DOC-2002")
    patient = make_user(db_session, university_id="STU-2021-360")
    appointment(db_session, doctor, patient, date.today())
    appointment(db_session, other_doctor, patient, date.today())

    metrics = service.get_dashboard_metrics(db_session, admin)

    assert metrics["appointments_today"] == 2
    assert metrics["patients_today"] == 1


@pytest.mark.unit
def test_dashboard_excludes_cancelled_from_the_patient_count(db_session):
    """A cancelled booking means nobody attended."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-360")
    appointment(db_session, doctor, patient, date.today(), AppointmentStatus.CANCELLED)

    metrics = service.get_dashboard_metrics(db_session, admin)

    assert metrics["patients_today"] == 0
    assert metrics["cancelled_today"] == 1


@pytest.mark.unit
def test_dashboard_reports_pending_registrations(db_session):
    """The dashboard surfaces work waiting for the administrator."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    make_user(
        db_session,
        university_id="DOC-9001",
        role=UserRole.DOCTOR,
        status=AccountStatus.PENDING_APPROVAL,
    )

    assert service.get_dashboard_metrics(db_session, admin)["pending_registrations"] == 1


@pytest.mark.unit
def test_doctor_workload_reports_completion_rate(db_session):
    """FR-J3: workload includes how many consultations were completed."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-360")
    today = date.today()
    appointment(db_session, doctor, patient, today, AppointmentStatus.COMPLETED)
    appointment(db_session, doctor, patient, today, AppointmentStatus.NO_SHOW)

    workload = service.get_doctor_workload(db_session, admin, today, today)

    assert workload[0]["total_appointments"] == 2
    assert workload[0]["completed"] == 1
    assert workload[0]["completion_rate"] == 50.0


@pytest.mark.unit
def test_doctor_workload_includes_doctors_with_no_appointments(db_session):
    """An idle doctor still appears, with a zero completion rate."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    make_doctor(db_session)
    today = date.today()

    workload = service.get_doctor_workload(db_session, admin, today, today)

    assert len(workload) == 1
    assert workload[0]["total_appointments"] == 0
    assert workload[0]["completion_rate"] == 0.0


@pytest.mark.unit
def test_daily_volumes_group_by_day(db_session):
    """FR-J3: volume is reported one row per calendar day."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-360")
    today = date.today()
    yesterday = today - timedelta(days=1)
    appointment(db_session, doctor, patient, today)
    appointment(db_session, doctor, patient, yesterday)

    volumes = service.get_daily_volumes(db_session, admin, yesterday, today)

    assert len(volumes) == 2
    assert volumes[0]["day"] == yesterday


@pytest.mark.unit
def test_report_rejects_an_inverted_window(db_session):
    """FR-J4: the reporting window must be valid."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)

    with pytest.raises(ValidationError, match="end date"):
        service.build_analytics_report(
            db_session, admin, date.today(), date.today() - timedelta(days=1)
        )


@pytest.mark.unit
def test_report_rejects_an_over_long_window(db_session):
    """A report is bounded so it cannot exhaust the database."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)

    with pytest.raises(ValidationError, match="at most"):
        service.build_analytics_report(
            db_session,
            admin,
            date.today() - timedelta(days=service.MAX_REPORT_DAYS + 1),
            date.today(),
        )


@pytest.mark.unit
def test_report_totals_match_the_daily_rows(db_session):
    """FR-J4: the summary is consistent with its own detail."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-360")
    today = date.today()
    appointment(db_session, doctor, patient, today)

    report = service.build_analytics_report(db_session, admin, today, today)

    assert report["total_appointments"] == sum(row["total"] for row in report["daily_volumes"])
    assert report["total_patients_seen"] == 1


@pytest.mark.unit
def test_report_csv_contains_the_summary_and_detail_blocks(db_session):
    """FR-J4: the export is a readable CSV."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    doctor = make_doctor(db_session)
    patient = make_user(db_session, university_id="STU-2021-360")
    today = date.today()
    appointment(db_session, doctor, patient, today)

    csv_text = service.report_to_csv(service.build_analytics_report(db_session, admin, today, today))

    assert "Summary" in csv_text
    assert "Daily Appointment Volume" in csv_text
    assert "Doctor Workload" in csv_text


@pytest.mark.unit
def test_settings_fall_back_to_defaults(db_session):
    """FR-J5: an unset value uses the configured default."""
    resolved = service.get_settings_map(db_session)

    assert resolved["daily_token_limit"] == service.DEFAULT_SETTINGS["daily_token_limit"]
    assert set(resolved) == set(service.DEFAULT_SETTINGS)


@pytest.mark.unit
def test_settings_can_be_updated(db_session):
    """FR-J5: an administrator configures token limits and slot duration."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)

    updated = service.update_settings(
        db_session, admin, {"daily_token_limit": 45, "slot_duration_minutes": 15}
    )

    assert updated["daily_token_limit"] == 45
    assert updated["slot_duration_minutes"] == 15


@pytest.mark.unit
def test_updating_a_setting_twice_overwrites_it(db_session):
    """A second change replaces the stored value rather than adding a row."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)
    service.update_settings(db_session, admin, {"daily_token_limit": 45})

    updated = service.update_settings(db_session, admin, {"daily_token_limit": 60})

    assert updated["daily_token_limit"] == 60


@pytest.mark.unit
def test_an_unknown_setting_is_refused(db_session):
    """A typo in a setting name is reported rather than silently stored."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)

    with pytest.raises(ValidationError, match="Unknown setting"):
        service.update_settings(db_session, admin, {"not_a_real_setting": 5})


@pytest.mark.unit
def test_an_empty_settings_update_is_refused(db_session):
    """A request that changes nothing is a validation error."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN)

    with pytest.raises(ValidationError):
        service.update_settings(db_session, admin, {})


@pytest.mark.unit
def test_recent_activity_names_the_actor(db_session):
    """The dashboard feed shows who performed each action."""
    admin = make_user(db_session, university_id="ADM-4001", role=UserRole.ADMIN, full_name="Centre Admin")
    student = make_user(db_session, university_id="STU-2021-360")
    service.set_account_status(db_session, admin, student.id, True, "Policy breach.")

    feed = service.get_recent_activity(db_session, admin)

    assert feed[0]["action"] == "account.suspend"
    assert feed[0]["actor_name"] == "Centre Admin"
