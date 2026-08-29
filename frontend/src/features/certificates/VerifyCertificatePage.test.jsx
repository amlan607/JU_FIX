/** Component tests for the public certificate verification screen (FR-F4). */
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '../../test/renderWithProviders';
import VerifyCertificatePage from './VerifyCertificatePage';

/** Mock fetch so verification returns the given payload. */
function mockVerify(data) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ success: true, data, error: null }),
    })
  );
}

describe('VerifyCertificatePage', () => {
  it('renders the reference field', () => {
    renderWithProviders(<VerifyCertificatePage />);

    expect(screen.getByLabelText(/certificate reference id/i)).toBeInTheDocument();
  });

  it('asks for a reference when the field is empty', async () => {
    const user = userEvent.setup();
    renderWithProviders(<VerifyCertificatePage />);

    await user.click(screen.getByRole('button', { name: /verify certificate/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/enter the reference id/i);
  });

  it('confirms a genuine certificate with its leave period', async () => {
    mockVerify({
      valid: true,
      reference_id: 'JUMC-2026-004312',
      patient_name: 'Shadman Rahman',
      patient_university_id: 'STU-2021-376',
      issued_by: 'Dr. Rashedul Karim',
      leave_start: '2026-08-24',
      leave_end: '2026-08-26',
      leave_days: 3,
      message: 'This is a genuine certificate issued by the JU Medical Centre.',
    });

    const user = userEvent.setup();
    renderWithProviders(<VerifyCertificatePage />);

    await user.type(screen.getByLabelText(/certificate reference id/i), 'JUMC-2026-004312');
    await user.click(screen.getByRole('button', { name: /verify certificate/i }));

    expect(await screen.findByText('Genuine certificate')).toBeInTheDocument();
    expect(screen.getByText(/shadman rahman/i)).toBeInTheDocument();
  });

  it('reports an unknown reference as not verified', async () => {
    mockVerify({ valid: false, message: 'No approved certificate matches that reference ID.' });

    const user = userEvent.setup();
    renderWithProviders(<VerifyCertificatePage />);

    await user.type(screen.getByLabelText(/certificate reference id/i), 'JUMC-2026-000000');
    await user.click(screen.getByRole('button', { name: /verify certificate/i }));

    expect(await screen.findByText('Not verified')).toBeInTheDocument();
  });

  it('never displays a medical reason in the result', async () => {
    mockVerify({
      valid: true,
      reference_id: 'JUMC-2026-004312',
      patient_name: 'Shadman Rahman',
      patient_university_id: 'STU-2021-376',
      issued_by: 'Dr. Rashedul Karim',
      leave_start: '2026-08-24',
      leave_end: '2026-08-26',
      leave_days: 3,
      message: 'This is a genuine certificate issued by the JU Medical Centre.',
    });

    const user = userEvent.setup();
    renderWithProviders(<VerifyCertificatePage />);

    await user.type(screen.getByLabelText(/certificate reference id/i), 'JUMC-2026-004312');
    await user.click(screen.getByRole('button', { name: /verify certificate/i }));

    await screen.findByText('Genuine certificate');
    expect(screen.queryByText(/diagnosis/i)).not.toBeInTheDocument();
  });
});
