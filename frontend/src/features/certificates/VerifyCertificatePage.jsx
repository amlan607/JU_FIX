/**
 * Public certificate verification screen (FR-F4).
 *
 * Route: `/verify-certificate`, outside the signed in shell. A department
 * office can confirm a certificate a student hands them without needing a
 * JU_FIX account. The result never discloses the medical reason.
 */
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { Alert } from '../../components/Feedback';
import FormField from '../../components/FormField';
import { verifyCertificate } from './certificateApi';

export default function VerifyCertificatePage() {
  const [searchParams] = useSearchParams();
  const [reference, setReference] = useState(searchParams.get('reference') ?? '');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [checking, setChecking] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setResult(null);
    setError('');

    if (!reference.trim()) {
      setError('Enter the reference ID printed on the certificate.');
      return;
    }

    setChecking(true);
    try {
      setResult(await verifyCertificate(reference.trim()));
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="ju-auth">
      <div className="ju-auth__card" style={{ maxWidth: '560px' }}>
        <p className="ju-auth__brand">JU_FIX</p>
        <h1 style={{ fontSize: 'var(--ju-section-title)' }}>Verify Medical Certificate</h1>
        <p className="ju-card__subtitle">
          Confirm that a certificate was issued by the JU Medical Centre. No sign in is required.
        </p>

        <Alert tone="error">{error}</Alert>

        <form onSubmit={handleSubmit} noValidate>
          <FormField
            label="Certificate Reference ID"
            name="reference"
            value={reference}
            onChange={(event) => setReference(event.target.value)}
            required
            placeholder="JUMC-2026-004312"
            help="The reference is printed at the foot of the certificate."
          />

          <div className="ju-form-actions">
            <button type="submit" className="ju-btn ju-btn--primary" disabled={checking}>
              {checking ? 'Checking…' : 'Verify Certificate'}
            </button>
          </div>
        </form>

        {result && (
          <div
            style={{
              marginTop: 'var(--ju-space-5)',
              padding: 'var(--ju-space-4)',
              borderRadius: 'var(--ju-radius)',
              border: `2px solid ${result.valid ? 'var(--ju-success)' : 'var(--ju-error)'}`,
              background: result.valid ? 'var(--ju-success-soft)' : 'var(--ju-error-soft)',
            }}
          >
            <p
              style={{
                margin: 0,
                fontWeight: 700,
                color: result.valid ? 'var(--ju-success)' : 'var(--ju-error)',
              }}
            >
              {result.valid ? 'Genuine certificate' : 'Not verified'}
            </p>
            <p style={{ margin: '4px 0 0' }}>{result.message}</p>

            {result.valid && (
              <dl style={{ display: 'grid', gap: 'var(--ju-space-2)', marginTop: 'var(--ju-space-4)' }}>
                <div>
                  <dt className="ju-kpi__label">Issued To</dt>
                  <dd style={{ margin: 0 }}>
                    {result.patient_name} ({result.patient_university_id})
                  </dd>
                </div>
                <div>
                  <dt className="ju-kpi__label">Leave Period</dt>
                  <dd style={{ margin: 0 }}>
                    {result.leave_start} to {result.leave_end} ({result.leave_days} day
                    {result.leave_days === 1 ? '' : 's'})
                  </dd>
                </div>
                <div>
                  <dt className="ju-kpi__label">Issued By</dt>
                  <dd style={{ margin: 0 }}>{result.issued_by}</dd>
                </div>
              </dl>
            )}
          </div>
        )}

        <p className="ju-auth__footer">
          <Link to="/login">Return to JU_FIX sign in</Link>
        </p>
      </div>
    </div>
  );
}
