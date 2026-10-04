/** Component tests for the login screen (FR-A4). */
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '../../test/renderWithProviders';
import LoginPage from './LoginPage';

/** Build a fetch mock returning the standard JU_FIX envelope. */
function mockFetch(response, ok = true, status = 200) {
  return vi.fn().mockResolvedValue({ ok, status, json: async () => response });
}

describe('LoginPage', () => {
  it('submits credentials, shows a server error, and links to account actions', async () => {
    const fetchMock = mockFetch(
      {
        success: false,
        data: null,
        error: {
          code: 'authentication_error',
          message: 'The university ID or password is incorrect.',
        },
      },
      false,
      401
    );
    vi.stubGlobal(
      'fetch',
      fetchMock
    );

    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);

    expect(screen.getByLabelText(/university id or email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /create account/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /forgot password/i })).toBeInTheDocument();

    await user.type(screen.getByLabelText(/university id or email/i), 'STU-2021-370');
    await user.type(screen.getByLabelText(/password/i), 'WrongPass1!');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/incorrect/i);
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/auth/login',
        expect.objectContaining({ method: 'POST' })
      );
    });
  });
});
