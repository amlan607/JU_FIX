/** Route declarations for the admin dashboard and reporting. Owner: Amlan Dutta Rahul (360). */
import { DashboardPage, ReportsPage, UsersPage } from './AdminPages';

const ADMIN = ['admin'];

export default [
  { path: '/admin/dashboard', element: <DashboardPage />, roles: ADMIN },
  { path: '/admin/users', element: <UsersPage />, roles: ADMIN },
  { path: '/admin/reports', element: <ReportsPage />, roles: ADMIN },
];
