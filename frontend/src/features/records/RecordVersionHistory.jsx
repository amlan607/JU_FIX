/**
 * Version history panel for one clinical entry (FR-D5).
 *
 * Shows every superseded state with who edited it and why, so an amended record
 * is fully traceable.
 */
import { useEffect, useState } from 'react';

import { EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import { fetchRecordVersions } from './recordApi';

export default function RecordVersionHistory({ recordId }) {
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchRecordVersions(recordId)
      .then((data) => {
        if (!cancelled) setVersions(data);
      })
      .catch((apiError) => {
        if (!cancelled) setError(apiError.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [recordId]);

  if (loading) return <LoadingState message="Loading edit history…" />;
  if (error) return <ErrorState message={error} />;

  return (
    <div
      style={{
        marginTop: 'var(--ju-space-4)',
        paddingTop: 'var(--ju-space-4)',
        borderTop: '1px solid var(--ju-border)',
      }}
    >
      <h3 className="ju-card__title">Edit History</h3>

      {versions.length === 0 ? (
        <EmptyState
          title="No edits recorded"
          hint="This entry has not been amended since it was created."
        />
      ) : (
        <ol style={{ margin: 0, paddingLeft: 'var(--ju-space-5)', display: 'grid', gap: 'var(--ju-space-3)' }}>
          {versions.map((version) => (
            <li key={version.id}>
              <strong>Version {version.version_number}</strong>
              <p className="ju-field__help" style={{ margin: '2px 0' }}>
                Superseded by an edit from {version.editor_name ?? 'a doctor'} on{' '}
                {new Date(version.created_at).toLocaleString('en-GB')}
              </p>
              {version.change_note && (
                <p style={{ margin: '2px 0' }}>Reason: {version.change_note}</p>
              )}
              <p style={{ margin: '2px 0' }}>
                <span className="ju-kpi__label">Previous diagnosis</span>
                <br />
                {version.diagnosis}
              </p>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
