/**
 * Thin HTTP client for the JU_FIX REST API.
 *
 * Every backend response uses the envelope
 * `{ success, data, error }`. This module unwraps that envelope so feature code
 * works with plain data and a single `ApiError` type (Coding Standard 3.5).
 */

const API_BASE = '/api';
const TOKEN_STORAGE_KEY = 'ju_fix_access_token';

/** Error thrown for any non successful API response. */
export class ApiError extends Error {
  /**
   * @param {string} message Human readable message safe to display.
   * @param {number} status HTTP status code returned by the API.
   * @param {string} code Stable machine readable error code.
   * @param {unknown} details Optional structured field level detail.
   */
  constructor(message, status, code = 'error', details = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

/**
 * Read the stored access token.
 * @returns {string | null} The token, or null when signed out.
 */
export function getToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

/**
 * Persist the access token for later requests.
 * @param {string} token The JWT returned by the login endpoint.
 */
export function setToken(token) {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

/** Remove the stored access token. */
export function clearToken() {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

/**
 * Send a request to the JU_FIX API and unwrap the standard envelope.
 *
 * @param {string} path Path below `/api`, for example `/auth/login`.
 * @param {{ method?: string, body?: object, auth?: boolean, query?: object }} options Request options.
 * @returns {Promise<any>} The `data` field of a successful response.
 * @throws {ApiError} When the request fails or the API reports an error.
 */
export async function request(path, options = {}) {
  const { method = 'GET', body, auth = true, query } = options;

  let url = `${API_BASE}${path}`;
  if (query) {
    const params = new URLSearchParams();
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params.append(key, String(value));
      }
    });
    const qs = params.toString();
    if (qs) url += `?${qs}`;
  }

  const headers = { 'Content-Type': 'application/json' };
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(url, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError('Cannot reach the JU_FIX server. Check your connection.', 0, 'network_error');
  }

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok || !payload || payload.success === false) {
    const apiError = payload?.error ?? {};
    throw new ApiError(
      apiError.message || 'The request could not be completed.',
      response.status,
      apiError.code || 'error',
      apiError.details ?? null
    );
  }

  return payload.data;
}

export const api = {
  /** @param {string} path @param {object} [query] */
  get: (path, query) => request(path, { method: 'GET', query }),
  /** @param {string} path @param {object} [body] @param {object} [opts] */
  post: (path, body, opts = {}) => request(path, { method: 'POST', body, ...opts }),
  /** @param {string} path @param {object} [body] */
  patch: (path, body) => request(path, { method: 'PATCH', body }),
  /** @param {string} path */
  delete: (path) => request(path, { method: 'DELETE' }),
};
