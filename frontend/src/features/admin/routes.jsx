/**
 * Route declarations for the admin dashboard and reporting (FR-J).
 *
 * Owner: Amlan Dutta Rahul (360).
 */
import AdminDashboardPage from './AdminDashboardPage';
import ReportsPage from './ReportsPage';
import UserManagementPage from './UserManagementPage';

export default [
  { path: '/admin/dashboard', element: <AdminDashboardPage />, roles: ['admin'] },
  { path: '/admin/users', element: <UserManagementPage />, roles: ['admin'] },
  { path: '/admin/reports', element: <ReportsPage />, roles: ['admin'] },
];
