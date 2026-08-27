/** Component tests for the My Appointments screen (FR-C3). */
import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '../../test/renderWithProviders';
import MyAppointmentsPage from './MyAppointmentsPage';

const BOOKED = {
  id: 1,
  doctor_name: 'Dr. Rashedul Karim',
  doctor_speciality: 'General Medicine',
  appointment_date: '2026-09-01',
  start_time: '10:00:00',
  end_time: '10:20:00',
  reason: 'Persistent fever',
  status: 'booked',
};

const COMPLETED = { ...BOOKED, id: 2, status: 'completed' };

/** Mock fetch so the page receives the given appointment list. */
function mockList(appointments) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true, data: appointments, error: null }),
    })
  );
}

describe('MyAppointmentsPage', () => {
  it('shows an empty state when there are no bookings', async () => {
    mockList([]);
    renderWithProviders(<MyAppointmentsPage />);

    expect(await screen.findByText(/no appointments yet/i)).toBeInTheDocument();
  });

  it('lists a booking with its doctor and status', async () => {
    mockList([BOOKED]);
    renderWithProviders(<MyAppointmentsPage />);

    expect(await screen.findByText('Dr. Rashedul Karim')).toBeInTheDocument();
    expect(screen.getByText('Booked')).toBeInTheDocument();
  });

  it('offers reschedule and cancel while the booking is editable', async () => {
    mockList([BOOKED]);
    renderWithProviders(<MyAppointmentsPage />);

    expect(await screen.findByRole('button', { name: /reschedule/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^cancel$/i })).toBeInTheDocument();
  });

  it('hides the actions once the appointment is completed', async () => {
    mockList([COMPLETED]);
    renderWithProviders(<MyAppointmentsPage />);

    expect(await screen.findByText(/no action available/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /reschedule/i })).not.toBeInTheDocument();
  });

  it('shows an error state when the list cannot be loaded', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({
          success: false,
          data: null,
          error: { code: 'internal_error', message: 'An unexpected error occurred.' },
        }),
      })
    );
    renderWithProviders(<MyAppointmentsPage />);

    expect(await screen.findByText(/unable to load this page/i)).toBeInTheDocument();
  });
});
