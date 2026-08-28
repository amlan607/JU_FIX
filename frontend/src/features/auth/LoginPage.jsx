/**
 * Login screen (FR-A4, FR-A6, FR-A7).
 *
 * Route: `/login`. On success the user is routed to the dashboard, or back to
 * the page they originally requested.
 */
import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { Alert } from '../../components/Feedback';
import FormField from '../../components/FormField';
import { useAuth } from './AuthContext';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [form, setForm] = useState({ identifier: '', password: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (event) => {
    setForm({ ...form, [event.target.name]: event.target.value });
    setError('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form.identifier.trim() || !form.password) {
      setError('Enter your university ID and password.');
      return;
    }

    setSubmitting(true);
    try {
      await login(form.identifier.trim(), form.password);
      navigate(location.state?.from ?? '/dashboard', { replace: true });
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="ju-auth">
      <div className="ju-auth__card">
        <p className="ju-auth__brand">JU_FIX</p>
        <h1 style={{ fontSize: 'var(--ju-section-title)' }}>Login</h1>
        <p className="ju-card__subtitle">
          Authenticate and redirect to the correct role dashboard.
        </p>

        <Alert tone="error">{error}</Alert>

        <form onSubmit={handleSubmit} noValidate>
          <div style={{ display: 'grid', gap: 'var(--ju-space-4)' }}>
            <FormField
              label="University ID or Email"
              name="identifier"
              value={form.identifier}
              onChange={handleChange}
              required
              placeholder="STU-2021-370"
              help="Use the ID issued by Jahangirnagar University."
            />
            <FormField
              label="Password"
              name="password"
              type="password"
              value={form.password}
              onChange={handleChange}
              required
            />
          </div>

          <div className="ju-form-actions">
            <Link to="/forgot-password" className="ju-btn ju-btn--secondary">
              Forgot Password
            </Link>
            <button type="submit" className="ju-btn ju-btn--primary" disabled={submitting}>
              {submitting ? 'Signing In…' : 'Sign In'}
            </button>
          </div>
        </form>

        <p className="ju-auth__footer">
          No account yet? <Link to="/register">Create Account</Link>
        </p>
      </div>
    </div>
  );
}
