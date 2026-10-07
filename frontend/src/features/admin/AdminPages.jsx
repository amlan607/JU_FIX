/** Admin screens: dashboard, user management, reports and settings (FR-J1 to FR-J5). */
import { useCallback, useState } from 'react';

import Async from '../../components/Async';
import { Alert, EmptyState } from '../../components/Feedback';
import FormField from '../../components/FormField';
import StatusChip from '../../components/StatusChip';
import { api } from '../../services/apiClient';
import { useLoad } from '../../services/hooks';

const fetchDashboard = () => api.get('/admin/dashboard');
const fetchPending = () => api.get('/admin/registrations/pending');
const fetchUsers = () => api.get('/admin/users');
const fetchReport = () => api.get('/admin/reports');
const fetchSettings = () => api.get('/admin/settings');

const KPIS = [['appointments_today', 'Appointments Today'], ['patients_today', 'Patients Today'],
  ['completed_today', 'Completed'], ['pending_registrations', 'Pending Registrations'], ['active_users', 'Active Accounts']];

/** Run an API action and report the outcome. */
function useNote(reload) {
  const [note, setNote] = useState({ tone: 'info', text: '' });
  const run = async (action, text) => {
    try {
      await action();
      setNote({ tone: 'success', text });
      reload();
    } catch (err) {
      setNote({ tone: 'error', text: err.message });
    }
  };
  return [note, run];
}

export function DashboardPage() {
  const dashboard = useLoad(fetchDashboard);
  const pending = useLoad(fetchPending);
  const [note, run] = useNote(() => { pending.reload(); dashboard.reload(); });
  const decide = (u, approve) => {
    const reason = approve ? null : window.prompt('Reason for rejecting?');
    if (approve || reason) run(() => api.patch(`/admin/registrations/${u.id}/decision`, { approve, reason }), 'Decision saved.');
  };
  return (
    <>
      <h1>Admin Dashboard</h1>
      <Alert tone={note.tone}>{note.text}</Alert>
      <Async state={dashboard}>
        {(d) => (
          <div className="ju-kpi-grid">
            {KPIS.map(([key, label]) => (
              <div key={key} className="ju-kpi"><span className="ju-kpi__label">{label}</span><span className="ju-kpi__value">{d.metrics[key]}</span></div>
            ))}
          </div>
        )}
      </Async>
      <h2>Pending Registrations</h2>
      <Async state={pending}>
        {(rows) => rows.length === 0 ? <EmptyState title="Nothing waiting" /> : rows.map((u) => (
          <div key={u.id} className="ju-card">
            {u.full_name} ({u.university_id}) applying as {u.role}
            <button type="button" className="ju-btn ju-btn--danger" onClick={() => decide(u, false)}>Reject</button>
            <button type="button" className="ju-btn ju-btn--primary" onClick={() => decide(u, true)}>Approve</button>
          </div>
        ))}
      </Async>
    </>
  );
}

export function UsersPage() {
  const users = useLoad(fetchUsers);
  const [note, run] = useNote(users.reload);
  const toggle = (u) => {
    const suspend = u.status === 'active';
    const reason = suspend ? window.prompt('Reason for suspending?') : null;
    if (!suspend || reason) run(() => api.patch(`/admin/users/${u.id}/status`, { suspend, reason }), 'Account updated.');
  };
  return (
    <>
      <h1>User Management</h1>
      <Alert tone={note.tone}>{note.text}</Alert>
      <Async state={users}>
        {(rows) => (
          <table className="ju-table">
            <tbody>
              {rows.map((u) => (
                <tr key={u.id}>
                  <td>{u.full_name}</td><td>{u.university_id}</td><td>{u.role}</td><td><StatusChip status={u.status} /></td>
                  <td>{['active', 'suspended'].includes(u.status) && <button type="button" className="ju-btn ju-btn--secondary" onClick={() => toggle(u)}>{u.status === 'active' ? 'Suspend' : 'Reactivate'}</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Async>
    </>
  );
}

export function ReportsPage() {
  const report = useLoad(fetchReport);
  const settings = useLoad(fetchSettings);
  const [token, setToken] = useState('');
  const [note, run] = useNote(settings.reload);
  const save = useCallback(() => run(() => api.patch('/admin/settings', { daily_token_limit: Number(token) }), 'Settings saved.'), [token]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <>
      <h1>Reports</h1>
      <Alert tone={note.tone}>{note.text}</Alert>
      <a className="ju-btn ju-btn--secondary" href="/api/admin/reports/export" download>Export CSV</a>
      <Async state={report}>
        {(r) => (
          <table className="ju-table">
            <thead><tr><th>Doctor</th><th>Total</th><th>Completed</th><th>Rate</th></tr></thead>
            <tbody>{r.doctor_workload.map((w) => <tr key={w.doctor_id}><td>{w.doctor_name}</td><td>{w.total}</td><td>{w.completed}</td><td>{w.completion_rate}%</td></tr>)}</tbody>
          </table>
        )}
      </Async>
      <Async state={settings}>
        {(s) => (
          <div className="ju-card">
            <FormField label={`Daily Token Limit (now ${s.daily_token_limit})`} type="number" name="token" value={token} onChange={(e) => setToken(e.target.value)} />
            <button type="button" className="ju-btn ju-btn--primary" onClick={save} disabled={!token}>Save Settings</button>
          </div>
        )}
      </Async>
    </>
  );
}
