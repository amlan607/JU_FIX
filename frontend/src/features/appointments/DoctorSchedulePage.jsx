/**
 * Doctor schedule console (FR-C7).
 *
 * Route: `/doctor/appointments`. The assigned doctor confirms a booking, then
 * marks it completed or a no show.
 */
import { useCallback, useEffect, useState } from 'react';

import { Alert, EmptyState, ErrorState, LoadingState } from '../../components/Feedback';
import FormField from '../../components/FormField';
import StatusChip from '../../components/StatusChip';
import { fetchDoctorSchedule, updateAppointmentStatus } from './appointmentApi';
import { formatDate, formatTime, todayIso } from './dateUtils';

/** Status transitions the doctor may apply, keyed by current status. */
const NEXT_ACTIONS = {
  booked: [{ status: 'confirmed', label: 'Confirm', variant: 'primary' }],
  confirmed: [
    { status: 'completed', label: 'Mark Completed', variant: 'primary' },
    { status: 'no_show', label: 'Mark No-Show', variant: 'danger' },
  ],
};

export default function DoctorSchedulePage() {
  const [date, setDate] = useState(todayIso());
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [actionError, setActionError] = useState('');
  const [banner, setBanner] = useState('');

  const load = useCallback(async (isoDate) => {
    setLoading(true);
    setLoadError('');
    try {
      setAppointments(await fetchDoctorSchedule(isoDate));
    } catch (apiError) {
      setLoadError(apiError.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(date);
  }, [load, date]);

  const applyStatus = async (appointment, status, label) => {
    setActionError('');
    try {
      await updateAppointmentStatus(appointment.id, status);
      setBanner(`${appointment.patient_name}: ${label.toLowerCase()} recorded.`);
      await load(date);
    } catch (apiError) {
      setActionError(apiError.message);
    }
  };

  return (
    <>
      <div className="ju-page-header">
        <h1>My Schedule</h1>
        <p>Consultations assigned to you. Confirm, complete or mark a no-show.</p>
      </div>

      <Alert tone="success">{banner}</Alert>
      <Alert tone="error">{actionError}</Alert>

      <div className="ju-card">
        <div style={{ maxWidth: '260px', marginBottom: 'var(--ju-space-4)' }}>
          <FormField
            label="Schedule Date"
            name="date"
            type="date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
          />
        </div>

        {loading ? (
          <LoadingState message="Loading your schedule…" />
        ) : loadError ? (
          <ErrorState message={loadError} onRetry={() => load(date)} />
        ) : appointments.length === 0 ? (
          <EmptyState
            title="No consultations on this date"
            hint="Choose a different date to see other bookings."
          />
        ) : (
          <div className="ju-table-wrap">
            <table className="ju-table">
              <caption className="ju-field__help" style={{ textAlign: 'left', paddingBottom: '8px' }}>
                Consultations assigned to you on {formatDate(date)}.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Time</th>
                  <th scope="col">Patient</th>
                  <th scope="col">Visit Type</th>
                  <th scope="col">Reason</th>
                  <th scope="col">Status</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {appointments.map((appointment) => (
                  <tr key={appointment.id}>
                    <td>
                      {formatTime(appointment.start_time)} – {formatTime(appointment.end_time)}
                    </td>
                    <td>{appointment.patient_name}</td>
                    <td style={{ textTransform: 'capitalize' }}>
                      {appointment.visit_type.replaceAll('_', ' ')}
                    </td>
                    <td style={{ maxWidth: '240px' }}>{appointment.reason}</td>
                    <td>
                      <StatusChip status={appointment.status} />
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        {(NEXT_ACTIONS[appointment.status] ?? []).map((action) => (
                          <button
                            key={action.status}
                            type="button"
                            className={`ju-btn ju-btn--${action.variant}`}
                            onClick={() => applyStatus(appointment, action.status, action.label)}
                          >
                            {action.label}
                          </button>
                        ))}
                        {!NEXT_ACTIONS[appointment.status] && (
                          <span className="ju-field__help">Closed</span>
                        )}
                      </div>
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
