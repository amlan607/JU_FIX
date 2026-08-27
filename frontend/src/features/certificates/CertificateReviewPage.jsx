/**
 * Doctor certificate review queue (FR-F2).
 *
 * Route: `/doctor/certificate-requests`. The treating doctor approves or
 * rejects each request. A rejection must carry remarks.
 */
import { useCallback, useEffect, useState } from 'react';

import { Alert, EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import FormField from '../../components/FormField';
import StatusChip from '../../components/StatusChip';
import { decideCertificate, fetchReviewQueue } from './certificateApi';

export default function CertificateReviewPage() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [banner, setBanner] = useState('');
  const [actionError, setActionError] = useState('');
  const [remarksById, setRemarksById] = useState({});
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      setRequests(await fetchReviewQueue());
    } catch (apiError) {
      setLoadError(apiError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const setRemarks = (id, value) => {
    setRemarksById((previous) => ({ ...previous, [id]: value }));
    setActionError('');
  };

  const decide = async (request, approve) => {
    const remarks = (remarksById[request.id] ?? '').trim();

    if (!approve && !remarks) {
      setActionError('Enter remarks explaining why this request is rejected.');
      return;
    }

    setBusyId(request.id);
    setActionError('');
    try {
      await decideCertificate(request.id, { approve, remarks: remarks || null });
      setBanner(
        approve
          ? `Certificate approved for ${request.patient_name}.`
          : `Request from ${request.patient_name} was rejected.`
      );
      await load();
    } catch (apiError) {
      setActionError(apiError.message);
    } finally {
      setBusyId(null);
    }
  };

  if (loading) return <LoadingState message="Loading certificate requests…" />;
  if (loadError) return <ErrorState message={loadError} onRetry={load} />;

  const pending = requests.filter((request) => request.status === 'submitted');
  const decided = requests.filter((request) => request.status !== 'submitted');

  return (
    <>
      <div className="ju-page-header">
        <h1>Certificate Review</h1>
        <p>Approve or reject sick leave requests from patients you have treated.</p>
      </div>

      <Alert tone="success">{banner}</Alert>
      <Alert tone="error">{actionError}</Alert>

      <div className="ju-card">
        <h3 className="ju-card__title">Awaiting Your Decision ({pending.length})</h3>

        {pending.length === 0 ? (
          <EmptyState
            title="Nothing waiting"
            hint="Requests appear here after a patient asks for a certificate."
          />
        ) : (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 'var(--ju-space-4)' }}>
            {pending.map((request) => (
              <li
                key={request.id}
                style={{
                  border: '1px solid var(--ju-border)',
                  borderRadius: 'var(--ju-radius)',
                  padding: 'var(--ju-space-4)',
                }}
              >
                <h3 style={{ margin: 0 }}>{request.patient_name}</h3>
                <p className="ju-field__help" style={{ margin: '4px 0 var(--ju-space-3)' }}>
                  {request.patient_university_id} · requesting {request.leave_days} day
                  {request.leave_days === 1 ? '' : 's'} from {request.leave_start} to{' '}
                  {request.leave_end}
                </p>

                <p style={{ marginTop: 0 }}>
                  <span className="ju-kpi__label">Patient&apos;s Reason</span>
                  <br />
                  {request.reason}
                </p>

                <FormField
                  label="Your Remarks"
                  name={`remarks_${request.id}`}
                  value={remarksById[request.id] ?? ''}
                  onChange={(event) => setRemarks(request.id, event.target.value)}
                  rows={2}
                  help="Required when rejecting. Optional but recommended when approving."
                />

                <div className="ju-form-actions">
                  <button
                    type="button"
                    className="ju-btn ju-btn--danger"
                    onClick={() => decide(request, false)}
                    disabled={busyId === request.id}
                  >
                    Reject
                  </button>
                  <button
                    type="button"
                    className="ju-btn ju-btn--primary"
                    onClick={() => decide(request, true)}
                    disabled={busyId === request.id}
                  >
                    {busyId === request.id ? 'Saving…' : 'Approve and Sign'}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="ju-card">
        <h3 className="ju-card__title">Decided Requests</h3>

        {decided.length === 0 ? (
          <EmptyState title="No decisions yet" />
        ) : (
          <div className="ju-table-wrap">
            <table className="ju-table">
              <caption className="ju-field__help" style={{ textAlign: 'left', paddingBottom: '8px' }}>
                Certificate requests you have already decided.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Patient</th>
                  <th scope="col">Leave Period</th>
                  <th scope="col">Reference</th>
                  <th scope="col">Remarks</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {decided.map((request) => (
                  <tr key={request.id}>
                    <td>
                      <strong>{request.patient_name}</strong>
                      <br />
                      <span className="ju-field__help">{request.patient_university_id}</span>
                    </td>
                    <td>
                      {request.leave_start} to {request.leave_end}
                    </td>
                    <td>{request.reference_id ?? '—'}</td>
                    <td style={{ maxWidth: '240px' }}>{request.doctor_remarks ?? '—'}</td>
                    <td>
                      <StatusChip status={request.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
