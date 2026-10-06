/**
 * API calls for digital prescription management (FR-D1, FR-D3).
 */
import { api } from '../../services/apiClient';

/**
 * Create a prescription draft.
 * @param {object} payload Patient, diagnosis and medicine lines.
 * @returns {Promise<object>} The created draft.
 */
export const createPrescription = (payload) => api.post('/prescriptions', payload);

/**
 * List the prescriptions written by the signed in doctor.
 * @param {string} [status] Optional status filter.
 * @returns {Promise<Array<object>>} The doctor's prescriptions.
 */
export const fetchWrittenPrescriptions = (status) => api.get('/prescriptions/written', { status });

/**
 * List the signed in patient's issued prescriptions.
 * @returns {Promise<Array<object>>} The patient's prescriptions.
 */
export const fetchMyPrescriptions = () => api.get('/prescriptions/my-prescriptions');

/**
 * List prescriptions waiting at the pharmacy counter.
 * @param {string} [status] Optional status filter.
 * @returns {Promise<Array<object>>} The dispensing queue.
 */
export const fetchPharmacyQueue = (status) => api.get('/prescriptions/pharmacy-queue', { status });

/**
 * Find an issued prescription by its printed reference code.
 * @param {string} code The reference code.
 * @returns {Promise<object>} The matching prescription.
 */
export const lookupByReference = (code) => api.get('/prescriptions/lookup', { code });

/**
 * Edit a draft prescription.
 * @param {number} id The prescription id.
 * @param {object} payload The changed fields.
 * @returns {Promise<object>} The updated draft.
 */
export const updatePrescription = (id, payload) => api.patch(`/prescriptions/${id}`, payload);

/**
 * Publish a draft to the patient and the pharmacy.
 * @param {number} id The prescription id.
 * @returns {Promise<object>} The issued prescription.
 */
export const issuePrescription = (id) => api.patch(`/prescriptions/${id}/issue`);

/**
 * Cancel a prescription that has not been dispensed.
 * @param {number} id The prescription id.
 * @returns {Promise<object>} The cancelled prescription.
 */
export const cancelPrescription = (id) => api.patch(`/prescriptions/${id}/cancel`);

/**
 * Record that the pharmacy has dispensed the medicines.
 * @param {number} id The prescription id.
 * @param {string} [note] Optional counter note.
 * @returns {Promise<object>} The dispensed prescription.
 */
export const dispensePrescription = (id, note) =>
  api.patch(`/prescriptions/${id}/dispense`, { note: note || null });
