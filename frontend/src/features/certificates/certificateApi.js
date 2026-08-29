/**
 * API calls for medical certificates and sick leave (FR-F1 to FR-F4).
 */
import { api } from '../../services/apiClient';

/**
 * Request a certificate after a completed consultation.
 * @param {{appointment_id: number, reason: string, leave_start: string, leave_end: string}} payload Request details.
 * @returns {Promise<object>} The submitted request.
 */
export const requestCertificate = (payload) => api.post('/certificates', payload);

/**
 * List the signed in patient's certificate requests.
 * @returns {Promise<Array<object>>} The patient's requests.
 */
export const fetchMyCertificates = () => api.get('/certificates');

/**
 * List the certificate requests waiting for the signed in doctor.
 * @param {string} [status] Optional status filter.
 * @returns {Promise<Array<object>>} The review queue.
 */
export const fetchReviewQueue = (status) => api.get('/certificates/review-queue', { status });

/**
 * Approve or reject a certificate request.
 * @param {number} id The request id.
 * @param {{approve: boolean, remarks: string|null}} payload The decision.
 * @returns {Promise<object>} The decided request.
 */
export const decideCertificate = (id, payload) =>
  api.patch(`/certificates/${id}/decision`, payload);

/**
 * Verify a certificate by its public reference. No sign in is required.
 * @param {string} reference The reference printed on the certificate.
 * @returns {Promise<object>} The verification result.
 */
export const verifyCertificate = (reference) =>
  api.get('/certificates/verify', { reference }).catch((error) => {
    throw error;
  });
