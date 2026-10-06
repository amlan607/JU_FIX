/** Component tests for the patient prescription list (FR-D3). */
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '../../test/renderWithProviders';
import MyPrescriptionsPage from './MyPrescriptionsPage';

const PRESCRIPTION = {
  id: 1,
  reference_code: 'RX-20260824-004312',
  patient_id: 5,
  doctor_id: 2,
  doctor_name: 'Dr. Rashedul Karim',
  diagnosis: 'Acute bacterial pharyngitis.',
  advice: 'Drink warm fluids and rest.',
  status: 'issued',
  issued_at: '2026-08-24T10:15:00Z',
  valid_until: '2026-09-23',
  items: [
    {
      id: 10,
      medicine_name: 'Amoxicillin',
      dosage: '500mg',
      frequency: '1+1+1',
      duration: '7 days',
      instructions: 'Take after meals.',
    },
  ],
};

/** Mock fetch so the page receives the given prescription list. */
function mockPrescriptions(prescriptions) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true, data: prescriptions, error: null }),
    })
  );
}

describe('MyPrescriptionsPage', () => {
  it('shows an empty state when nothing has been issued', async () => {
    mockPrescriptions([]);
    renderWithProviders(<MyPrescriptionsPage />);

    expect(await screen.findByText(/no prescriptions yet/i)).toBeInTheDocument();
  });

  it('lists a prescription with its reference code and doctor', async () => {
    mockPrescriptions([PRESCRIPTION]);
    renderWithProviders(<MyPrescriptionsPage />);

    expect(await screen.findByText('Acute bacterial pharyngitis.')).toBeInTheDocument();
    expect(screen.getByText(/RX-20260824-004312/)).toBeInTheDocument();
  });

  it('reveals the medicine table when opened', async () => {
    mockPrescriptions([PRESCRIPTION]);
    const user = userEvent.setup();
    renderWithProviders(<MyPrescriptionsPage />);

    await user.click(await screen.findByRole('button', { name: /view medicines/i }));

    expect(screen.getByText('Amoxicillin')).toBeInTheDocument();
    expect(screen.getByText('1+1+1')).toBeInTheDocument();
  });

  it('shows the dispensing status as a chip', async () => {
    mockPrescriptions([{ ...PRESCRIPTION, status: 'dispensed' }]);
    renderWithProviders(<MyPrescriptionsPage />);

    expect(await screen.findByText('Dispensed')).toBeInTheDocument();
  });

  it('shows an error state when loading fails', async () => {
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
    renderWithProviders(<MyPrescriptionsPage />);

    expect(await screen.findByText(/unable to load this page/i)).toBeInTheDocument();
  });
});
