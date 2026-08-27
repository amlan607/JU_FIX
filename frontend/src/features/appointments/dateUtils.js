/**
 * Date helpers for the booking screens.
 *
 * All values exchanged with the API use ISO 8601 (Quick Reference: date/time format).
 */

/** Number of days ahead a patient may book. Mirrors the backend rule. */
export const MAX_ADVANCE_DAYS = 30;

/**
 * Return a date as an ISO 8601 `YYYY-MM-DD` string.
 * @param {Date} date The date to format.
 * @returns {string} The ISO date string.
 */
export function toIsoDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * Today as an ISO 8601 date string.
 * @returns {string} Today's date.
 */
export function todayIso() {
  return toIsoDate(new Date());
}

/**
 * The last bookable date as an ISO 8601 string.
 * @returns {string} The maximum bookable date.
 */
export function maxBookableIso() {
  const limit = new Date();
  limit.setDate(limit.getDate() + MAX_ADVANCE_DAYS);
  return toIsoDate(limit);
}

/**
 * Report whether an ISO date falls on a Friday, when the centre is closed.
 * @param {string} isoDate An ISO 8601 date string.
 * @returns {boolean} True when the date is a Friday.
 */
export function isClosedDay(isoDate) {
  if (!isoDate) return false;
  const [year, month, day] = isoDate.split('-').map(Number);
  return new Date(year, month - 1, day).getDay() === 5;
}

/**
 * Format an ISO date for display, for example `Mon, 25 Aug 2026`.
 * @param {string} isoDate An ISO 8601 date string.
 * @returns {string} A readable date.
 */
export function formatDate(isoDate) {
  if (!isoDate) return '';
  const [year, month, day] = isoDate.split('-').map(Number);
  return new Date(year, month - 1, day).toLocaleDateString('en-GB', {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

/**
 * Trim a `HH:MM:SS` value to `HH:MM` for display.
 * @param {string} value A time string from the API.
 * @returns {string} The shortened time.
 */
export function formatTime(value) {
  return value ? value.slice(0, 5) : '';
}
