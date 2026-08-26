/**
 * Root component and router.
 *
 * Feature screens are mounted from the route registry, so this file stays stable
 * while the six feature branches are merged one after another.
 */
import { Navigate, Route, Routes } from 'react-router-dom';

import AppLayout from './components/AppLayout';
import ProtectedRoute from './components/ProtectedRoute';
import { AuthProvider } from './features/auth/AuthContext';
import DashboardPage from './pages/DashboardPage';
import NotFoundPage from './pages/NotFoundPage';
import { appRoutes, publicRoutes } from './routes/registry';

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {publicRoutes().map((route) => (
          <Route key={route.path} path={route.path} element={route.element} />
        ))}

        <Route
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/dashboard" element={<DashboardPage />} />

          {appRoutes().map((route) => (
            <Route
              key={route.path}
              path={route.path}
              element={
                route.roles ? (
                  <ProtectedRoute roles={route.roles}>{route.element}</ProtectedRoute>
                ) : (
                  route.element
                )
              }
            />
          ))}

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </AuthProvider>
  );
}
