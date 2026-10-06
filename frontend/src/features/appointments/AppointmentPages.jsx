/** Booking and doctor schedule screens (FR-C1 to FR-C3, FR-C7). */
import { useCallback, useState } from 'react';

import Async from '../../components/Async';
import { Alert, EmptyState } from '../../components/Feedback';
import FormField from '../../components/FormField';
import StatusChip from '../../components/StatusChip';
import { useForm, useLoad } from '../../services/hooks';
import {
  cancelAppointment, createAppointment, fetchAvailability, fetchDoctorSchedule, fetchDoctors,
  fetchMyAppointments, updateAppointmentStatus,
} from './appointmentApi';
import { formatDate, formatTime, todayIso } from './dateUtils';

/** Run an API action, show the outcome and reload the list. */
function useAction(reload) {
  const [note, setNote] = useState({ tone: 'info', text: '' });
  const run = async (action, success) => {
    try {
      await action();
      setNote({ tone: 'success', text: success });
      reload();
    } catch (err) {
      setNote({ tone: 'error', text: err.message });
    }
  };
  return [note, run];
}

export function BookingPage() {
  const doctors = useLoad(fetchDoctors);
  const mine = useLoad(fetchMyAppointments);
  const [note, run] = useAction(mine.reload);
  const [form, bind] = useForm({ doctor_id: '', date: todayIso(), reason: '' });
  const [slots, setSlots] = useState([]);

  const findSlots = () => run(async () => setSlots((await fetchAvailability(form.doctor_id, form.date)).slots), 'Pick a time.');
  const book = (slot) =>
    run(async () => {
      const body = { doctor_id: Number(form.doctor_id), appointment_date: form.date, start_time: `${slot.start_time}:00`, reason: form.reason };
      await createAppointment(body);
      setSlots([]);
    }, 'Appointment booked.');

  return (
    <>
      <h1>Book an Appointment</h1>
      <Alert tone={note.tone}>{note.text}</Alert>
      <Async state={doctors}>
        {(list) => (
          <div className="ju-card ju-form-grid">
            <FormField label="Doctor" required options={list.map((d) => ({ value: String(d.doctor_id), label: `${d.full_name} - ${d.speciality}` }))} {...bind('doctor_id')} />
            <FormField label="Date" type="date" required min={todayIso()} {...bind('date')} />
            <FormField label="Reason for Visit" required rows={2} {...bind('reason')} />
            <button type="button" className="ju-btn ju-btn--primary" onClick={findSlots} disabled={!form.doctor_id}>Find Slots</button>
          </div>
        )}
      </Async>
      {slots.map((s) => (
        <button key={s.start_time} type="button" className="ju-btn ju-btn--secondary" disabled={!s.available} onClick={() => book(s)}>{s.start_time}</button>
      ))}
      <Async state={mine}>
        {(rows) => (
          <table className="ju-table">
            <tbody>
              {rows.map((a) => (
                <tr key={a.id}>
                  <td>{a.doctor_name}</td><td>{formatDate(a.appointment_date)} {formatTime(a.start_time)}</td>
                  <td><StatusChip status={a.status} /></td>
                  <td>{a.status === 'booked' && <button type="button" className="ju-btn ju-btn--danger" onClick={() => run(() => cancelAppointment(a.id), 'Cancelled.')}>Cancel</button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Async>
    </>
  );
}

const NEXT = { booked: ['confirmed'], confirmed: ['completed', 'no_show'] };

export function SchedulePage() {
  const [day, setDay] = useState(todayIso());
  const load = useCallback(() => fetchDoctorSchedule(day), [day]);
  const schedule = useLoad(load);
  const [note, run] = useAction(schedule.reload);

  return (
    <>
      <h1>My Schedule</h1>
      <Alert tone={note.tone}>{note.text}</Alert>
      <FormField label="Date" type="date" name="day" value={day} onChange={(e) => setDay(e.target.value)} />
      <Async state={schedule}>
        {(rows) => rows.length === 0 ? <EmptyState title="No consultations on this date" /> : (
          <table className="ju-table">
            <tbody>
              {rows.map((a) => (
                <tr key={a.id}>
                  <td>{formatTime(a.start_time)}</td><td>{a.patient_name}</td><td><StatusChip status={a.status} /></td>
                  <td>{(NEXT[a.status] ?? []).map((s) => (
                    <button key={s} type="button" className="ju-btn ju-btn--secondary" onClick={() => run(() => updateAppointmentStatus(a.id, s), `Marked ${s}.`)}>{s.replace('_', ' ')}</button>
                  ))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Async>
    </>
  );
}
