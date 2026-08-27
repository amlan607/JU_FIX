/**
 * Route guard for authenticated and role restricted screens.
 *
 * This is a usability guard only. Every protected endpoint repeats the same
 * check on the backend, so removing this component in the browser grants nothing.
 */
import { Navigate, useLocation } from 'react-router-dom';

import { useAuth } from '../features/auth/AuthContext';
import { LoadingState, PermissionDenied } from './Feedback';

export default function ProtectedRoute({ children, roles = null }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) return <LoadingState message="Checking your session…" />;
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  if (roles && !roles.includes(user.role)) return <PermissionDenied />;

  return children;
}
