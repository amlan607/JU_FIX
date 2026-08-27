/**
 * Role aware landing page shown immediately after sign in (FR-A7).
 *
 * Each role sees shortcuts to the screens its own feature owner delivered.
 */
import { Link } from 'react-router-dom';

import { useAuth } from '../features/auth/AuthContext';

/** Shortcut cards grouped by role. */
const SHORTCUTS = {
  student: [
    { to: '/appointments/book', title: 'Book an Appointment', hint: 'Choose a doctor, date and time slot.' },
    { to: '/appointments', title: 'My Appointments', hint: 'Review, reschedule or cancel a booking.' },
    { to: '/medical-records', title: 'Medical Records', hint: 'View your consultation history.' },
    { to: '/prescriptions', title: 'My Prescriptions', hint: 'View and download issued prescriptions.' },
    { to: '/certificates', title: 'Medical Certificates', hint: 'Request and track sick leave documents.' },
  ],
  faculty: [
    { to: '/appointments/book', title: 'Book an Appointment', hint: 'Choose a doctor, date and time slot.' },
    { to: '/appointments', title: 'My Appointments', hint: 'Review, reschedule or cancel a booking.' },
    { to: '/medical-records', title: 'Medical Records', hint: 'View your consultation history.' },
    { to: '/certificates', title: 'Medical Certificates', hint: 'Request and track sick leave documents.' },
  ],
  doctor: [
    { to: '/doctor/appointments', title: 'My Schedule', hint: 'See today\u2019s booked consultations.' },
    { to: '/doctor/patients', title: 'Patient Records', hint: 'Open an authorised patient health record.' },
    { to: '/doctor/prescriptions', title: 'Write Prescription', hint: 'Create and issue a digital prescription.' },
    { to: '/doctor/certificate-requests', title: 'Certificate Review', hint: 'Approve or reject requests.' },
  ],
  pharmacist: [
    { to: '/pharmacy/prescriptions', title: 'Dispensing Queue', hint: 'Verify and dispense issued prescriptions.' },
  ],
  admin: [
    { to: '/admin/dashboard', title: 'Operational Dashboard', hint: 'Daily patient and appointment statistics.' },
    { to: '/admin/users', title: 'User Management', hint: 'Approve, suspend or reactivate accounts.' },
    { to: '/admin/reports', title: 'Reports', hint: 'Generate and export platform analytics.' },
  ],
};

export default function DashboardPage() {
  const { user } = useAuth();
  const shortcuts = SHORTCUTS[user?.role] ?? [];

  return (
    <>
      <div className="ju-page-header">
        <h1>Welcome, {user?.full_name}</h1>
        <p>JU Medical Centre Automation System. You are signed in as {user?.role}.</p>
      </div>

      <div className="ju-kpi-grid">
        {shortcuts.map((item) => (
          <Link key={item.to} to={item.to} className="ju-kpi" style={{ textDecoration: 'none' }}>
            <span className="ju-kpi__label">Go to</span>
            <span style={{ fontSize: '18px', fontWeight: 600, color: 'var(--ju-text)' }}>
              {item.title}
            </span>
            <span className="ju-kpi__hint">{item.hint}</span>
          </Link>
        ))}
      </div>
    </>
  );
}
