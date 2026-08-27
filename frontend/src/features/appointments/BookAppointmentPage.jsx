/**
 * Appointment booking wizard (FR-C1, FR-C2).
 *
 * Route: `/appointments/book`. Implements the three step flow from the UI
 * design: search a doctor, choose a slot, then review and confirm.
 */
import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Alert, EmptyState, LoadingState } from '../../components/Feedback';
import FormField from '../../components/FormField';
import {
  createAppointment,
  fetchAvailability,
  fetchDoctors,
} from './appointmentApi';
import { formatDate, formatTime, isClosedDay, maxBookableIso, todayIso } from './dateUtils';

const STEP_SEARCH = 1;
const STEP_SLOT = 2;
const STEP_REVIEW = 3;

const VISIT_TYPES = [
  { value: 'consultation', label: 'General Consultation' },
  { value: 'follow_up', label: 'Follow-up Visit' },
  { value: 'checkup', label: 'Routine Checkup' },
];

export default function BookAppointmentPage() {
  const navigate = useNavigate();

  const [step, setStep] = useState(STEP_SEARCH);
  const [doctors, setDoctors] = useState([]);
  const [loadingDoctors, setLoadingDoctors] = useState(true);
  const [slots, setSlots] = useState([]);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const [form, setForm] = useState({
    speciality: '',
    doctor_id: '',
    appointment_date: '',
    start_time: '',
    visit_type: 'consultation',
    reason: '',
  });

  const selectedDoctor = doctors.find((doctor) => String(doctor.doctor_id) === String(form.doctor_id));

  const loadDoctors = useCallback(async (speciality) => {
    setLoadingDoctors(true);
    setError('');
    try {
      setDoctors(await fetchDoctors(speciality || undefined));
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setLoadingDoctors(false);
    }
  }, []);

  useEffect(() => {
    loadDoctors();
  }, [loadDoctors]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((previous) => ({ ...previous, [name]: value }));
    setError('');
  };

  const goToSlots = async (event) => {
    event.preventDefault();
    if (!form.doctor_id) {
      setError('Select a doctor to continue.');
      return;
    }
    if (!form.appointment_date) {
      setError('Choose the date of your visit.');
      return;
    }
    if (isClosedDay(form.appointment_date)) {
      setError('The medical centre is closed on Friday. Choose another date.');
      return;
    }
    if (form.reason.trim().length < 3) {
      setError('Describe the reason for your visit.');
      return;
    }

    setLoadingSlots(true);
    setError('');
    try {
      const data = await fetchAvailability(Number(form.doctor_id), form.appointment_date);
      setSlots(data.slots);
      setStep(STEP_SLOT);
    } catch (apiError) {
      setError(apiError.message);
    } finally {
      setLoadingSlots(false);
    }
  };

  const chooseSlot = (slot) => {
    setForm((previous) => ({ ...previous, start_time: slot.start_time }));
    setStep(STEP_REVIEW);
  };

  const confirmBooking = async () => {
    setSubmitting(true);
    setError('');
    try {
      const appointment = await createAppointment({
        doctor_id: Number(form.doctor_id),
        appointment_date: form.appointment_date,
        start_time: `${form.start_time}:00`,
        reason: form.reason.trim(),
        visit_type: form.visit_type,
      });
      navigate('/appointments', {
        state: {
          message: `Appointment confirmed with ${appointment.doctor_name} on ${formatDate(
            form.appointment_date
          )} at ${form.start_time}.`,
        },
      });
    } catch (apiError) {
      setError(apiError.message);
      if (apiError.code === 'conflict') {
        // The slot was taken while the patient was reviewing. Reload the grid.
        setStep(STEP_SLOT);
        const data = await fetchAvailability(Number(form.doctor_id), form.appointment_date);
        setSlots(data.slots);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="ju-page-header">
        <h1>Book an Appointment</h1>
        <p>Step {step} of 3. Select a department, doctor, date and time slot.</p>
      </div>

      <Alert tone="error">{error}</Alert>

      {step === STEP_SEARCH && (
        <div className="ju-card">
          <h3 className="ju-card__title">Appointment Search</h3>
          <p className="ju-card__subtitle">Select department, preferred date, visit type and reason.</p>

          <form onSubmit={goToSlots} noValidate>
            <div className="ju-form-grid">
              <FormField
                label="Speciality"
                name="speciality"
                value={form.speciality}
                onChange={(event) => {
                  handleChange(event);
                  loadDoctors(event.target.value);
                }}
                help="Leave empty to see every available doctor."
              />
              <FormField
                label="Doctor"
                name="doctor_id"
                value={form.doctor_id}
                onChange={handleChange}
                required
                options={doctors.map((doctor) => ({
                  value: String(doctor.doctor_id),
                  label: `${doctor.full_name} — ${doctor.speciality}`,
                }))}
              />
              <FormField
                label="Date"
                name="appointment_date"
                type="date"
                value={form.appointment_date}
                onChange={handleChange}
                required
                min={todayIso()}
                max={maxBookableIso()}
                help="The medical centre is closed on Friday."
              />
              <FormField
                label="Visit Type"
                name="visit_type"
                value={form.visit_type}
                onChange={handleChange}
                required
                options={VISIT_TYPES}
              />
            </div>

            <div style={{ marginTop: 'var(--ju-space-4)' }}>
              <FormField
                label="Reason for Visit"
                name="reason"
                value={form.reason}
                onChange={handleChange}
                required
                rows={4}
                placeholder="Describe your symptoms and how long you have had them."
              />
            </div>

            {loadingDoctors && <LoadingState message="Loading available doctors…" />}

            <div className="ju-form-actions">
              <button type="submit" className="ju-btn ju-btn--primary" disabled={loadingSlots}>
                {loadingSlots ? 'Loading Slots…' : 'Continue'}
              </button>
            </div>
          </form>
        </div>
      )}

      {step === STEP_SLOT && (
        <div className="ju-card">
          <h3 className="ju-card__title">Doctor and Slot Selection</h3>
          <p className="ju-card__subtitle">
            {selectedDoctor?.full_name} · {formatDate(form.appointment_date)}
          </p>

          {slots.length === 0 ? (
            <EmptyState
              title="No slots configured"
              hint="This doctor has no consultation slots on the selected date."
            />
          ) : (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))',
                gap: 'var(--ju-space-3)',
              }}
            >
              {slots.map((slot) => (
                <button
                  key={slot.start_time}
                  type="button"
                  className={`ju-btn ${slot.available ? 'ju-btn--secondary' : 'ju-btn--secondary'}`}
                  disabled={!slot.available}
                  onClick={() => chooseSlot(slot)}
                  aria-label={
                    slot.available
                      ? `Select slot ${slot.start_time}`
                      : `Slot ${slot.start_time} is already booked`
                  }
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
              onClick={() => setStep(STEP_SEARCH)}
            >
              Change Doctor
            </button>
          </div>
        </div>
      )}

      {step === STEP_REVIEW && (
        <div className="ju-card">
          <h3 className="ju-card__title">Review and Confirm</h3>
          <p className="ju-card__subtitle">Review details and confirm the booking.</p>

          <dl style={{ display: 'grid', gap: 'var(--ju-space-3)', margin: 0 }}>
            <div>
              <dt className="ju-kpi__label">Doctor</dt>
              <dd style={{ margin: 0 }}>
                {selectedDoctor?.full_name} — {selectedDoctor?.speciality}
              </dd>
            </div>
            <div>
              <dt className="ju-kpi__label">Date and Time</dt>
              <dd style={{ margin: 0 }}>
                {formatDate(form.appointment_date)} at {formatTime(form.start_time)}
              </dd>
            </div>
            <div>
              <dt className="ju-kpi__label">Room</dt>
              <dd style={{ margin: 0 }}>{selectedDoctor?.room_number ?? 'To be assigned'}</dd>
            </div>
            <div>
              <dt className="ju-kpi__label">Reason</dt>
              <dd style={{ margin: 0 }}>{form.reason}</dd>
            </div>
          </dl>

          <div className="ju-form-actions">
            <button
              type="button"
              className="ju-btn ju-btn--secondary"
              onClick={() => setStep(STEP_SLOT)}
            >
              Back and Edit
            </button>
            <button
              type="button"
              className="ju-btn ju-btn--primary"
              onClick={confirmBooking}
              disabled={submitting}
            >
              {submitting ? 'Confirming…' : 'Confirm Appointment'}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
