/** Route declarations for appointment booking. Owner: Mir Mohaiminul Islam (350). */
import { BookingPage, SchedulePage } from './AppointmentPages';

const PATIENTS = ['student', 'faculty'];

export default [
  { path: '/appointments', element: <BookingPage />, roles: PATIENTS },
  { path: '/appointments/book', element: <BookingPage />, roles: PATIENTS },
  { path: '/doctor/appointments', element: <SchedulePage />, roles: ['doctor'] },
];
