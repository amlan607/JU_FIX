/**
 * Record type labels shared by the health record screens.
 *
 * The values mirror `app.core.constants.RecordType` on the backend.
 */

/** Options for the record type selector and filter. */
export const RECORD_TYPES = [
  { value: 'consultation', label: 'Consultation' },
  { value: 'diagnosis', label: 'Diagnosis' },
  { value: 'lab_result', label: 'Lab Result' },
  { value: 'vaccination', label: 'Vaccination' },
  { value: 'note', label: 'Clinical Note' },
];

/**
 * Turn a stored record type into its display label.
 * @param {string} value The stored record type.
 * @returns {string} The human readable label.
 */
export function recordTypeLabel(value) {
  return RECORD_TYPES.find((type) => type.value === value)?.label ?? 'Clinical Note';
}

/**
 * Format an ISO date for display in the timeline.
 * @param {string} isoDate An ISO 8601 date string.
 * @returns {string} A readable date, or an empty string.
 */
export function formatVisitDate(isoDate) {
  if (!isoDate) return '';
  const [year, month, day] = isoDate.split('-').map(Number);
  return new Date(year, month - 1, day).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}
