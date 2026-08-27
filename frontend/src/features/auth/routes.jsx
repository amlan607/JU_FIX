/**
 * Route declarations for the accounts and authentication feature (FR-A).
 *
 * Owner: Oywon Islam (370).
 */
import ForgotPasswordPage from './ForgotPasswordPage';
import LoginPage from './LoginPage';
import ProfilePage from './ProfilePage';
import RegisterPage from './RegisterPage';
import VerifyAccountPage from './VerifyAccountPage';

export default [
  { path: '/login', element: <LoginPage />, layout: 'public' },
  { path: '/register', element: <RegisterPage />, layout: 'public' },
  { path: '/verify-account', element: <VerifyAccountPage />, layout: 'public' },
  { path: '/forgot-password', element: <ForgotPasswordPage />, layout: 'public' },
  { path: '/profile', element: <ProfilePage /> },
];
