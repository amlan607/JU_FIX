/**
 * Medical certificate request screen (FR-F1).
 *
 * Route: `/certificates/request`. A certificate follows a consultation, so the
 * form offers only the patient's completed appointments.
 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Alert, EmptyState, LoadingState } from '../../components/Feedback';
import FormField from '../../components/FormField';
import { fetchMyAppointments } from '../appointments/appointmentApi';
import { formatDate } from '../appointments/dateUtils';
import { requestCertificate } from './certificateApi';

/** Today as an ISO 8601 date string. */
function todayIso() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(
    now.getDate()
  ).padStart(2, '0')}`;
}

export default function RequestCertificatePage() {
  const navigate = useNavigate();
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState({});

  const [form, setForm] = useState({
    appointment_id: '',
    reason: '',
    leave_start: todayIso(),
    leave_end: todayIso(),
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const all = await fetchMyAppointments();
      setAppointments(all.filter((appointment) => appointment.status === 'completed'));
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleChange = (event) => {
    setForm({ ...form, [event.target.name]: event.target.value });
    setErrors({ ...errors, [event.target.name]: '' });
    setError('');
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    const found = {};
    if (!form.appointment_id) found.appointment_id = 'Select the consultation this relates to.';
    if (form.reason.trim().length < 5) found.reason = 'Describe why you need the certificate.';
    if (form.leave_end < form.leave_start) {
      found.leave_end = 'The end date cannot be before the start date.';
    }
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setSubmitting(true);
    try {
      await requestCertificate({
        appointment_id: Number(form.appointment_id),
        reason: form.reason.trim(),
        leave_start: form.leave_start,
        leave_end: form.leave_end,
      });
      navigate('/certificates', {
        state: { message: 'Your request has been sent to the doctor for review.' },
      });
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingState message="Loading your completed consultations…" />;

  return (
    <>
      <div className="ju-page-header">
        <h1>Request Medical Certificate</h1>
        <p>Request a sick leave document for a consultation you have already attended.</p>
      </div>

      <Alert tone="error">{error}</Alert>

      <div className="ju-card">
        {appointments.length === 0 ? (
          <EmptyState
            title="No completed consultations"
            hint="A certificate can only be requested after a doctor marks your appointment completed."
          />
        ) : (
          <form onSubmit={handleSubmit} noValidate>
            <div className="ju-form-grid">
              <FormField
                label="Consultation"
                name="appointment_id"
                value={form.appointment_id}
                onChange={handleChange}
                required
                error={errors.appointment_id}
                options={appointments.map((appointment) => ({
                  value: String(appointment.id),
                  label: `${formatDate(appointment.appointment_date)} — ${appointment.doctor_name}`,
                }))}
              />
              <FormField
                label="Leave Start Date"
                name="leave_start"
                type="date"
                value={form.leave_start}
                onChange={handleChange}
                required
                error={errors.leave_start}
              />
              <FormField
                label="Leave End Date"
                name="leave_end"
                type="date"
                value={form.leave_end}
                onChange={handleChange}
                required
                error={errors.leave_end}
              />
            </div>

            <div style={{ marginTop: 'var(--ju-space-4)' }}>
              <FormField
                label="Reason for Request"
                name="reason"
                value={form.reason}
                onChange={handleChange}
                required
                rows={4}
                error={errors.reason}
                placeholder="Describe your condition and why you need leave from classes or duties."
                help="Your doctor reviews this before approving the certificate."
              />
            </div>

            <div className="ju-form-actions">
              <button type="submit" className="ju-btn ju-btn--primary" disabled={submitting}>
                {submitting ? 'Submitting…' : 'Submit Request'}
              </button>
            </div>
          </form>
        )}
      </div>
    </>
  );
}
