/**
 * My Profile screen (FR-A8).
 *
 * Route: `/profile`. A user may edit their own display details. The university
 * ID, role and account status are read only because only an administrator can
 * change them.
 */
import { useState } from 'react';

import { Alert } from '../../components/Feedback';
import FormField from '../../components/FormField';
import StatusChip from '../../components/StatusChip';
import { api } from '../../services/apiClient';
import { useAuth } from './AuthContext';
import { isBdPhoneValid } from './passwordPolicy';

export default function ProfilePage() {
  const { user, setUser } = useAuth();
  const [form, setForm] = useState({
    full_name: user?.full_name ?? '',
    phone: user?.phone ?? '',
    department: user?.department ?? '',
    designation: user?.designation ?? '',
  });
  const [errors, setErrors] = useState({});
  const [saved, setSaved] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (event) => {
    setForm({ ...form, [event.target.name]: event.target.value });
    setErrors({ ...errors, [event.target.name]: '' });
    setSaved('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (form.phone && !isBdPhoneValid(form.phone)) {
      setErrors({ phone: 'Enter a valid Bangladeshi mobile number.' });
      return;
    }

    setSubmitting(true);
    setError('');
    try {
      const updated = await api.patch('/auth/me', {
        full_name: form.full_name.trim(),
        phone: form.phone.trim() || null,
        department: form.department.trim() || null,
        designation: form.designation.trim() || null,
      });
      setUser(updated);
      setSaved('Your profile has been updated.');
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="ju-page-header">
        <h1>My Profile</h1>
        <p>View and edit your contact and department details.</p>
      </div>

      <div className="ju-card">
        <Alert tone="success">{saved}</Alert>
        <Alert tone="error">{error}</Alert>

        <div
          style={{
            display: 'flex',
            gap: 'var(--ju-space-4)',
            marginBottom: 'var(--ju-space-5)',
            flexWrap: 'wrap',
          }}
        >
          <div>
            <span className="ju-kpi__label">University ID</span>
            <p style={{ margin: 0, fontWeight: 600 }}>{user?.university_id}</p>
          </div>
          <div>
            <span className="ju-kpi__label">Role</span>
            <p style={{ margin: 0, textTransform: 'capitalize', fontWeight: 600 }}>{user?.role}</p>
          </div>
          <div>
            <span className="ju-kpi__label">Account Status</span>
            <p style={{ margin: 0 }}>
              <StatusChip status={user?.status} />
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          <div className="ju-form-grid">
            <FormField
              label="Full Name"
              name="full_name"
              value={form.full_name}
              onChange={handleChange}
              required
            />
            <FormField
              label="Email"
              name="email"
              value={user?.email ?? ''}
              onChange={() => {}}
              disabled
              help="Contact the medical centre office to change a verified email."
            />
            <FormField
              label="Phone"
              name="phone"
              value={form.phone}
              onChange={handleChange}
              error={errors.phone}
              placeholder="01712345678"
            />
            <FormField
              label="Department"
              name="department"
              value={form.department}
              onChange={handleChange}
            />
            <FormField
              label="Designation"
              name="designation"
              value={form.designation}
              onChange={handleChange}
            />
          </div>

          <div className="ju-form-actions">
            <button type="submit" className="ju-btn ju-btn--primary" disabled={submitting}>
              {submitting ? 'Saving…' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </>
  );
}
