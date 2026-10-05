/** Component tests for the patient health record timeline (FR-D3). */
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '../../test/renderWithProviders';
import MyRecordsPage from './MyRecordsPage';

const RECORD = {
  id: 1,
  patient_id: 5,
  doctor_id: 2,
  doctor_name: 'Dr. Rashedul Karim',
  record_type: 'consultation',
  visit_date: '2026-08-20',
  title: 'Acute viral fever',
  diagnosis: 'Viral fever with mild dehydration.',
  symptoms: 'Fever 102F for three days.',
  treatment: 'Paracetamol 500mg and rest.',
  version: 1,
};

/** Mock fetch so the timeline receives the given record list. */
function mockRecords(records) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true, data: records, error: null }),
    })
  );
}

describe('MyRecordsPage', () => {
  it('shows an empty state when there is no history', async () => {
    mockRecords([]);
    renderWithProviders(<MyRecordsPage />);

    expect(await screen.findByText(/no medical records yet/i)).toBeInTheDocument();
  });

  it('lists an entry with its doctor and visit date', async () => {
    mockRecords([RECORD]);
    renderWithProviders(<MyRecordsPage />);

    expect(await screen.findByText('Acute viral fever')).toBeInTheDocument();
    expect(screen.getByText(/dr\. rashedul karim/i)).toBeInTheDocument();
  });

  it('reveals the clinical detail when the entry is opened', async () => {
    mockRecords([RECORD]);
    const user = userEvent.setup();
    renderWithProviders(<MyRecordsPage />);

    await user.click(await screen.findByRole('button', { name: /view details/i }));

    expect(screen.getByText('Viral fever with mild dehydration.')).toBeInTheDocument();
    expect(screen.getByText('Paracetamol 500mg and rest.')).toBeInTheDocument();
  });

  it('hides the clinical detail again on a second click', async () => {
    mockRecords([RECORD]);
    const user = userEvent.setup();
    renderWithProviders(<MyRecordsPage />);

    const toggle = await screen.findByRole('button', { name: /view details/i });
    await user.click(toggle);
    await user.click(screen.getByRole('button', { name: /hide details/i }));

    expect(screen.queryByText('Viral fever with mild dehydration.')).not.toBeInTheDocument();
  });

  it('shows an error state when the timeline cannot be loaded', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        json: async () => ({
          success: false,
          data: null,
          error: { code: 'permission_denied', message: 'Your role does not permit this action.' },
        }),
      })
    );
    renderWithProviders(<MyRecordsPage />);

    expect(await screen.findByText(/unable to load this page/i)).toBeInTheDocument();
  });
});
