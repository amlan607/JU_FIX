# Digital Prescription Management

**Owner:** Md Sher Ali (364) - **Requirements:** FR-D1, FR-D3, FR-D4

## Rules implemented

- Lifecycle draft -> issued -> dispensed. A draft is private to its doctor; a patient asking for one gets 404.
- A doctor can prescribe only for a patient they have an appointment with (FR-D4).
- Medicines are rows in `prescription_items`, not a text blob. Reference codes look like `RX-20260824-004312`.
- Only a pharmacist dispenses, only once, and not after `valid_until`. `record_id` is a plain integer (no FK) so this feature does not depend on EHR.

## Files

`backend/app/` and `frontend/` paths: models/prescription.py, schemas/prescription.py, services/prescription_service.py, controllers/prescription_controller.py, tests/test_prescriptions.py, frontend/src/features/prescriptions/
