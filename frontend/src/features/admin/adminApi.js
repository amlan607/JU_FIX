/**
 * API calls for the admin dashboard and reporting (FR-J1 to FR-J5).
 */
import { api } from '../../services/apiClient';

/**
 * Fetch the daily metrics and the recent activity feed.
 * @param {string} [date] Optional ISO date; defaults to today.
 * @returns {Promise<{metrics: object, recent_activity: Array<object>}>} Dashboard payload.
 */
export const fetchDashboard = (date) => api.get('/admin/dashboard', { date });

/**
 * Fetch registrations awaiting an administrator decision.
 * @returns {Promise<Array<object>>} Pending registrations.
 */
export const fetchPendingRegistrations = () => api.get('/admin/registrations/pending');

/**
 * Approve or reject a pending registration.
 * @param {number} userId The account being decided.
 * @param {{approve: boolean, reason: string|null}} payload The decision.
 * @returns {Promise<object>} The updated account.
 */
export const decideRegistration = (userId, payload) =>
  api.patch(`/admin/registrations/${userId}/decision`, payload);

/**
 * Fetch accounts for the user management screen.
 * @param {{role?: string, status?: string, search?: string}} filters Optional filters.
 * @returns {Promise<Array<object>>} Matching accounts.
 */
export const fetchUsers = (filters = {}) => api.get('/admin/users', filters);

/**
 * Suspend or reactivate an account.
 * @param {number} userId The account being changed.
 * @param {{suspend: boolean, reason: string|null}} payload The action.
 * @returns {Promise<object>} The updated account.
 */
export const setAccountStatus = (userId, payload) =>
  api.patch(`/admin/users/${userId}/status`, payload);

/**
 * Generate the platform analytics report.
 * @param {string} [start] ISO start date.
 * @param {string} [end] ISO end date.
 * @returns {Promise<object>} The report.
 */
export const fetchReport = (start, end) => api.get('/admin/reports', { start, end });

/**
 * Read the operational settings.
 * @returns {Promise<object>} The current settings.
 */
export const fetchSettings = () => api.get('/admin/settings');

/**
 * Change one or more operational settings.
 * @param {object} payload The settings to change.
 * @returns {Promise<object>} The settings after the change.
 */
export const updateSettings = (payload) => api.patch('/admin/settings', payload);

/**
 * Build the CSV export URL for the given window.
 *
 * The browser follows this link directly, so the endpoint returns a file rather
 * than the standard JSON envelope.
 *
 * @param {string} start ISO start date.
 * @param {string} end ISO end date.
 * @returns {string} The export URL.
 */
export const reportExportUrl = (start, end) =>
  `/api/admin/reports/export?start=${start}&end=${end}`;
