# Appointment Booking and Scheduling

**Owner:** Mir Mohaiminul Islam (350) · **Requirements:** FR-C1 – FR-C3, FR-C7

## What it does

A student or faculty member searches for a doctor, picks a date and a free slot,
gives a reason and books. They can move or cancel the booking until the doctor
confirms it. The doctor then confirms, completes or marks a no-show.

## Slots are derived, not stored

There is no table of slots. `build_slot_grid()` computes the day's slots from
the clinic hours and the doctor's own `consultation_minutes`, then marks each
one taken or free against the existing bookings.

- Clinic hours: 09:00 to 17:00
- Lunch break: 13:00 to 14:00, excluded from the grid
- Friday: closed
- Booking window: up to 30 days ahead, never in the past

A doctor with 20 minute consultations gets 09:00, 09:20, 09:40 …; a doctor with
15 minute consultations gets a finer grid. Changing a doctor's consultation
length takes effect immediately, with no data migration.

## Preventing double booking — FR-C2

Two guards, deliberately:

1. The service checks for an existing active booking in that slot.
2. A **partial unique index** on `(doctor_id, appointment_date, start_time)`
   enforces it in the database.

The service check alone loses a race: two requests can both read "free" before
either writes. The index closes that window, and the service catches the
resulting `IntegrityError` and returns a clean 409.

The index is **partial** — restricted to `status IN ('booked', 'confirmed')`.
A plain unique constraint would permanently reserve a slot that had been
cancelled, which is wrong: a cancelled slot must become available again. A test
covers exactly this (`test_a_cancelled_slot_becomes_bookable_again`), and it is
what caught the original design.

## Status transitions — FR-C7

```
booked ──► confirmed ──► completed
   │            │    └──► no_show
   └──► cancelled ◄──┘
```

Anything outside this map is a 400. A booked appointment cannot jump straight to
completed, because a consultation that was never confirmed did not happen.

## Who may do what

| Action | Who |
|---|---|
| Book | student, faculty |
| Reschedule | the booking patient, while status is `booked` |
| Cancel | the patient (while `booked`), the assigned doctor, an admin |
| Change status | the assigned doctor only |
| Read a booking | the patient, the assigned doctor, an admin |

Once the doctor confirms, the patient can no longer reschedule or cancel
themselves — the doctor has committed the slot. The message tells them to
contact the medical centre rather than failing silently.

## Files

| Layer | Path |
|---|---|
| Model | `backend/app/models/appointment.py` |
| Schemas | `backend/app/schemas/appointment.py` |
| Service | `backend/app/services/appointment_service.py` |
| Controller | `backend/app/controllers/appointment_controller.py` |
| Tests | `backend/tests/test_appointment_service.py`, `test_appointment_api.py` |
| Screens | `frontend/src/features/appointments/` |
