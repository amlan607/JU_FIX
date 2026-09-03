import { describe, expect, it } from 'vitest';

import { categoryLabel, isUrgent, relativeTime, targetPath } from './notificationFormat';

describe('notificationFormat', () => {
  it('formats known categories', () => {
    expect(categoryLabel('appointment_reminder')).toBe('Appointment reminder');
  });
  it('uses a fallback for unknown categories', () => {
    expect(categoryLabel('other')).toBe('Notification');
  });
  it('identifies security and emergency notifications as urgent', () => {
    expect(isUrgent('security')).toBe(true);
    expect(isUrgent('emergency')).toBe(true);
    expect(isUrgent('appointment_update')).toBe(false);
  });
  it('formats recent timestamps', () => {
    expect(relativeTime(new Date().toISOString())).toBe('Just now');
  });
  it('formats minute, hour, and day timestamps', () => {
    expect(relativeTime(new Date(Date.now() - 5 * 60000).toISOString())).toBe('5m ago');
    expect(relativeTime(new Date(Date.now() - 2 * 3600000).toISOString())).toBe('2h ago');
    expect(relativeTime(new Date(Date.now() - 3 * 86400000).toISOString())).toBe('3d ago');
  });
  it('links appointment notifications to appointments', () => {
    expect(targetPath({ entity_type: 'appointment' })).toBe('/appointments');
    expect(targetPath({ entity_type: 'prescription' })).toBeNull();
  });
});
