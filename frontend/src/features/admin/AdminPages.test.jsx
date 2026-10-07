/** Component test for the admin dashboard (FR-J3). */
import { screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';

import { renderWithProviders } from '../../test/renderWithProviders';
import { DashboardPage } from './AdminPages';

it('shows the headline figures', async () => {
  const metrics = { appointments_today: 15, patients_today: 12, completed_today: 11, pending_registrations: 0, active_users: 148 };
  const reply = (data) => ({ ok: true, status: 200, json: async () => ({ success: true, data, error: null }) });
  vi.stubGlobal('fetch', vi.fn((url) => Promise.resolve(reply(url.includes('dashboard') ? { metrics } : []))));
  renderWithProviders(<DashboardPage />);
  expect(await screen.findByText('Patients Today')).toBeInTheDocument();
  expect(screen.getByText('12')).toBeInTheDocument();
});
