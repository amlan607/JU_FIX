const CATEGORY_LABELS = {
  appointment_reminder: 'Appointment reminder',
  appointment_update: 'Appointment update',
  medicine_reminder: 'Medicine reminder',
  queue_update: 'Queue update',
  record_update: 'Record update',
  certificate_update: 'Certificate update',
  emergency: 'Emergency alert',
  security: 'Account security',
};

export function categoryLabel(category) {
  return CATEGORY_LABELS[category] ?? 'Notification';
}

export function isUrgent(category) {
  return category === 'emergency' || category === 'security';
}

export function relativeTime(value) {
  const elapsed = Math.max(0, Date.now() - new Date(value).getTime());
  const minutes = Math.floor(elapsed / 60000);
  if (minutes < 1) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export function targetPath(notification) {
  if (notification.entity_type === 'appointment') return '/appointments';
  return null;
}
