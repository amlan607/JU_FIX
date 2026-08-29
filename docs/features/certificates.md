# Medical Certificate and Sick Leave

**Owner:** Shadman Rahman (376) · **Requirements:** FR-F1 – FR-F4

## What it does

A patient requests a sick leave certificate after a consultation. The treating
doctor approves or rejects it with remarks. An approved certificate is digitally
signed, carries a unique reference ID, and can be verified by anyone holding
that reference.

## A certificate follows a real consultation — FR-F1

The request must reference an appointment that is **completed** and belongs to
the requesting patient. This prevents a certificate for a consultation that was
booked but never attended. Leave also cannot start before the consultation date,
and one certificate covers at most 30 days.

One consultation has at most one open request. A *rejected* request does not
block a resubmission, because the patient may reasonably provide more detail.

## The decision — FR-F2

Only the doctor who conducted the consultation may decide. A rejection **must**
carry remarks, enforced both in the schema and again in the service, so the
patient always learns why.

## The digital signature — FR-F3

On approval the certificate receives:

- a reference ID, `JUMC-YYYY-NNNNNN`
- a signature: `HMAC-SHA256` over the reference ID, the patient's university ID,
  the doctor's university ID, the leave dates and the appointment ID, keyed with
  the application secret

Verification recomputes the HMAC from the stored row and compares it with
`hmac.compare_digest`. If anything covered by the signature has changed — say
the leave end date was edited in the database — the hashes differ and
verification fails. A test does exactly that and asserts the failure.

`compare_digest` is used rather than `==` because it takes constant time,
so comparison timing cannot leak information about the expected value.

## Public verification — FR-F4

`GET /api/certificates/verify?reference=…` is **unauthenticated** by design: a
department office needs to check a certificate a student hands them, and they do
not have a JU_FIX account.

Because it is public, the response is minimal:

| Returned | Not returned |
|---|---|
| valid / not valid | the medical reason |
| patient name and university ID | the diagnosis |
| issuing doctor | the doctor's remarks |
| leave dates and day count | anything clinical |

The office learns that the certificate is genuine and which dates it covers.
It learns nothing about the student's health. Two tests assert this.

## Files

| Layer | Path |
|---|---|
| Model | `backend/app/models/certificate.py` |
| Schemas | `backend/app/schemas/certificate.py` |
| Service | `backend/app/services/certificate_service.py` |
| Controller | `backend/app/controllers/certificate_controller.py` |
| Tests | `backend/tests/test_certificate_service.py`, `test_certificate_api.py` |
| Screens | `frontend/src/features/certificates/` |
