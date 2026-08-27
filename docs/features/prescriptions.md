# Digital Prescription Management

**Owner:** Md Sher Ali (364) · **Requirements:** FR-D1, FR-D3, FR-D4

## What it does

A doctor writes a prescription as a draft, reviews it, then issues it. The
patient sees and prints it. The pharmacist verifies it by reference code and
records the dispensing.

## Lifecycle

```
draft ──► issued ──► dispensed
  │          │
  └──────────┴──► cancelled
```

| Status | Who sees it | Editable |
|---|---|---|
| `draft` | the prescribing doctor only | yes |
| `issued` | doctor, patient, pharmacy | **no** |
| `dispensed` | doctor, patient, pharmacy | no |
| `cancelled` | doctor | no |

A patient requesting a draft gets **404, not 403** — a draft is not yet a
prescription, so its existence is not disclosed.

## Why issuing freezes the medicine list

Once issued, the prescription cannot be edited. If a doctor could change the
medicines after the patient had seen them, the paper the patient holds and the
list the pharmacist reads could disagree, and the patient could be handed
something different from what they were told. To change an issued prescription
the doctor cancels it and writes a new one, which leaves both in the record.

## Medicines are rows, not a text field

`prescription_items` holds one row per medicine with `medicine_name`, `dosage`,
`frequency`, `duration` and `instructions`. A single delimited text field would
be unparseable for the pharmacy screen and impossible to report on.

## Reference codes

Format `RX-YYYYMMDD-NNNNNN`, generated with `secrets.randbelow` and re-drawn on
collision. Short enough to read aloud at the counter, and not sequential, so one
code does not let anyone guess another.

## Separation of duties

A doctor cannot dispense and a pharmacist cannot prescribe. Both are enforced in
the service, not only by hiding buttons. A prescription past its `valid_until`
date is refused at the counter.

## Files

| Layer | Path |
|---|---|
| Models | `backend/app/models/prescription.py` |
| Schemas | `backend/app/schemas/prescription.py` |
| Service | `backend/app/services/prescription_service.py` |
| Controller | `backend/app/controllers/prescription_controller.py` |
| Tests | `backend/tests/test_prescription_service.py`, `test_prescription_api.py` |
| Screens | `frontend/src/features/prescriptions/` |
