import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '../../test/renderWithProviders';
import NotificationsPage from './NotificationsPage';

const notification = {
  id: 1,
  category: 'appointment_reminder',
  title: 'Appointment soon',
  body: 'Your appointment is tomorrow.',
  entity_type: 'appointment',
  entity_id: 3,
  is_read: false,
  created_at: new Date().toISOString(),
};

function response(data, ok = true) {
  return { ok, status: ok ? 200 : 500, json: async () => ({ success: ok, data, error: ok ? null : { message: 'Failed' } }) };
}

describe('NotificationsPage', () => {
  it('shows an empty state', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ unread_count: 0, notifications: [] })));
    renderWithProviders(<NotificationsPage />);
    expect(await screen.findByText(/no notifications yet/i)).toBeInTheDocument();
  });

  it('lists unread notifications and the badge count', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ unread_count: 1, notifications: [notification] })));
    renderWithProviders(<NotificationsPage />);
    expect(await screen.findByText('Appointment soon')).toBeInTheDocument();
    expect(screen.getByText(/1 unread notification/)).toBeInTheDocument();
    expect(screen.getByText('New')).toBeInTheDocument();
  });

  it('filters to unread notifications', async () => {
    const fetchMock = vi.fn().mockResolvedValue(response({ unread_count: 0, notifications: [] }));
    vi.stubGlobal('fetch', fetchMock);
    renderWithProviders(<NotificationsPage />);
    await screen.findByText(/no notifications yet/i);
    await userEvent.click(screen.getByRole('button', { name: 'Unread' }));
    await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith('/api/notifications?unread_only=true', expect.anything()));
  });

  it('marks all notifications read', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(response({ unread_count: 1, notifications: [notification] }))
      .mockResolvedValueOnce(response({ marked: 1 }))
      .mockResolvedValue(response({ unread_count: 0, notifications: [] }));
    vi.stubGlobal('fetch', fetchMock);
    renderWithProviders(<NotificationsPage />);
    await userEvent.click(await screen.findByRole('button', { name: /mark all read/i }));
    expect(await screen.findByText(/marked 1 notification as read/i)).toBeInTheDocument();
  });

  it('shows a load error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(null, false)));
    renderWithProviders(<NotificationsPage />);
    expect(await screen.findByText(/unable to load this page/i)).toBeInTheDocument();
  });
});
