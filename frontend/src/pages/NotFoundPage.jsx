/** Fallback screen for an unknown route. */
import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="ju-state">
      <p className="ju-state__title">Page not found</p>
      <p>The page you requested does not exist in JU_FIX.</p>
      <Link to="/dashboard" className="ju-btn ju-btn--primary">
        Return to Dashboard
      </Link>
    </div>
  );
}
