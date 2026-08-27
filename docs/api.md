# API Reference

Base path: `/api`. Interactive documentation generated from the code is at
`/api/docs` while the server is running.

## Response envelope

Every JSON endpoint returns:

```json
{ "success": true,  "data": { }, "error": null }
{ "success": false, "data": null, "error": { "code": "…", "message": "…", "details": null } }
```

The one exception is `GET /api/admin/reports/export`, which returns a CSV file
because the browser downloads it directly.

## Authentication

Send the JWT from login on every protected request:

```
Authorization: Bearer <access_token>
```

## Accounts and Authentication — FR-A

| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | `/auth/register` | public | Create an account |
| POST | `/auth/verify-account` | public | Activate with a verification token |
| POST | `/auth/login` | public | Authenticate and receive a JWT |
| POST | `/auth/logout` | any | Revoke the current session |
| POST | `/auth/forgot-password` | public | Start a password reset |
| POST | `/auth/reset-password` | public | Complete a password reset |
| GET | `/auth/me` | any | Read own profile |
| PATCH | `/auth/me` | any | Edit own profile |

## Appointment Booking — FR-C

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/appointments/doctors` | any | List bookable doctors |
| GET | `/appointments/availability` | any | Slot grid for a doctor on a date |
| POST | `/appointments` | student, faculty | Book a slot |
| GET | `/appointments` | student, faculty | Own bookings |
| GET | `/appointments/doctor-schedule` | doctor | Assigned consultations |
| GET | `/appointments/{id}` | patient, assigned doctor, admin | One booking |
| PATCH | `/appointments/{id}/reschedule` | student, faculty | Move to another slot |
| PATCH | `/appointments/{id}/cancel` | patient, doctor, admin | Cancel |
| PATCH | `/appointments/{id}/status` | assigned doctor | Confirm, complete, no-show |

## Electronic Health Records — FR-D2 to FR-D5

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/medical-records/my-records` | student, faculty | Own timeline |
| GET | `/medical-records/patients` | doctor | Authorised patients |
| GET | `/medical-records/patients/{id}` | patient, authorised doctor | Patient timeline |
| POST | `/medical-records` | doctor | Add a clinical entry |
| GET | `/medical-records/{id}` | patient, authorised doctor | One entry |
| PATCH | `/medical-records/{id}` | authoring doctor | Edit, creating a version |
| GET | `/medical-records/{id}/versions` | patient, authorised doctor | Edit history |

## Digital Prescriptions — FR-D1, FR-D3

| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | `/prescriptions` | doctor | Create a draft |
| GET | `/prescriptions/my-prescriptions` | student, faculty | Own issued prescriptions |
| GET | `/prescriptions/written` | doctor | Prescriptions the doctor wrote |
| GET | `/prescriptions/pharmacy-queue` | pharmacist | Dispensing queue |
| GET | `/prescriptions/lookup` | pharmacist | Find by reference code |
| GET | `/prescriptions/{id}` | patient, author, pharmacist | One prescription |
| PATCH | `/prescriptions/{id}` | author | Edit a draft |
| PATCH | `/prescriptions/{id}/issue` | author | Publish to patient and pharmacy |
| PATCH | `/prescriptions/{id}/cancel` | author | Cancel before dispensing |
| PATCH | `/prescriptions/{id}/dispense` | pharmacist | Record dispensing |

## Medical Certificates — FR-F

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/certificates/verify` | **public** | Verify by reference ID |
| POST | `/certificates` | student, faculty | Request after a consultation |
| GET | `/certificates` | student, faculty | Own requests |
| GET | `/certificates/review-queue` | doctor | Requests to decide |
| GET | `/certificates/{id}` | patient, treating doctor | One request |
| PATCH | `/certificates/{id}/decision` | treating doctor | Approve or reject |

## Admin Dashboard and Reporting — FR-J

| Method | Path | Roles | Purpose |
|---|---|---|---|
| GET | `/admin/dashboard` | admin | Daily metrics and activity feed |
| GET | `/admin/registrations/pending` | admin | Approval queue |
| PATCH | `/admin/registrations/{id}/decision` | admin | Approve or reject |
| GET | `/admin/users` | admin | Account list with filters |
| PATCH | `/admin/users/{id}/status` | admin | Suspend or reactivate |
| GET | `/admin/reports` | admin | Analytics report |
| GET | `/admin/reports/export` | admin | Download the report as CSV |
| GET | `/admin/settings` | admin | Read operational settings |
| PATCH | `/admin/settings` | admin | Change operational settings |

## Status codes

| Code | Meaning |
|---|---|
| 200 | Success |
| 201 | Created |
| 400 | Validation failure |
| 401 | Not authenticated, or session revoked or expired |
| 403 | Authenticated but not permitted |
| 404 | Not found |
| 409 | Conflict, for example a double booking |
| 500 | Unexpected server error |
