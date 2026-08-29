/**
 * Patient certificate list (FR-F1, FR-F3).
 *
 * Route: `/certificates`. Shows the status of every request and gives the
 * printable certificate once a doctor approves it.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

import { Alert, EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import StatusChip from '../../components/StatusChip';
import CertificateDocument from './CertificateDocument';
import { fetchMyCertificates } from './certificateApi';

export default function MyCertificatesPage() {
  const location = useLocation();
  const [certificates, setCertificates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [openId, setOpenId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setCertificates(await fetchMyCertificates());
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <LoadingState message="Loading your certificate requests…" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <>
      <div className="ju-page-header">
        <h1>Medical Certificates</h1>
        <p>Track your sick leave requests and download approved certificates.</p>
      </div>

      <Alert tone="success">{location.state?.message}</Alert>

      <div className="ju-card">
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 'var(--ju-space-3)',
            flexWrap: 'wrap',
            marginBottom: 'var(--ju-space-4)',
          }}
        >
          <h3 className="ju-card__title" style={{ margin: 0 }}>
            Your Requests
          </h3>
          <Link to="/certificates/request" className="ju-btn ju-btn--primary">
            Request Certificate
          </Link>
        </div>

        {certificates.length === 0 ? (
          <EmptyState
            title="No requests yet"
            hint="Request a certificate after a completed consultation."
          />
        ) : (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 'var(--ju-space-3)' }}>
            {certificates.map((certificate) => (
              <li
                key={certificate.id}
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
                    <h3 style={{ margin: 0 }}>
                      {certificate.leave_days} day{certificate.leave_days === 1 ? '' : 's'} leave
                    </h3>
                    <p className="ju-field__help" style={{ margin: '4px 0 0' }}>
                      {certificate.leave_start} to {certificate.leave_end} · reviewed by{' '}
                      {certificate.doctor_name}
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <StatusChip status={certificate.status} />
                    {certificate.status === 'approved' && (
                      <button
                        type="button"
                        className="ju-btn ju-btn--secondary"
                        onClick={() => setOpenId(openId === certificate.id ? null : certificate.id)}
                      >
                        {openId === certificate.id ? 'Hide Certificate' : 'View Certificate'}
                      </button>
                    )}
                  </div>
                </div>

                {certificate.status === 'rejected' && certificate.doctor_remarks && (
                  <Alert tone="error">Doctor&apos;s remarks: {certificate.doctor_remarks}</Alert>
                )}

                {certificate.status === 'submitted' && (
                  <p className="ju-field__help" style={{ marginTop: 'var(--ju-space-3)' }}>
                    Waiting for {certificate.doctor_name} to review this request.
                  </p>
                )}

                {openId === certificate.id && <CertificateDocument certificate={certificate} />}
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
