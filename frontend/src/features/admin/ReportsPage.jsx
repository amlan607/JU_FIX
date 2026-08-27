/**
 * Reporting and platform settings (FR-J3, FR-J4, FR-J5).
 *
 * Route: `/admin/reports`. Generates the analytics report for a chosen window,
 * offers the CSV export, and edits the operational settings.
 */
import { useCallback, useEffect, useState } from 'react';

import { Alert, EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import FormField from '../../components/FormField';
import { fetchReport, fetchSettings, reportExportUrl, updateSettings } from './adminApi';

/** Settings the administrator may change, with the label shown on the form. */
const SETTING_FIELDS = [
  { key: 'daily_token_limit', label: 'Daily Token Limit', help: 'Tokens issued per doctor per day.' },
  { key: 'slot_duration_minutes', label: 'Default Slot Duration (minutes)', help: 'Used for new doctors.' },
  { key: 'reminder_hours_before', label: 'Reminder Lead Time (hours)', help: 'How early to remind a patient.' },
  { key: 'max_advance_booking_days', label: 'Booking Window (days)', help: 'How far ahead a patient may book.' },
];

/** An ISO date `days` before today. */
function isoDaysAgo(days) {
  const value = new Date();
  value.setDate(value.getDate() - days);
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(
    value.getDate()
  ).padStart(2, '0')}`;
}

export default function ReportsPage() {
  const [range, setRange] = useState({ start: isoDaysAgo(29), end: isoDaysAgo(0) });
  const [report, setReport] = useState(null);
  const [settings, setSettings] = useState(null);
  const [settingsDraft, setSettingsDraft] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [banner, setBanner] = useState('');
  const [savingSettings, setSavingSettings] = useState(false);

  const load = useCallback(async (window) => {
    setLoading(true);
    setError('');
    try {
      const [generated, current] = await Promise.all([
        fetchReport(window.start, window.end),
        fetchSettings(),
      ]);
      setReport(generated);
      setSettings(current);
      setSettingsDraft(current);
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(range);
  }, [load, range]);

  const saveSettings = async (event) => {
    event.preventDefault();
    setSavingSettings(true);
    setError('');
    try {
      const changed = Object.fromEntries(
        Object.entries(settingsDraft)
          .filter(([key, value]) => Number(value) !== Number(settings[key]))
          .map(([key, value]) => [key, Number(value)])
      );

      if (Object.keys(changed).length === 0) {
        setBanner('No settings were changed.');
        return;
      }

      const updated = await updateSettings(changed);
      setSettings(updated);
      setSettingsDraft(updated);
      setBanner('Operational settings updated.');
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setSavingSettings(false);
    }
  };

  if (loading) return <LoadingState message="Generating the report…" />;
  if (error && !report) return <ErrorState message={error} onRetry={() => load(range)} />;

  return (
    <>
      <div className="ju-page-header">
        <h1>Reports</h1>
        <p>Platform analytics for a chosen period, and the operational settings.</p>
      </div>

      <Alert tone="success">{banner}</Alert>
      <Alert tone="error">{error}</Alert>

      <div className="ju-card">
        <h3 className="ju-card__title">Reporting Period</h3>

        <div className="ju-form-grid">
          <FormField
            label="Start Date"
            name="start"
            type="date"
            value={range.start}
            onChange={(event) => setRange({ ...range, start: event.target.value })}
          />
          <FormField
            label="End Date"
            name="end"
            type="date"
            value={range.end}
            onChange={(event) => setRange({ ...range, end: event.target.value })}
          />
        </div>

        <div className="ju-form-actions">
          <a
            className="ju-btn ju-btn--secondary"
            href={reportExportUrl(range.start, range.end)}
            download
          >
            Export as CSV
          </a>
        </div>
      </div>

      <div className="ju-kpi-grid">
        <div className="ju-kpi">
          <span className="ju-kpi__label">Total Appointments</span>
          <span className="ju-kpi__value">{report?.total_appointments ?? 0}</span>
          <span className="ju-kpi__hint">All statuses in the period</span>
        </div>
        <div className="ju-kpi">
          <span className="ju-kpi__label">Patients Seen</span>
          <span className="ju-kpi__value">{report?.total_patients_seen ?? 0}</span>
          <span className="ju-kpi__hint">Distinct completed consultations</span>
        </div>
        <div className="ju-kpi">
          <span className="ju-kpi__label">Prescriptions Issued</span>
          <span className="ju-kpi__value">{report?.total_prescriptions ?? 0}</span>
          <span className="ju-kpi__hint">Published to patients</span>
        </div>
        <div className="ju-kpi">
          <span className="ju-kpi__label">Certificates Approved</span>
          <span className="ju-kpi__value">{report?.total_certificates_approved ?? 0}</span>
          <span className="ju-kpi__hint">Signed and issued</span>
        </div>
      </div>

      <div className="ju-card">
        <h3 className="ju-card__title">Doctor Workload</h3>

        {(report?.doctor_workload ?? []).length === 0 ? (
          <EmptyState title="No doctors to report on" />
        ) : (
          <div className="ju-table-wrap">
            <table className="ju-table">
              <caption className="ju-field__help" style={{ textAlign: 'left', paddingBottom: '8px' }}>
                Consultations per doctor between {report.start_date} and {report.end_date}.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Doctor</th>
                  <th scope="col">Speciality</th>
                  <th scope="col">Total</th>
                  <th scope="col">Completed</th>
                  <th scope="col">Cancelled</th>
                  <th scope="col">No-Show</th>
                  <th scope="col">Completion Rate</th>
                </tr>
              </thead>
              <tbody>
                {report.doctor_workload.map((row) => (
                  <tr key={row.doctor_id}>
                    <td>
                      <strong>{row.doctor_name}</strong>
                    </td>
                    <td>{row.speciality ?? '—'}</td>
                    <td>{row.total_appointments}</td>
                    <td>{row.completed}</td>
                    <td>{row.cancelled}</td>
                    <td>{row.no_show}</td>
                    <td>{row.completion_rate}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="ju-card">
        <h3 className="ju-card__title">Daily Appointment Volume</h3>

        {(report?.daily_volumes ?? []).length === 0 ? (
          <EmptyState
            title="No appointments in this period"
            hint="Choose a wider date range."
          />
        ) : (
          <div className="ju-table-wrap">
            <table className="ju-table">
              <caption className="ju-field__help" style={{ textAlign: 'left', paddingBottom: '8px' }}>
                One row per day that had at least one appointment.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  <th scope="col">Total</th>
                  <th scope="col">Completed</th>
                  <th scope="col">Cancelled</th>
                  <th scope="col">No-Show</th>
                  <th scope="col">Unique Patients</th>
                </tr>
              </thead>
              <tbody>
                {report.daily_volumes.map((row) => (
                  <tr key={row.day}>
                    <td>{row.day}</td>
                    <td>{row.total}</td>
                    <td>{row.completed}</td>
                    <td>{row.cancelled}</td>
                    <td>{row.no_show}</td>
                    <td>{row.unique_patients}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="ju-card">
        <h3 className="ju-card__title">Operational Settings</h3>
        <p className="ju-card__subtitle">
          These values control token limits, slot length, reminders and the booking window.
        </p>

        <form onSubmit={saveSettings} noValidate>
          <div className="ju-form-grid">
            {SETTING_FIELDS.map((field) => (
              <FormField
                key={field.key}
                label={field.label}
                name={field.key}
                type="number"
                value={settingsDraft?.[field.key] ?? ''}
                onChange={(event) =>
                  setSettingsDraft({ ...settingsDraft, [field.key]: event.target.value })
                }
                help={field.help}
              />
            ))}
          </div>

          <div className="ju-form-actions">
            <button type="submit" className="ju-btn ju-btn--primary" disabled={savingSettings}>
              {savingSettings ? 'Saving…' : 'Save Settings'}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
