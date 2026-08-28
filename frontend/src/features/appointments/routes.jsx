/**
 * Route declarations for the appointment booking feature (FR-C).
 *
 * Owner: Mir Mohaiminul Islam (350).
 */
import BookAppointmentPage from './BookAppointmentPage';
import DoctorSchedulePage from './DoctorSchedulePage';
import MyAppointmentsPage from './MyAppointmentsPage';

export default [
  { path: '/appointments', element: <MyAppointmentsPage />, roles: ['student', 'faculty'] },
  { path: '/appointments/book', element: <BookAppointmentPage />, roles: ['student', 'faculty'] },
  { path: '/doctor/appointments', element: <DoctorSchedulePage />, roles: ['doctor'] },
];
