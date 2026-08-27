# Admin Dashboard and Reporting

**Owner:** Amlan Dutta Rahul (360) · **Requirements:** FR-J1 – FR-J5

## What it does

Approves or rejects doctor, pharmacist and admin registrations; suspends and
reactivates accounts; reports daily patient counts, appointment volumes and
doctor workload; exports the report as CSV; and configures the operational
settings.

## Registration approval — FR-J1

A doctor, pharmacist or admin who has verified their contact sits in
`pending_approval` until an administrator decides.

- **Approve** sets the account to `active`. For a doctor it also creates a
  `DoctorProfile` if one is missing, so the doctor appears in booking search
  immediately rather than being approved but unbookable.
- **Reject** requires a reason, which is written to the audit trail.

## Account management — FR-J2

Suspend or reactivate any account, with a reason required on suspension.
Because `get_current_user` checks account status on every request, a suspended
user's existing session stops working immediately — a test asserts this.

An administrator **cannot change their own status**. Without that guard a single
administrator could suspend themselves and lock everyone out of the admin area
permanently.

## Reporting — FR-J3, FR-J4

The dashboard reports daily counts. `patients_today` counts **distinct**
patients, not appointments, so one student seeing two doctors is one patient.
Cancelled bookings are excluded from the patient count, because nobody attended.

Doctor workload includes doctors with **zero** appointments, via an outer join.
An idle doctor is exactly the thing a workload report should surface, and an
inner join would hide them.

The CSV export returns a file rather than the JSON envelope, since the browser
downloads it directly. Reports are bounded to 365 days so one request cannot
scan the whole table.

## Operational settings — FR-J5

`daily_token_limit`, `slot_duration_minutes`, `reminder_hours_before` and
`max_advance_booking_days` live in a key/value table, so adding a setting needs
no schema migration. Unset values fall back to the configured defaults, and each
is range-bounded in the schema.

## What the administrator cannot see

This service returns **counts and workload only**. No diagnoses, no prescription
contents, no certificate reasons. Managing the platform does not require reading
anyone's medical history, and the EHR service refuses admin access outright.

## Files

| Layer | Path |
|---|---|
| Model | `backend/app/models/system_setting.py` |
| Schemas | `backend/app/schemas/admin.py` |
| Service | `backend/app/services/admin_service.py` |
| Controller | `backend/app/controllers/admin_controller.py` |
| Tests | `backend/tests/test_admin_service.py`, `test_admin_api.py` |
| Screens | `frontend/src/features/admin/` |
