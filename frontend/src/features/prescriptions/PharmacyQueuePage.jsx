/**
 * Pharmacy verification and dispensing console.
 *
 * Route: `/pharmacy/prescriptions`. The pharmacist verifies a prescription by
 * its reference code, checks the medicine list, then records the dispensing.
 */
import { useCallback, useEffect, useState } from 'react';

import { Alert, EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import FormField from '../../components/FormField';
import StatusChip from '../../components/StatusChip';
import MedicineTable from './MedicineTable';
import { dispensePrescription, fetchPharmacyQueue, lookupByReference } from './prescriptionApi';

export default function PharmacyQueuePage() {
  const [queue, setQueue] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [banner, setBanner] = useState('');
  const [actionError, setActionError] = useState('');
  const [code, setCode] = useState('');
  const [lookupResult, setLookupResult] = useState(null);
  const [openId, setOpenId] = useState(null);
  const [note, setNote] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      setQueue(await fetchPharmacyQueue());
    } catch (apiError) {
      setLoadError(apiError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleLookup = async (event) => {
    event.preventDefault();
    setActionError('');
    setLookupResult(null);

    if (!code.trim()) {
      setActionError('Enter the reference code printed on the prescription.');
      return;
    }

    try {
      setLookupResult(await lookupByReference(code.trim()));
    } catch (apiError) {
      setActionError(apiError.message);
    }
  };

  const handleDispense = async (prescription) => {
    setActionError('');
    try {
      await dispensePrescription(prescription.id, note);
      setBanner(`${prescription.reference_code} dispensed to ${prescription.patient_name}.`);
      setNote('');
      setLookupResult(null);
      setCode('');
      await load();
    } catch (apiError) {
      setActionError(apiError.message);
    }
  };

  return (
    <>
      <div className="ju-page-header">
        <h1>Dispensing Queue</h1>
        <p>Verify a prescription by reference code, then record the dispensing.</p>
      </div>

      <Alert tone="success">{banner}</Alert>
      <Alert tone="error">{actionError}</Alert>

      <div className="ju-card">
        <h3 className="ju-card__title">Verify by Reference Code</h3>
        <p className="ju-card__subtitle">
          Ask the patient for the code shown on their prescription, for example RX-20260824-004312.
        </p>

        <form onSubmit={handleLookup} noValidate>
          <div style={{ maxWidth: '340px' }}>
            <FormField
              label="Reference Code"
              name="reference_code"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              required
              placeholder="RX-20260824-004312"
            />
          </div>
          <div className="ju-form-actions">
            <button type="submit" className="ju-btn ju-btn--primary">
              Verify Prescription
            </button>
          </div>
        </form>

        {lookupResult && (
          <div
            style={{
              marginTop: 'var(--ju-space-4)',
              paddingTop: 'var(--ju-space-4)',
              borderTop: '1px solid var(--ju-border)',
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: 'var(--ju-space-3)',
              }}
            >
              <div>
                <h3 style={{ margin: 0 }}>{lookupResult.patient_name}</h3>
                <p className="ju-field__help" style={{ margin: '4px 0 0' }}>
                  {lookupResult.patient_university_id} · prescribed by {lookupResult.doctor_name}
                </p>
              </div>
              <StatusChip status={lookupResult.status} />
            </div>

            <div style={{ marginTop: 'var(--ju-space-4)' }}>
              <MedicineTable items={lookupResult.items} />
            </div>

            {lookupResult.status === 'issued' ? (
              <>
                <div style={{ marginTop: 'var(--ju-space-4)' }}>
                  <FormField
                    label="Counter Note"
                    name="note"
                    value={note}
                    onChange={(event) => setNote(event.target.value)}
                    rows={2}
                    help="Record a substitution or a partial supply if needed."
                  />
                </div>
                <div className="ju-form-actions">
                  <button
                    type="button"
                    className="ju-btn ju-btn--primary"
                    onClick={() => handleDispense(lookupResult)}
                  >
                    Mark as Dispensed
                  </button>
                </div>
              </>
            ) : (
              <Alert tone="warning">
                This prescription was already dispensed on{' '}
                {new Date(lookupResult.dispensed_at).toLocaleString('en-GB')}.
              </Alert>
            )}
          </div>
        )}
      </div>

      <div className="ju-card">
        <h3 className="ju-card__title">Waiting at the Counter</h3>

        {loading ? (
          <LoadingState message="Loading the dispensing queue…" />
        ) : loadError ? (
          <ErrorState message={loadError} onRetry={load} />
        ) : queue.length === 0 ? (
          <EmptyState
            title="Nothing waiting"
            hint="Issued prescriptions appear here as doctors publish them."
          />
        ) : (
          <div className="ju-table-wrap">
            <table className="ju-table">
              <caption className="ju-field__help" style={{ textAlign: 'left', paddingBottom: '8px' }}>
                Issued and recently dispensed prescriptions.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Reference</th>
                  <th scope="col">Patient</th>
                  <th scope="col">Prescribed By</th>
                  <th scope="col">Medicines</th>
                  <th scope="col">Status</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {queue.map((prescription) => (
                  <tr key={prescription.id}>
                    <td>{prescription.reference_code}</td>
                    <td>
                      <strong>{prescription.patient_name}</strong>
                      <br />
                      <span className="ju-field__help">{prescription.patient_university_id}</span>
                    </td>
                    <td>{prescription.doctor_name}</td>
                    <td>{prescription.items.length}</td>
                    <td>
                      <StatusChip status={prescription.status} />
                    </td>
                    <td>
                      <button
                        type="button"
                        className="ju-btn ju-btn--secondary"
                        onClick={() => setOpenId(openId === prescription.id ? null : prescription.id)}
                      >
                        {openId === prescription.id ? 'Hide' : 'View'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {openId && (
              <div style={{ marginTop: 'var(--ju-space-4)' }}>
                <MedicineTable items={queue.find((item) => item.id === openId)?.items ?? []} />
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}
