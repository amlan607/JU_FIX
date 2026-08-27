/** Component tests for the administrator dashboard (FR-J3). */
import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '../../test/renderWithProviders';
import AdminDashboardPage from './AdminDashboardPage';

const METRICS = {
  report_date: '2026-08-24',
  patients_today: 12,
  appointments_today: 15,
  completed_today: 11,
  cancelled_today: 2,
  no_show_today: 2,
  prescriptions_issued_today: 9,
  certificates_pending: 3,
  pending_registrations: 2,
  active_users: 148,
  suspended_users: 1,
};

const ACTIVITY = [
  {
    id: 1,
    action: 'account.suspend',
    entity_type: 'user',
    actor_name: 'Centre Admin',
    summary: 'Policy breach.',
    created_at: '2026-08-24T09:30:00Z',
  },
];

/** Mock fetch so the dashboard receives the given payload. */
function mockDashboard(metrics, activity) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        success: true,
        data: { metrics, recent_activity: activity },
        error: null,
      }),
    })
  );
}

describe('AdminDashboardPage', () => {
  it('renders the headline KPI values', async () => {
    mockDashboard(METRICS, ACTIVITY);
    renderWithProviders(<AdminDashboardPage />);

    expect(await screen.findByText('Patients Today')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('15')).toBeInTheDocument();
  });

  it('prompts the administrator when registrations are waiting', async () => {
    mockDashboard(METRICS, ACTIVITY);
    renderWithProviders(<AdminDashboardPage />);

    expect(await screen.findByText(/action needed/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /review registrations/i })).toBeInTheDocument();
  });

  it('hides the prompt when nothing is waiting', async () => {
    mockDashboard({ ...METRICS, pending_registrations: 0 }, ACTIVITY);
    renderWithProviders(<AdminDashboardPage />);

    await screen.findByText('Patients Today');
    expect(screen.queryByText(/action needed/i)).not.toBeInTheDocument();
  });

  it('lists recent activity with the actor name', async () => {
    mockDashboard(METRICS, ACTIVITY);
    renderWithProviders(<AdminDashboardPage />);

    expect(await screen.findByText('Centre Admin')).toBeInTheDocument();
    expect(screen.getByText('account.suspend')).toBeInTheDocument();
  });

  it('shows an empty state when there is no activity', async () => {
    mockDashboard(METRICS, []);
    renderWithProviders(<AdminDashboardPage />);

    expect(await screen.findByText(/no recorded activity yet/i)).toBeInTheDocument();
  });

  it('shows an error state when the dashboard cannot be loaded', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        json: async () => ({
          success: false,
          data: null,
          error: { code: 'permission_denied', message: 'Only an administrator can do this.' },
        }),
      })
    );
    renderWithProviders(<AdminDashboardPage />);

    expect(await screen.findByText(/unable to load this page/i)).toBeInTheDocument();
  });
});
