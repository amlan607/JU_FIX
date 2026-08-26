/**
 * Status chip that communicates state with text and colour together.
 *
 * The UI standard requires status to be readable without relying on colour
 * alone, so the label text is always rendered.
 */

/** Maps a domain status to a chip tone. */
const TONE_BY_STATUS = {
  active: 'success',
  approved: 'success',
  completed: 'success',
  issued: 'success',
  dispensed: 'success',
  confirmed: 'success',
  verified: 'success',

  pending: 'warning',
  pending_approval: 'warning',
  pending_verification: 'warning',
  submitted: 'warning',
  booked: 'warning',
  draft: 'warning',

  rejected: 'error',
  cancelled: 'error',
  suspended: 'error',
  no_show: 'error',
  expired: 'error',
};

/** Turns `pending_approval` into `Pending approval`. */
function toLabel(status) {
  const text = String(status).replaceAll('_', ' ');
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export default function StatusChip({ status, label }) {
  const tone = TONE_BY_STATUS[status] ?? 'neutral';
  return <span className={`ju-chip ju-chip--${tone}`}>{label ?? toLabel(status)}</span>;
}
