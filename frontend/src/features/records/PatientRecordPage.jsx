/**
 * Doctor view of one patient's health record (FR-D2, FR-D4, FR-D5).
 *
 * Route: `/doctor/patients/:patientId`. Combines the timeline, the add entry
 * form and the version history for the selected entry.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { Alert, EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import StatusChip from '../../components/StatusChip';
import AddRecordForm from './AddRecordForm';
import RecordDetailCard from './RecordDetailCard';
import RecordVersionHistory from './RecordVersionHistory';
import { fetchPatientRecords } from './recordApi';
import { formatVisitDate, recordTypeLabel } from './recordTypes';

export default function PatientRecordPage() {
  const { patientId } = useParams();
  const numericPatientId = Number(patientId);

  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [banner, setBanner] = useState('');
  const [openRecordId, setOpenRecordId] = useState(null);
  const [historyForId, setHistoryForId] = useState(null);
  const [showForm, setShowForm] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setRecords(await fetchPatientRecords(numericPatientId));
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setLoading(false);
    }
  }, [numericPatientId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreated = async () => {
    setBanner('The clinical entry has been added to this record.');
    setShowForm(false);
    await load();
  };

  if (loading) return <LoadingState message="Loading the patient record…" />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  const patientName = records[0]?.patient_name ?? `Patient #${numericPatientId}`;

  return (
    <>
      <div className="ju-page-header">
        <h1>{patientName}</h1>
        <p>
          <Link to="/doctor/patients">Back to patient list</Link> · {records.length} clinical{' '}
          {records.length === 1 ? 'entry' : 'entries'}
        </p>
      </div>

      <Alert tone="success">{banner}</Alert>

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
            Health Record Timeline
          </h3>
          <button
            type="button"
            className="ju-btn ju-btn--primary"
            onClick={() => setShowForm((open) => !open)}
          >
            {showForm ? 'Close Form' : 'Add Clinical Entry'}
          </button>
        </div>

        {showForm && (
          <AddRecordForm patientId={numericPatientId} onCreated={handleCreated} />
        )}

        {records.length === 0 ? (
          <EmptyState
            title="No entries yet"
            hint="Add the first clinical entry after the consultation."
          />
        ) : (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 'var(--ju-space-3)' }}>
            {records.map((record) => (
              <li
                key={record.id}
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
                    <h3 style={{ margin: 0 }}>{record.title}</h3>
                    <p className="ju-field__help" style={{ margin: '4px 0 0' }}>
                      {formatVisitDate(record.visit_date)} · {recordTypeLabel(record.record_type)} ·{' '}
                      {record.doctor_name}
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <StatusChip status="info" label={`Version ${record.version}`} />
                    <button
                      type="button"
                      className="ju-btn ju-btn--secondary"
                      onClick={() => setOpenRecordId(openRecordId === record.id ? null : record.id)}
                    >
                      {openRecordId === record.id ? 'Hide Details' : 'View Details'}
                    </button>
                    <button
                      type="button"
                      className="ju-btn ju-btn--ghost"
                      onClick={() => setHistoryForId(historyForId === record.id ? null : record.id)}
                    >
                      {historyForId === record.id ? 'Hide History' : 'Edit History'}
                    </button>
                  </div>
                </div>

                {openRecordId === record.id && <RecordDetailCard record={record} />}
                {historyForId === record.id && <RecordVersionHistory recordId={record.id} />}
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
