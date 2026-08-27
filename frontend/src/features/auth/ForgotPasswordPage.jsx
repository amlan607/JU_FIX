/**
 * Password Recovery screen (FR-A5).
 *
 * Route: `/forgot-password`. Implements the three step flow from the UI design:
 * request a code, enter the code, then set a new password.
 */
import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { Alert } from '../../components/Feedback';
import FormField from '../../components/FormField';
import { api } from '../../services/apiClient';
import { checkPassword, isPasswordValid } from './passwordPolicy';

const STEP_REQUEST = 'request';
const STEP_RESET = 'reset';

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(STEP_REQUEST);
  const [identifier, setIdentifier] = useState('');
  const [token, setToken] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const passwordRules = useMemo(() => checkPassword(newPassword), [newPassword]);

  const requestCode = async (event) => {
    event.preventDefault();
    if (!identifier.trim()) {
      setError('Enter your university ID or email.');
      return;
    }

    setSubmitting(true);
    setError('');
    try {
      const data = await api.post(
        '/auth/forgot-password',
        { identifier: identifier.trim() },
        { auth: false }
      );
      setNotice(data.message);
      if (data.reset_token) setToken(data.reset_token);
      setStep(STEP_RESET);
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setSubmitting(false);
    }
  };

  const submitReset = async (event) => {
    event.preventDefault();
    if (!token.trim()) {
      setError('Enter the recovery code you received.');
      return;
    }
    if (!isPasswordValid(newPassword)) {
      setError('The new password does not meet every requirement below.');
      return;
    }

    setSubmitting(true);
    setError('');
    try {
      await api.post(
        '/auth/reset-password',
        { token: token.trim(), new_password: newPassword },
        { auth: false }
      );
      navigate('/login', { state: { message: 'Password updated. Please sign in.' } });
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
        <h1 style={{ fontSize: 'var(--ju-section-title)' }}>Password Recovery</h1>
        <p className="ju-card__subtitle">Recover access using the verified contact method.</p>

        <Alert tone="info">{notice}</Alert>
        <Alert tone="error">{error}</Alert>

        {step === STEP_REQUEST ? (
          <form onSubmit={requestCode} noValidate>
            <FormField
              label="University ID or Email"
              name="identifier"
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              required
            />
            <div className="ju-form-actions">
              <Link to="/login" className="ju-btn ju-btn--secondary">
                Return to Login
              </Link>
              <button type="submit" className="ju-btn ju-btn--primary" disabled={submitting}>
                {submitting ? 'Sending…' : 'Send Recovery Code'}
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={submitReset} noValidate>
            <div style={{ display: 'grid', gap: 'var(--ju-space-4)' }}>
              <FormField
                label="Recovery Code"
                name="token"
                value={token}
                onChange={(event) => setToken(event.target.value)}
                required
              />
              <FormField
                label="New Password"
                name="new_password"
                type="password"
                value={newPassword}
                onChange={(event) => setNewPassword(event.target.value)}
                required
              />
            </div>

            <ul
              style={{
                listStyle: 'none',
                padding: 0,
                margin: 'var(--ju-space-3) 0 0',
                fontSize: 'var(--ju-chip)',
                display: 'grid',
                gap: '4px',
              }}
            >
              {passwordRules.map((rule) => (
                <li
                  key={rule.id}
                  style={{
                    color: rule.satisfied ? 'var(--ju-success)' : 'var(--ju-text-secondary)',
                  }}
                >
                  {rule.satisfied ? '✓' : '•'} {rule.label}
                </li>
              ))}
            </ul>

            <div className="ju-form-actions">
              <button
                type="button"
                className="ju-btn ju-btn--secondary"
                onClick={() => setStep(STEP_REQUEST)}
              >
                Back
              </button>
              <button type="submit" className="ju-btn ju-btn--primary" disabled={submitting}>
                {submitting ? 'Updating…' : 'Reset Password'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
