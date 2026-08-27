/**
 * API calls for the appointment booking feature (FR-C).
 *
 * Keeping the endpoints in one module means a URL change is a one line edit and
 * the screens stay free of transport detail.
 */
import { api } from '../../services/apiClient';

/**
 * List doctors available for booking.
 * @param {string} [speciality] Optional speciality filter.
 * @returns {Promise<Array<object>>} Bookable doctors.
 */
export const fetchDoctors = (speciality) => api.get('/appointments/doctors', { speciality });

/**
 * Fetch the slot grid for one doctor on one date.
 * @param {number} doctorId The doctor's user id.
 * @param {string} date ISO 8601 date string.
 * @returns {Promise<object>} Doctor summary, date and slots.
 */
export const fetchAvailability = (doctorId, date) =>
  api.get('/appointments/availability', { doctor_id: doctorId, date });

/**
 * Create a booking.
 * @param {{doctor_id: number, appointment_date: string, start_time: string, reason: string}} payload Booking details.
 * @returns {Promise<object>} The created appointment.
 */
export const createAppointment = (payload) => api.post('/appointments', payload);

/**
 * List the signed in patient's own bookings.
 * @param {string} [status] Optional status filter.
 * @returns {Promise<Array<object>>} The patient's appointments.
 */
export const fetchMyAppointments = (status) => api.get('/appointments', { status });

/**
 * Move a booking to a different slot.
 * @param {number} id The appointment id.
 * @param {{appointment_date: string, start_time: string}} payload The new slot.
 * @returns {Promise<object>} The updated appointment.
 */
export const rescheduleAppointment = (id, payload) =>
  api.patch(`/appointments/${id}/reschedule`, payload);

/**
 * Cancel a booking.
 * @param {number} id The appointment id.
 * @param {string} [reason] Optional cancellation reason.
 * @returns {Promise<object>} The cancelled appointment.
 */
export const cancelAppointment = (id, reason) =>
  api.patch(`/appointments/${id}/cancel`, { reason: reason || null });

/**
 * List the signed in doctor's schedule.
 * @param {string} [date] Optional ISO date filter.
 * @returns {Promise<Array<object>>} Assigned appointments.
 */
export const fetchDoctorSchedule = (date) => api.get('/appointments/doctor-schedule', { date });

/**
 * Advance an appointment's status as the assigned doctor.
 * @param {number} id The appointment id.
 * @param {string} status The target status.
 * @returns {Promise<object>} The updated appointment.
 */
export const updateAppointmentStatus = (id, status) =>
  api.patch(`/appointments/${id}/status?status=${status}`);
