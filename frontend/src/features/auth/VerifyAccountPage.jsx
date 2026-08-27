/**
 * Account Verification screen (FR-A2).
 *
 * Route: `/verify-account`. The token normally arrives in an email link; in
 * development the registration response returns it so the flow can be completed
 * without a mail server.
 */
import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom';

import { Alert } from '../../components/Feedback';
import FormField from '../../components/FormField';
import { api } from '../../services/apiClient';

export default function VerifyAccountPage() {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();

  const [token, setToken] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const supplied = searchParams.get('token') ?? location.state?.token ?? '';
    if (supplied) setToken(supplied);
    if (location.state?.message) setStatus(location.state.message);
  }, [searchParams, location.state]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!token.trim()) {
      setError('Enter the verification code from your email.');
      return;
    }

    setSubmitting(true);
    setError('');
    try {
      const data = await api.post('/auth/verify-account', { token: token.trim() }, { auth: false });
      setStatus(
        data.user.status === 'pending_approval'
          ? 'Your contact is verified. An administrator will review the account shortly.'
          : 'Your account is verified. You can sign in now.'
      );
      if (data.user.status === 'active') {
        setTimeout(() => navigate('/login'), 1500);
      }
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
        <h1 style={{ fontSize: 'var(--ju-section-title)' }}>Account Verification</h1>
        <p className="ju-card__subtitle">Verify email or phone through OTP or approval link.</p>

        <Alert tone="success">{status}</Alert>
        <Alert tone="error">{error}</Alert>

        <form onSubmit={handleSubmit} noValidate>
          <FormField
            label="Verification Code"
            name="token"
            value={token}
            onChange={(event) => setToken(event.target.value)}
            required
            help="Paste the code from the verification link sent to your contact."
          />

          <div className="ju-form-actions">
            <Link to="/login" className="ju-btn ju-btn--secondary">
              Return to Login
            </Link>
            <button type="submit" className="ju-btn ju-btn--primary" disabled={submitting}>
              {submitting ? 'Verifying…' : 'Verify Account'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
