/** Component test for the patient prescription list (FR-D3). */
import { screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';

import { renderWithProviders } from '../../test/renderWithProviders';
import { MyPrescriptionsPage } from './PrescriptionPages';

it('lists a prescription with its medicines', async () => {
  const row = { id: 1, reference_code: 'RX-1', status: 'issued', patient_name: 'A', diagnosis: 'Flu', items: [{ id: 1, medicine_name: 'Amoxicillin', dosage: '500mg', frequency: '1+1+1', duration: '7 days' }] };
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ success: true, data: [row], error: null }) }));
  renderWithProviders(<MyPrescriptionsPage />);
  expect(await screen.findByText(/Amoxicillin 500mg/)).toBeInTheDocument();
});
