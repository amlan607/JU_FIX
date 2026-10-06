/** API calls for appointment booking (FR-C). */
import { api } from '../../services/apiClient';

/** List bookable doctors. */
export const fetchDoctors = () => api.get('/appointments/doctors');
/** Fetch the slot grid for a doctor and ISO date. */
export const fetchAvailability = (doctorId, date) => api.get('/appointments/availability', { doctor_id: doctorId, date });
/** Book a slot. */
export const createAppointment = (payload) => api.post('/appointments', payload);
/** List the signed in patient's bookings. */
export const fetchMyAppointments = () => api.get('/appointments');
/** Cancel a booking. */
export const cancelAppointment = (id) => api.patch(`/appointments/${id}/cancel`, {});
/** List the signed in doctor's bookings for an ISO date. */
export const fetchDoctorSchedule = (date) => api.get('/appointments/doctor-schedule', { date });
/** Advance a booking as the assigned doctor. */
export const updateAppointmentStatus = (id, status) => api.patch(`/appointments/${id}/status?status=${status}`);
