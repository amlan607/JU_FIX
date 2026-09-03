import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { Alert, ErrorState, LoadingState } from '../../components/Feedback';
import { fetchPreferences, updatePreference } from './notificationApi';

export default function NotificationPreferencesPage() {
  const [preferences, setPreferences] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [banner, setBanner] = useState('');
  const [busyCategory, setBusyCategory] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setPreferences(await fetchPreferences());
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const toggle = async (preference, channel) => {
    setBusyCategory(preference.category);
    setError('');
    try {
      const payload = { category: preference.category, [channel]: !preference[channel] };
      setPreferences(await updatePreference(payload));
      setBanner(`${preference.label} updated.`);
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setBusyCategory(null);
    }
  };

  if (loading) return <LoadingState message="Loading your preferences..." />;
  if (error && preferences.length === 0) return <ErrorState message={error} onRetry={load} />;

  return (
    <>
      <div className="ju-page-header">
        <h1>Notification Preferences</h1>
        <p><Link to="/notifications">Back to notifications</Link> · Choose what JU_FIX tells you about.</p>
      </div>
      <Alert tone="success">{banner}</Alert>
      <Alert tone="error">{error}</Alert>
      <div className="ju-card">
        <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 'var(--ju-space-3)' }}>
          {preferences.map((preference) => (
            <li key={preference.category} style={{ border: '1px solid var(--ju-border)', borderRadius: 'var(--ju-radius)', padding: 'var(--ju-space-4)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 'var(--ju-space-4)', flexWrap: 'wrap' }}>
                <div style={{ flex: '1 1 260px' }}>
                  <strong>{preference.label}</strong>
                  <p className="ju-field__help" style={{ margin: '4px 0 0' }}>{preference.description}</p>
                  {!preference.can_disable && <p className="ju-field__help" style={{ margin: '4px 0 0' }}>This category cannot be switched off because you must always be told about it.</p>}
                </div>
                <div style={{ display: 'flex', gap: 'var(--ju-space-3)', alignItems: 'center' }}>
                  <label style={{ display: 'flex', gap: '6px', alignItems: 'center', fontSize: 'var(--ju-label)' }}>
                    <input type="checkbox" checked={preference.in_app_enabled} disabled={!preference.can_disable || busyCategory === preference.category} onChange={() => toggle(preference, 'in_app_enabled')} aria-label={`In-app notifications for ${preference.label}`} />
                    In-app
                  </label>
                  <label style={{ display: 'flex', gap: '6px', alignItems: 'center', fontSize: 'var(--ju-label)' }}>
                    <input type="checkbox" checked={preference.email_enabled} disabled={!preference.can_disable || busyCategory === preference.category} onChange={() => toggle(preference, 'email_enabled')} aria-label={`Email notifications for ${preference.label}`} />
                    Email
                  </label>
                </div>
              </div>
            </li>
          ))}
        </ul>
      </div>
    </>
  );
}
