/**
 * Administrator operational dashboard (FR-J3).
 *
 * Route: `/admin/dashboard`. Shows the day's counts, the work waiting for the
 * administrator, and a feed of recent platform activity.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import FormField from '../../components/FormField';
import { fetchDashboard } from './adminApi';

/** KPI cards rendered from the metrics payload, in display order. */
const KPI_CARDS = [
  { key: 'patients_today', label: 'Patients Today', hint: 'Distinct patients with a live booking' },
  { key: 'appointments_today', label: 'Appointments Today', hint: 'All statuses' },
  { key: 'completed_today', label: 'Completed', hint: 'Consultations finished' },
  { key: 'no_show_today', label: 'No-Shows', hint: 'Booked but not attended' },
  { key: 'prescriptions_issued_today', label: 'Prescriptions Issued', hint: 'Published to patients' },
  { key: 'certificates_pending', label: 'Certificates Pending', hint: 'Awaiting a doctor decision' },
  { key: 'pending_registrations', label: 'Pending Registrations', hint: 'Awaiting your approval' },
  { key: 'active_users', label: 'Active Accounts', hint: 'Across all five roles' },
];

/** Today as an ISO 8601 date string. */
function todayIso() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(
    now.getDate()
  ).padStart(2, '0')}`;
}

export default function AdminDashboardPage() {
  const [date, setDate] = useState(todayIso());
  const [metrics, setMetrics] = useState(null);
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async (isoDate) => {
    setLoading(true);
    setError('');
    try {
      const data = await fetchDashboard(isoDate);
      setMetrics(data.metrics);
      setActivity(data.recent_activity);
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(date);
  }, [load, date]);

  if (loading) return <LoadingState message="Loading the operational dashboard…" />;
  if (error) return <ErrorState message={error} onRetry={() => load(date)} />;

  return (
    <>
      <div className="ju-page-header">
        <h1>Admin Dashboard</h1>
        <p>Daily operations across the JU Medical Centre.</p>
      </div>

      <div style={{ maxWidth: '260px', marginBottom: 'var(--ju-space-4)' }}>
        <FormField
          label="Report Date"
          name="date"
          type="date"
          value={date}
          onChange={(event) => setDate(event.target.value)}
        />
      </div>

      <div className="ju-kpi-grid">
        {KPI_CARDS.map((card) => (
          <div key={card.key} className="ju-kpi">
            <span className="ju-kpi__label">{card.label}</span>
            <span className="ju-kpi__value">{metrics?.[card.key] ?? 0}</span>
            <span className="ju-kpi__hint">{card.hint}</span>
          </div>
        ))}
      </div>

      {metrics?.pending_registrations > 0 && (
        <div className="ju-card">
          <h3 className="ju-card__title">Action Needed</h3>
          <p>
            {metrics.pending_registrations} registration
            {metrics.pending_registrations === 1 ? '' : 's'} awaiting your decision.
          </p>
          <Link to="/admin/users" className="ju-btn ju-btn--primary">
            Review Registrations
          </Link>
        </div>
      )}

      <div className="ju-card">
        <h3 className="ju-card__title">Recent Activity</h3>
        <p className="ju-card__subtitle">
          Platform actions recorded in the audit trail. Clinical content is never shown here.
        </p>

        {activity.length === 0 ? (
          <EmptyState title="No recorded activity yet" />
        ) : (
          <div className="ju-table-wrap">
            <table className="ju-table">
              <caption className="ju-field__help" style={{ textAlign: 'left', paddingBottom: '8px' }}>
                The most recent audit entries, newest first.
              </caption>
              <thead>
                <tr>
                  <th scope="col">When</th>
                  <th scope="col">Who</th>
                  <th scope="col">Action</th>
                  <th scope="col">Detail</th>
                </tr>
              </thead>
              <tbody>
                {activity.map((entry) => (
                  <tr key={entry.id}>
                    <td>{new Date(entry.created_at).toLocaleString('en-GB')}</td>
                    <td>{entry.actor_name}</td>
                    <td>{entry.action}</td>
                    <td style={{ maxWidth: '320px' }}>{entry.summary ?? '—'}</td>
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
