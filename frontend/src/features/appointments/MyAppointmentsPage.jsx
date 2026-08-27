/**
 * My Appointments screen (FR-C3).
 *
 * Route: `/appointments`. Lists the patient's own bookings and offers
 * reschedule and cancel while the booking is still patient editable.
 */
import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

import { Alert, EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import FormField from '../../components/FormField';
import StatusChip from '../../components/StatusChip';
import {
  cancelAppointment,
  fetchAvailability,
  fetchMyAppointments,
  rescheduleAppointment,
} from './appointmentApi';
import { formatDate, formatTime, maxBookableIso, todayIso } from './dateUtils';

/** Statuses the patient may still change themselves. */
const EDITABLE = new Set(['booked']);

export default function MyAppointmentsPage() {
  const location = useLocation();
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [banner, setBanner] = useState(location.state?.message ?? '');
  const [actionError, setActionError] = useState('');
  const [editing, setEditing] = useState(null);
  const [newDate, setNewDate] = useState('');
  const [newSlots, setNewSlots] = useState([]);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError('');
    try {
      setAppointments(await fetchMyAppointments());
    } catch (apiError) {
      setLoadError(apiError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const startReschedule = (appointment) => {
    setEditing(appointment);
    setNewDate(appointment.appointment_date);
    setNewSlots([]);
    setActionError('');
  };

  const loadSlotsForNewDate = async (isoDate) => {
    setNewDate(isoDate);
    setNewSlots([]);
    if (!isoDate || !editing) return;
    try {
      const data = await fetchAvailability(editing.doctor_id, isoDate);
      setNewSlots(data.slots);
    } catch (apiError) {
      setActionError(apiError.message);
    }
  };

  const applyReschedule = async (startTime) => {
    try {
      await rescheduleAppointment(editing.id, {
        appointment_date: newDate,
        start_time: `${startTime}:00`,
      });
      setBanner('Your appointment has been rescheduled.');
      setEditing(null);
      await load();
    } catch (apiError) {
      setActionError(apiError.message);
    }
  };

  const handleCancel = async (appointment) => {
    const confirmed = window.confirm(
      `Cancel your appointment with ${appointment.doctor_name} on ${formatDate(
        appointment.appointment_date
      )}? This cannot be undone.`
    );
    if (!confirmed) return;

    try {
      await cancelAppointment(appointment.id, 'Cancelled by the patient.');
      setBanner('Your appointment has been cancelled.');
      await load();
    } catch (apiError) {
      setActionError(apiError.message);
    }
  };

  if (loading) return <LoadingState message="Loading your appointments…" />;
  if (loadError) return <ErrorState message={loadError} onRetry={load} />;

  return (
    <>
      <div className="ju-page-header">
        <h1>My Appointments</h1>
        <p>View, reschedule or cancel upcoming appointments and review history.</p>
      </div>

      <Alert tone="success">{banner}</Alert>
      <Alert tone="error">{actionError}</Alert>

      <div className="ju-card">
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 'var(--ju-space-4)',
            gap: 'var(--ju-space-3)',
            flexWrap: 'wrap',
          }}
        >
          <h3 className="ju-card__title" style={{ margin: 0 }}>
            All Appointments
          </h3>
          <Link to="/appointments/book" className="ju-btn ju-btn--primary">
            Book Appointment
          </Link>
        </div>

        {appointments.length === 0 ? (
          <EmptyState
            title="You have no appointments yet"
            hint="Book a consultation to see it listed here."
          />
        ) : (
          <div className="ju-table-wrap">
            <table className="ju-table">
              <caption className="ju-field__help" style={{ textAlign: 'left', paddingBottom: '8px' }}>
                Appointments booked by you, newest first.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Doctor</th>
                  <th scope="col">Date</th>
                  <th scope="col">Time</th>
                  <th scope="col">Reason</th>
                  <th scope="col">Status</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {appointments.map((appointment) => (
                  <tr key={appointment.id}>
                    <td>
                      <strong>{appointment.doctor_name}</strong>
                      <br />
                      <span className="ju-field__help">{appointment.doctor_speciality}</span>
                    </td>
                    <td>{formatDate(appointment.appointment_date)}</td>
                    <td>
                      {formatTime(appointment.start_time)} – {formatTime(appointment.end_time)}
                    </td>
                    <td style={{ maxWidth: '220px' }}>{appointment.reason}</td>
                    <td>
                      <StatusChip status={appointment.status} />
                    </td>
                    <td>
                      {EDITABLE.has(appointment.status) ? (
                        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                          <button
                            type="button"
                            className="ju-btn ju-btn--secondary"
                            onClick={() => startReschedule(appointment)}
                          >
                            Reschedule
                          </button>
                          <button
                            type="button"
                            className="ju-btn ju-btn--danger"
                            onClick={() => handleCancel(appointment)}
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <span className="ju-field__help">No action available</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {editing && (
        <div className="ju-card">
          <h3 className="ju-card__title">Reschedule Appointment</h3>
          <p className="ju-card__subtitle">
            {editing.doctor_name} · currently {formatDate(editing.appointment_date)} at{' '}
            {formatTime(editing.start_time)}
          </p>

          <FormField
            label="New Date"
            name="new_date"
            type="date"
            value={newDate}
            onChange={(event) => loadSlotsForNewDate(event.target.value)}
            required
            min={todayIso()}
            max={maxBookableIso()}
          />

          {newSlots.length > 0 && (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))',
                gap: 'var(--ju-space-3)',
                marginTop: 'var(--ju-space-4)',
              }}
            >
              {newSlots.map((slot) => (
                <button
                  key={slot.start_time}
                  type="button"
                  className="ju-btn ju-btn--secondary"
                  disabled={!slot.available}
                  onClick={() => applyReschedule(slot.start_time)}
                >
                  {slot.start_time}
                </button>
              ))}
            </div>
          )}

          <div className="ju-form-actions">
            <button
              type="button"
              className="ju-btn ju-btn--secondary"
              onClick={() => setEditing(null)}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </>
  );
}
