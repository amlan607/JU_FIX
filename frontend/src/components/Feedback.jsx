/**
 * Shared loading, empty, error and alert presentation components.
 *
 * The UI standard requires every screen to define loading, empty, error,
 * disabled, success and permission denied states. Centralising them here keeps
 * those states consistent across all twelve features.
 */

/** Inline banner for success, error, warning or informational messages. */
export function Alert({ tone = 'info', children }) {
  if (!children) return null;
  return (
    <div className={`ju-alert ju-alert--${tone}`} role={tone === 'error' ? 'alert' : 'status'}>
      {children}
    </div>
  );
}

/** Placeholder shown while a request is in flight. */
export function LoadingState({ message = 'Loading…' }) {
  return (
    <div className="ju-state" role="status">
      <p>{message}</p>
    </div>
  );
}

/** Placeholder shown when a list has no rows. */
export function EmptyState({ title = 'Nothing to show yet', hint = '' }) {
  return (
    <div className="ju-state">
      <p className="ju-state__title">{title}</p>
      {hint && <p>{hint}</p>}
    </div>
  );
}

/** Placeholder shown when a request fails. */
export function ErrorState({ message = 'Something went wrong.', onRetry }) {
  return (
    <div className="ju-state">
      <p className="ju-state__title">Unable to load this page</p>
      <p>{message}</p>
      {onRetry && (
        <button type="button" className="ju-btn ju-btn--secondary" onClick={onRetry}>
          Try Again
        </button>
      )}
    </div>
  );
}

/** Placeholder shown when the signed in role may not view a screen. */
export function PermissionDenied() {
  return (
    <div className="ju-state">
      <p className="ju-state__title">Permission denied</p>
      <p>Your role does not have access to this page.</p>
    </div>
  );
}
