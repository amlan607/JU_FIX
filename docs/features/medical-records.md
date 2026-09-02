# Electronic Health Records

**Owner:** Ziad Muhammad Tahzeeb Rahman (375) · **Requirements:** FR-D2 – FR-D5

## What it does

Stores each consultation as a clinical entry, shows a patient their own history,
lets an authorised doctor read and add entries, and keeps a full version history
of every edit.

## The access rule — FR-D4

**A doctor account is not enough.** Access requires a *treatment relationship*,
which exists when either:

- a non-cancelled appointment links that doctor to that patient, or
- the doctor already authored a record for that patient.

A cancelled appointment grants nothing, because that consultation never happened.

| Who | Access |
|---|---|
| The patient | Their own record, always (FR-D3) |
| A doctor with a relationship | That patient's record |
| A doctor without one | **Denied** |
| An administrator | **Denied** |

Administrators are refused clinical content deliberately. They manage accounts
and read operational counts; diagnoses are not needed for either. This is least
privilege, and a test asserts it (`test_an_admin_cannot_read_clinical_content`).

## Version history — FR-D5

A clinical record must never be silently rewritten. On every edit:

1. The current state is copied into `medical_record_versions`.
2. The new values are written to `medical_records`.
3. `version` increments.

So `medical_records` holds the current state and the versions table holds every
superseded state, each with who edited it, when, and an optional change note.
A record showing "Version 3" has two rows of history behind it.

**Only the authoring doctor may edit an entry.** A colleague with a treatment
relationship can read it but not change it, which keeps clinical accountability
with the person who wrote it.

## Audit trail

Every read and every write is recorded — `record.view`, `record.list`,
`record.create`, `record.update`. The audit entry stores identifiers and the
action, never the diagnosis text. A test asserts that clinical content does not
leak into the audit table.

## Files

| Layer | Path |
|---|---|
| Models | `backend/app/models/medical_record.py` |
| Schemas | `backend/app/schemas/medical_record.py` |
| Service | `backend/app/services/medical_record_service.py` |
| Controller | `backend/app/controllers/medical_record_controller.py` |
| Tests | `backend/tests/test_medical_record_service.py`, `test_medical_record_api.py` |
| Screens | `frontend/src/features/records/` |
