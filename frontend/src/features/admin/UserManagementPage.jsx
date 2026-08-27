/**
 * User management screen (FR-J1, FR-J2).
 *
 * Route: `/admin/users`. Combines the registration approval queue with the
 * full account list, since an administrator works both in the same sitting.
 */
import { useCallback, useEffect, useState } from 'react';

import { Alert, EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import FormField from '../../components/FormField';
import StatusChip from '../../components/StatusChip';
import { decideRegistration, fetchPendingRegistrations, fetchUsers, setAccountStatus } from './adminApi';

const ROLE_OPTIONS = [
  { value: 'student', label: 'Student' },
  { value: 'faculty', label: 'Faculty or Staff' },
  { value: 'doctor', label: 'Doctor' },
  { value: 'pharmacist', label: 'Pharmacist' },
  { value: 'admin', label: 'Administrator' },
];

const STATUS_OPTIONS = [
  { value: 'active', label: 'Active' },
  { value: 'pending_verification', label: 'Pending Verification' },
  { value: 'pending_approval', label: 'Pending Approval' },
  { value: 'suspended', label: 'Suspended' },
];

export default function UserManagementPage() {
  const [pending, setPending] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [banner, setBanner] = useState('');
  const [actionError, setActionError] = useState('');
  const [reasons, setReasons] = useState({});
  const [busyId, setBusyId] = useState(null);
  const [filters, setFilters] = useState({ role: '', status: '', search: '' });

  const load = useCallback(async (activeFilters) => {
    setLoading(true);
    setLoadError('');
    try {
      const [queue, accounts] = await Promise.all([
        fetchPendingRegistrations(),
        fetchUsers({
          role: activeFilters.role || undefined,
          status: activeFilters.status || undefined,
          search: activeFilters.search || undefined,
        }),
      ]);
      setPending(queue);
      setUsers(accounts);
    } catch (apiError) {
      setLoadError(apiError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(filters);
  }, [load, filters]);

  const setReason = (id, value) => {
    setReasons((previous) => ({ ...previous, [id]: value }));
    setActionError('');
  };

  const decide = async (registration, approve) => {
    const reason = (reasons[registration.user_id] ?? '').trim();

    if (!approve && !reason) {
      setActionError('Enter a reason before rejecting this registration.');
      return;
    }

    setBusyId(registration.user_id);
    setActionError('');
    try {
      await decideRegistration(registration.user_id, { approve, reason: reason || null });
      setBanner(
        approve
          ? `${registration.full_name} has been approved and can now sign in.`
          : `${registration.full_name}'s registration was rejected.`
      );
      await load(filters);
    } catch (apiError) {
      setActionError(apiError.message);
    } finally {
      setBusyId(null);
    }
  };

  const changeStatus = async (user, suspend) => {
    const reason = suspend
      ? window.prompt(`Why are you suspending ${user.full_name}?`)
      : null;

    if (suspend && !(reason ?? '').trim()) {
      setActionError('A suspension needs a reason.');
      return;
    }

    setBusyId(user.user_id);
    setActionError('');
    try {
      await setAccountStatus(user.user_id, { suspend, reason: reason || null });
      setBanner(
        suspend
          ? `${user.full_name} has been suspended.`
          : `${user.full_name} has been reactivated.`
      );
      await load(filters);
    } catch (apiError) {
      setActionError(apiError.message);
    } finally {
      setBusyId(null);
    }
  };

  if (loading) return <LoadingState message="Loading accounts…" />;
  if (loadError) return <ErrorState message={loadError} onRetry={() => load(filters)} />;

  return (
    <>
      <div className="ju-page-header">
        <h1>User Management</h1>
        <p>Approve registrations, and suspend or reactivate accounts.</p>
      </div>

      <Alert tone="success">{banner}</Alert>
      <Alert tone="error">{actionError}</Alert>

      <div className="ju-card">
        <h3 className="ju-card__title">Pending Registrations ({pending.length})</h3>
        <p className="ju-card__subtitle">
          Doctor, pharmacist and administrator accounts cannot sign in until you approve them.
        </p>

        {pending.length === 0 ? (
          <EmptyState title="Nothing waiting" hint="New staff registrations appear here." />
        ) : (
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 'var(--ju-space-4)' }}>
            {pending.map((registration) => (
              <li
                key={registration.user_id}
                style={{
                  border: '1px solid var(--ju-border)',
                  borderRadius: 'var(--ju-radius)',
                  padding: 'var(--ju-space-4)',
                }}
              >
                <h3 style={{ margin: 0 }}>{registration.full_name}</h3>
                <p className="ju-field__help" style={{ margin: '4px 0 var(--ju-space-3)' }}>
                  {registration.university_id} · applying as {registration.role} ·{' '}
                  {registration.email ?? registration.phone ?? 'no contact on file'}
                  {registration.department ? ` · ${registration.department}` : ''}
                </p>

                <FormField
                  label="Reason"
                  name={`reason_${registration.user_id}`}
                  value={reasons[registration.user_id] ?? ''}
                  onChange={(event) => setReason(registration.user_id, event.target.value)}
                  rows={2}
                  help="Required when rejecting. Recorded in the audit trail."
                />

                <div className="ju-form-actions">
                  <button
                    type="button"
                    className="ju-btn ju-btn--danger"
                    onClick={() => decide(registration, false)}
                    disabled={busyId === registration.user_id}
                  >
                    Reject
                  </button>
                  <button
                    type="button"
                    className="ju-btn ju-btn--primary"
                    onClick={() => decide(registration, true)}
                    disabled={busyId === registration.user_id}
                  >
                    {busyId === registration.user_id ? 'Saving…' : 'Approve'}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="ju-card">
        <h3 className="ju-card__title">All Accounts</h3>

        <div className="ju-form-grid" style={{ marginBottom: 'var(--ju-space-4)' }}>
          <FormField
            label="Filter by Role"
            name="role"
            value={filters.role}
            onChange={(event) => setFilters({ ...filters, role: event.target.value })}
            options={ROLE_OPTIONS}
          />
          <FormField
            label="Filter by Status"
            name="status"
            value={filters.status}
            onChange={(event) => setFilters({ ...filters, status: event.target.value })}
            options={STATUS_OPTIONS}
          />
          <FormField
            label="Search"
            name="search"
            value={filters.search}
            onChange={(event) => setFilters({ ...filters, search: event.target.value })}
            placeholder="Name or university ID"
          />
        </div>

        {users.length === 0 ? (
          <EmptyState title="No accounts match" hint="Adjust the filters above." />
        ) : (
          <div className="ju-table-wrap">
            <table className="ju-table">
              <caption className="ju-field__help" style={{ textAlign: 'left', paddingBottom: '8px' }}>
                Accounts matching the current filters.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Name</th>
                  <th scope="col">University ID</th>
                  <th scope="col">Role</th>
                  <th scope="col">Department</th>
                  <th scope="col">Status</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.user_id}>
                    <td>
                      <strong>{user.full_name}</strong>
                      <br />
                      <span className="ju-field__help">{user.email ?? '—'}</span>
                    </td>
                    <td>{user.university_id}</td>
                    <td style={{ textTransform: 'capitalize' }}>{user.role}</td>
                    <td>{user.department ?? '—'}</td>
                    <td>
                      <StatusChip status={user.status} />
                    </td>
                    <td>
                      {user.status === 'suspended' ? (
                        <button
                          type="button"
                          className="ju-btn ju-btn--secondary"
                          onClick={() => changeStatus(user, false)}
                          disabled={busyId === user.user_id}
                        >
                          Reactivate
                        </button>
                      ) : user.status === 'active' ? (
                        <button
                          type="button"
                          className="ju-btn ju-btn--danger"
                          onClick={() => changeStatus(user, true)}
                          disabled={busyId === user.user_id}
                        >
                          Suspend
                        </button>
                      ) : (
                        <span className="ju-field__help">Awaiting the user</span>
                      )}
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
