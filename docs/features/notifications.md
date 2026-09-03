# Notifications and Reminders

**Owner:** Oywon Islam (370) · **Requirements:** FR-H1 – FR-H5

## What it does

Notifications are stored for the signed-in user, so reminders and updates remain
available after the user was offline. Other features create messages through the
shared `notification_service.notify()` entry point.

## Reminder sweeps

The reminder job can be run by an administrator or a scheduler through
`POST /api/notifications/run-reminders`.

- Appointment reminders are created 24 hours and 1 hour before booked or
  confirmed appointments.
- Active issued or dispensed prescriptions receive one daily medicine reminder
  until their validity date.
- `reminder_dispatches` claims each appointment offset or prescription day before
  creating a notification. Its unique constraint makes repeated sweeps safe.
- Reminder bodies name the appointment or medicine but do not include a
  prescription diagnosis.

## Notification centre

Authenticated users can list their own notifications with
`GET /api/notifications`, filter to unread items, mark one item read, or mark all
items read. Ownership is enforced in the service layer before a notification is
updated.

## Preferences and mandatory alerts

`GET /api/notifications/preferences` returns every notification category with
separate in-app and email settings. Users can update optional categories with
`PATCH /api/notifications/preferences`. New categories default to enabled.

Security and emergency alerts are always enabled and their settings are locked.
The service checks this rule before reading stored preference rows, so even a
manually inserted opt-out cannot suppress a mandatory alert.

## Files

| Layer | Path |
|---|---|
| Models | `backend/app/models/notification.py`, `prescription.py` |
| Schemas | `backend/app/schemas/notification.py` |
| Service | `backend/app/services/notification_service.py` |
| Controller | `backend/app/controllers/notification_controller.py` |
| Tests | `backend/tests/test_notification_service.py`, `test_notification_api.py` |
| Screens | `frontend/src/features/notifications/` |
