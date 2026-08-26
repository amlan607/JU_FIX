/** Test helper that renders a component inside the router and auth providers. */
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import { AuthProvider } from '../features/auth/AuthContext';

/**
 * Render `ui` wrapped in the providers every JU_FIX screen expects.
 *
 * @param {JSX.Element} ui The component under test.
 * @param {{route?: string}} options Initial router entry.
 * @returns {import('@testing-library/react').RenderResult}
 */
export function renderWithProviders(ui, { route = '/' } = {}) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AuthProvider>{ui}</AuthProvider>
    </MemoryRouter>
  );
}
