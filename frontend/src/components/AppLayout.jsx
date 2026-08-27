/**
 * Application shell: 240px sidebar, 64px top bar and the routed page content.
 *
 * Navigation entries are filtered by role so each user only sees the areas
 * their role can reach.
 */
import { NavLink, Outlet, useLocation } from 'react-router-dom';

import { useAuth } from '../features/auth/AuthContext';

/** Sidebar entries with the roles permitted to see them. */
const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', roles: ['student', 'faculty', 'doctor', 'pharmacist', 'admin'] },
  { to: '/appointments', label: 'Appointments', roles: ['student', 'faculty'] },
  { to: '/appointments/book', label: 'Book Appointment', roles: ['student', 'faculty'] },
  { to: '/doctor/appointments', label: 'My Schedule', roles: ['doctor'] },
  { to: '/medical-records', label: 'Medical Records', roles: ['student', 'faculty'] },
  { to: '/doctor/patients', label: 'Patient Records', roles: ['doctor'] },
  { to: '/prescriptions', label: 'Prescriptions', roles: ['student', 'faculty'] },
  { to: '/doctor/prescriptions', label: 'Prescriptions', roles: ['doctor'] },
  { to: '/pharmacy/prescriptions', label: 'Dispensing', roles: ['pharmacist'] },
  { to: '/certificates', label: 'Certificates', roles: ['student', 'faculty'] },
  { to: '/doctor/certificate-requests', label: 'Certificate Review', roles: ['doctor'] },
  { to: '/admin/dashboard', label: 'Admin Dashboard', roles: ['admin'] },
  { to: '/admin/users', label: 'User Management', roles: ['admin'] },
  { to: '/admin/reports', label: 'Reports', roles: ['admin'] },
  { to: '/profile', label: 'My Profile', roles: ['student', 'faculty', 'doctor', 'pharmacist', 'admin'] },
];

export default function AppLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();

  const visibleItems = NAV_ITEMS.filter((item) => item.roles.includes(user?.role));
  const currentLabel =
    visibleItems.find((item) => location.pathname.startsWith(item.to))?.label ?? 'JU_FIX';

  return (
    <div className="ju-shell">
      <aside className="ju-sidebar">
        <div className="ju-sidebar__brand">
          JU_FIX
          <small>Medical Centre</small>
        </div>

        <nav className="ju-sidebar__nav" aria-label="Main navigation">
          {visibleItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/dashboard'}
              className={({ isActive }) =>
                `ju-sidebar__link${isActive ? ' ju-sidebar__link--active' : ''}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="ju-sidebar__user">
          <strong>{user?.full_name}</strong>
          <span>{user?.role}</span>
        </div>
      </aside>

      <div className="ju-main">
        <header className="ju-topbar">
          <span className="ju-topbar__title">{currentLabel}</span>
          <button type="button" className="ju-btn ju-btn--secondary" onClick={logout}>
            Sign Out
          </button>
        </header>

        <main className="ju-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
