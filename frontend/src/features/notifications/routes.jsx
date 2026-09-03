import NotificationsPage from './NotificationsPage';
import NotificationPreferencesPage from './NotificationPreferencesPage';

export default [
	{ path: '/notifications', element: <NotificationsPage /> },
	{ path: '/notifications/preferences', element: <NotificationPreferencesPage /> },
];
