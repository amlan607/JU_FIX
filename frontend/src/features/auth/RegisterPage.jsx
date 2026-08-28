/**
 * Create Account screen (FR-A1, FR-A3, FR-J1).
 *
 * Route: `/register`. Doctor and pharmacist registrations are told up front
 * that an administrator must approve the account.
 */
import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { Alert } from '../../components/Feedback';
import FormField from '../../components/FormField';
import { api } from '../../services/apiClient';
import { checkPassword, isBdPhoneValid, isPasswordValid } from './passwordPolicy';

/** Roles a person may request at registration. Admin is created internally. */
const ROLE_OPTIONS = [
  { value: 'student', label: 'Student' },
  { value: 'faculty', label: 'Faculty or Staff' },
  { value: 'doctor', label: 'Doctor' },
  { value: 'pharmacist', label: 'Pharmacist' },
];

const ROLES_NEEDING_APPROVAL = ['doctor', 'pharmacist'];

const EMPTY_FORM = {
  university_id: '',
  full_name: '',
  email: '',
  phone: '',
  password: '',
  confirm_password: '',
  role: 'student',
  department: '',
};

export default function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [banner, setBanner] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const passwordRules = useMemo(() => checkPassword(form.password), [form.password]);
  const needsApproval = ROLES_NEEDING_APPROVAL.includes(form.role);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((previous) => ({ ...previous, [name]: value }));
    setErrors((previous) => ({ ...previous, [name]: '' }));
    setBanner('');
  };

  /**
   * Validate the form locally before calling the API.
   * @returns {Record<string, string>} Field errors keyed by field name.
   */
  const validate = () => {
    const found = {};
    if (!form.university_id.trim()) found.university_id = 'University ID is required.';
    if (form.full_name.trim().length < 2) found.full_name = 'Enter your full name.';
    if (!form.email.trim() && !form.phone.trim()) {
      found.email = 'Provide an email address or a phone number.';
    }
    if (form.phone.trim() && !isBdPhoneValid(form.phone)) {
      found.phone = 'Enter a valid Bangladeshi mobile number, for example 01712345678.';
    }
    if (!isPasswordValid(form.password)) {
      found.password = 'The password does not meet every requirement below.';
    }
    if (form.password !== form.confirm_password) {
      found.confirm_password = 'The two passwords do not match.';
    }
    return found;
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    const found = validate();
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setSubmitting(true);
    try {
      const data = await api.post(
        '/auth/register',
        {
          university_id: form.university_id.trim(),
          full_name: form.full_name.trim(),
          email: form.email.trim() || null,
          phone: form.phone.trim() || null,
          password: form.password,
          role: form.role,
          department: form.department.trim() || null,
        },
        { auth: false }
      );

      navigate('/verify-account', {
        state: { message: data.message, token: data.verification_token },
      });
    } catch (apiError) {
      setBanner(apiError.message);
      if (Array.isArray(apiError.details)) {
        const fieldErrors = {};
        apiError.details.forEach((detail) => {
          fieldErrors[detail.field] = detail.message;
        });
        setErrors(fieldErrors);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="ju-auth">
      <div className="ju-auth__card" style={{ maxWidth: '640px' }}>
        <p className="ju-auth__brand">JU_FIX</p>
        <h1 style={{ fontSize: 'var(--ju-section-title)' }}>Create Account</h1>
        <p className="ju-card__subtitle">
          Create an account with verified identity, role and secure password.
        </p>

        <Alert tone="error">{banner}</Alert>
        {needsApproval && (
          <Alert tone="info">
            {form.role === 'doctor' ? 'Doctor' : 'Pharmacist'} accounts are activated only after an
            administrator approves the registration.
          </Alert>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <div className="ju-form-grid">
            <FormField
              label="University ID"
              name="university_id"
              value={form.university_id}
              onChange={handleChange}
              required
              error={errors.university_id}
              placeholder="STU-2021-370"
            />
            <FormField
              label="Full Name"
              name="full_name"
              value={form.full_name}
              onChange={handleChange}
              required
              error={errors.full_name}
            />
            <FormField
              label="Email"
              name="email"
              type="email"
              value={form.email}
              onChange={handleChange}
              error={errors.email}
              help="Email or phone is required."
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
              label="Role"
              name="role"
              value={form.role}
              onChange={handleChange}
              required
              options={ROLE_OPTIONS}
            />
            <FormField
              label="Department or Designation"
              name="department"
              value={form.department}
              onChange={handleChange}
            />
            <FormField
              label="Password"
              name="password"
              type="password"
              value={form.password}
              onChange={handleChange}
              required
              error={errors.password}
            />
            <FormField
              label="Confirm Password"
              name="confirm_password"
              type="password"
              value={form.confirm_password}
              onChange={handleChange}
              required
              error={errors.confirm_password}
            />
          </div>

          <ul
            style={{
              listStyle: 'none',
              padding: 0,
              margin: 'var(--ju-space-4) 0 0',
              fontSize: 'var(--ju-chip)',
              display: 'grid',
              gap: '4px',
            }}
          >
            {passwordRules.map((rule) => (
              <li
                key={rule.id}
                style={{ color: rule.satisfied ? 'var(--ju-success)' : 'var(--ju-text-secondary)' }}
              >
                {rule.satisfied ? '✓' : '•'} {rule.label}
              </li>
            ))}
          </ul>

          <div className="ju-form-actions">
            <Link to="/login" className="ju-btn ju-btn--secondary">
              Sign In
            </Link>
            <button type="submit" className="ju-btn ju-btn--primary" disabled={submitting}>
              {submitting ? 'Creating Account…' : 'Create Account'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
