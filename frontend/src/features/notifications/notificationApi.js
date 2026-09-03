import { api } from '../../services/apiClient';

export function fetchNotifications({ unread_only = false } = {}) {
  return api.get('/notifications', { unread_only });
}

export function markRead(notificationId) {
  return api.patch(`/notifications/${notificationId}/read`);
}

export function markAllRead() {
  return api.patch('/notifications/read-all');
}

export function fetchPreferences() {
  return api.get('/notifications/preferences');
}

export function updatePreference(payload) {
  return api.patch('/notifications/preferences', payload);
}
