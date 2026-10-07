/** Component test for the patient timeline (FR-D3). */
import { screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';

import { renderWithProviders } from '../../test/renderWithProviders';
import { MyRecordsPage } from './RecordPages';

it('lists a record with its diagnosis', async () => {
  const row = { id: 1, title: 'Viral fever', version: 1, visit_date: '2026-08-20', doctor_name: 'Dr. Karim', diagnosis: 'Viral fever' };
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ success: true, data: [row], error: null }) }));
  renderWithProviders(<MyRecordsPage />);
  expect(await screen.findByText(/Dr\. Karim/)).toBeInTheDocument();
});
