import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '../../test/renderWithProviders';
import NotificationPreferencesPage from './NotificationPreferencesPage';

const preferences = [
  {
    category: 'appointment_reminder',
    label: 'Appointment Reminders',
    description: 'Before a scheduled visit.',
    in_app_enabled: true,
    email_enabled: true,
    can_disable: true,
  },
  {
    category: 'security',
    label: 'Account Security',
    description: 'Sign-ins and account changes.',
    in_app_enabled: true,
    email_enabled: true,
    can_disable: false,
  },
];

function mockPreferences(updateResponse = preferences) {
  const fetchMock = vi.fn()
    .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ success: true, data: preferences, error: null }) })
    .mockResolvedValue({ ok: true, status: 200, json: async () => ({ success: true, data: updateResponse, error: null }) });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

describe('NotificationPreferencesPage', () => {
  it('shows loading then all available categories', async () => {
    mockPreferences();
    renderWithProviders(<NotificationPreferencesPage />);
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(await screen.findByText('Appointment Reminders')).toBeInTheDocument();
    expect(screen.getByText('Account Security')).toBeInTheDocument();
  });

  it('locks mandatory categories', async () => {
    mockPreferences();
    renderWithProviders(<NotificationPreferencesPage />);
    await screen.findByText('Account Security');
    expect(screen.getByLabelText('In-app notifications for Account Security')).toBeDisabled();
    expect(screen.getByText(/cannot be switched off/i)).toBeInTheDocument();
  });

  it('updates an optional channel', async () => {
    const fetchMock = mockPreferences();
    renderWithProviders(<NotificationPreferencesPage />);
    await screen.findByText('Appointment Reminders');
    await userEvent.click(screen.getByLabelText('In-app notifications for Appointment Reminders'));
    await waitFor(() => expect(fetchMock).toHaveBeenLastCalledWith('/api/notifications/preferences', expect.objectContaining({ method: 'PATCH' })));
  });

  it('shows a load error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500, json: async () => ({ success: false, error: { message: 'Failed' } }) }));
    renderWithProviders(<NotificationPreferencesPage />);
    expect(await screen.findByText(/unable to load this page/i)).toBeInTheDocument();
  });
});
