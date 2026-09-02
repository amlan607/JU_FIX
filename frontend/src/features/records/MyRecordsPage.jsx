/**
 * Patient health record timeline (FR-D3).
 *
 * Route: `/medical-records`. A patient reads their own consultation history and
 * opens any entry for the full clinical detail.
 */
import { useCallback, useEffect, useState } from 'react';

import { EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import FormField from '../../components/FormField';
import StatusChip from '../../components/StatusChip';
import RecordDetailCard from './RecordDetailCard';
import { fetchMyRecords } from './recordApi';
import { RECORD_TYPES, formatVisitDate, recordTypeLabel } from './recordTypes';

export default function MyRecordsPage() {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [openRecord, setOpenRecord] = useState(null);

  const load = useCallback(async (type) => {
    setLoading(true);
    setError('');
    try {
      setRecords(await fetchMyRecords(type || undefined));
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(typeFilter);
  }, [load, typeFilter]);

  return (
    <>
      <div className="ju-page-header">
        <h1>My Medical Records</h1>
        <p>Your consultation history at the JU Medical Centre, newest visit first.</p>
      </div>

      <div className="ju-card">
        <div style={{ maxWidth: '280px', marginBottom: 'var(--ju-space-4)' }}>
          <FormField
            label="Filter by Record Type"
            name="record_type"
            value={typeFilter}
            onChange={(event) => setTypeFilter(event.target.value)}
            options={RECORD_TYPES}
          />
        </div>

        {loading ? (
          <LoadingState message="Loading your medical history…" />
        ) : error ? (
          <ErrorState message={error} onRetry={() => load(typeFilter)} />
        ) : records.length === 0 ? (
          <EmptyState
            title="No medical records yet"
            hint="Entries appear here after a doctor completes a consultation with you."
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
                    alignItems: 'flex-start',
                  }}
                >
                  <div>
                    <h3 style={{ margin: 0 }}>{record.title}</h3>
                    <p className="ju-field__help" style={{ margin: '4px 0 0' }}>
                      {formatVisitDate(record.visit_date)} · {record.doctor_name} ·{' '}
                      {recordTypeLabel(record.record_type)}
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    {record.version > 1 && <StatusChip status="info" label={`v${record.version}`} />}
                    <button
                      type="button"
                      className="ju-btn ju-btn--secondary"
                      onClick={() => setOpenRecord(openRecord?.id === record.id ? null : record)}
                    >
                      {openRecord?.id === record.id ? 'Hide Details' : 'View Details'}
                    </button>
                  </div>
                </div>

                {openRecord?.id === record.id && <RecordDetailCard record={record} />}
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  );
}
