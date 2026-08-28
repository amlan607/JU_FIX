/**
 * API calls for the Electronic Health Record feature (FR-D2 to FR-D5).
 */
import { api } from '../../services/apiClient';

/**
 * Fetch the signed in patient's own record timeline.
 * @param {string} [type] Optional record type filter.
 * @returns {Promise<Array<object>>} The patient's clinical entries.
 */
export const fetchMyRecords = (type) => api.get('/medical-records/my-records', { type });

/**
 * Fetch the patients the signed in doctor is authorised to open.
 * @returns {Promise<Array<object>>} Authorised patients.
 */
export const fetchAuthorisedPatients = () => api.get('/medical-records/patients');

/**
 * Fetch one patient's record timeline.
 * @param {number} patientId The patient's user id.
 * @param {string} [type] Optional record type filter.
 * @returns {Promise<Array<object>>} The patient's clinical entries.
 */
export const fetchPatientRecords = (patientId, type) =>
  api.get(`/medical-records/patients/${patientId}`, { type });

/**
 * Fetch one clinical entry in full.
 * @param {number} recordId The record id.
 * @returns {Promise<object>} The record detail.
 */
export const fetchRecord = (recordId) => api.get(`/medical-records/${recordId}`);

/**
 * Add a clinical entry.
 * @param {object} payload The record fields.
 * @returns {Promise<object>} The created record.
 */
export const createRecord = (payload) => api.post('/medical-records', payload);

/**
 * Edit a clinical entry. Every edit creates a version snapshot.
 * @param {number} recordId The record id.
 * @param {object} payload The changed fields plus an optional change note.
 * @returns {Promise<object>} The updated record.
 */
export const updateRecord = (recordId, payload) => api.patch(`/medical-records/${recordId}`, payload);

/**
 * Fetch the edit history of a clinical entry.
 * @param {number} recordId The record id.
 * @returns {Promise<Array<object>>} Historical versions, newest first.
 */
export const fetchRecordVersions = (recordId) => api.get(`/medical-records/${recordId}/versions`);
