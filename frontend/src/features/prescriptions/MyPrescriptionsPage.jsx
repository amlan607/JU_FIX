/**
 * Patient prescription list (FR-D3).
 *
 * Route: `/prescriptions`. A patient views and prints the prescriptions their
 * doctor has issued. Drafts are never returned by the API.
 */
import { useCallback, useEffect, useState } from 'react';

import { EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import StatusChip from '../../components/StatusChip';
import MedicineTable from './MedicineTable';
import { fetchMyPrescriptions } from './prescriptionApi';

/**
 * Format an ISO timestamp for display.
 * @param {string} value An ISO 8601 timestamp.
 * @returns {string} A readable date, or a dash when absent.
 */
function formatIssued(value) {
  return value ? new Date(value).toLocaleDateString('en-GB') : '—';
}

export default function MyPrescriptionsPage() {
  const [prescriptions, setPrescriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [openId, setOpenId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setPrescriptions(await fetchMyPrescriptions());
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <LoadingState message="Loading your prescriptions…" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <>
      <div className="ju-page-header">
        <h1>My Prescriptions</h1>
        <p>Prescriptions issued to you by the JU Medical Centre doctors.</p>
      </div>

      <div className="ju-card">
        {prescriptions.length === 0 ? (
          <EmptyState
            title="No prescriptions yet"
            hint="A prescription appears here once your doctor issues it."
          />
        ) : (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 'var(--ju-space-3)' }}>
            {prescriptions.map((prescription) => (
              <li
                key={prescription.id}
                style={{
                  border: '1px solid var(--ju-border)',
                  borderRadius: 'var(--ju-radius)',
                  padding: 'var(--ju-space-4)',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: 'var(--ju-space-3)',
                    flexWrap: 'wrap',
                  }}
                >
                  <div>
                    <h3 style={{ margin: 0 }}>{prescription.diagnosis}</h3>
                    <p className="ju-field__help" style={{ margin: '4px 0 0' }}>
                      {prescription.reference_code} · issued {formatIssued(prescription.issued_at)} by{' '}
                      {prescription.doctor_name}
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <StatusChip status={prescription.status} />
                    <button
                      type="button"
                      className="ju-btn ju-btn--secondary"
                      onClick={() => setOpenId(openId === prescription.id ? null : prescription.id)}
                    >
                      {openId === prescription.id ? 'Hide Medicines' : 'View Medicines'}
                    </button>
                  </div>
                </div>

                {openId === prescription.id && (
                  <div style={{ marginTop: 'var(--ju-space-4)' }}>
                    <MedicineTable items={prescription.items} />

                    {prescription.advice && (
                      <p style={{ marginTop: 'var(--ju-space-3)' }}>
                        <span className="ju-kpi__label">Advice</span>
                        <br />
                        {prescription.advice}
                      </p>
                    )}

                    <p className="ju-field__help" style={{ marginTop: 'var(--ju-space-3)' }}>
                      Valid until {prescription.valid_until ?? 'not specified'}. Show the reference
                      code at the pharmacy counter.
                    </p>

                    <div className="ju-form-actions">
                      <button
                        type="button"
                        className="ju-btn ju-btn--secondary"
                        onClick={() => window.print()}
                      >
                        Print or Save as PDF
                      </button>
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
