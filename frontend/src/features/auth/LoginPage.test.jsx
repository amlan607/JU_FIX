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
  it('renders both credential fields with visible labels', () => {
    renderWithProviders(<LoginPage />);

    expect(screen.getByLabelText(/university id or email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it('shows a validation message when the form is empty', async () => {
    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);

    await user.click(screen.getByRole('button', { name: /sign in/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/enter your university id/i);
  });

  it('shows the server message when credentials are rejected', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch(
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
      )
    );

    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);

    await user.type(screen.getByLabelText(/university id or email/i), 'STU-2021-370');
    await user.type(screen.getByLabelText(/password/i), 'WrongPass1!');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/incorrect/i);
  });

  it('sends the credentials to the login endpoint', async () => {
    const fetchMock = mockFetch({
      success: true,
      data: {
        access_token: 'token-123',
        user: { id: 1, full_name: 'Oywon Islam', role: 'student' },
      },
      error: null,
    });
    vi.stubGlobal('fetch', fetchMock);

    const user = userEvent.setup();
    renderWithProviders(<LoginPage />);

    await user.type(screen.getByLabelText(/university id or email/i), 'STU-2021-370');
    await user.type(screen.getByLabelText(/password/i), 'JuFix@2026');
    await user.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/auth/login',
        expect.objectContaining({ method: 'POST' })
      );
    });
  });

  it('offers links to registration and password recovery', () => {
    renderWithProviders(<LoginPage />);

    expect(screen.getByRole('link', { name: /create account/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /forgot password/i })).toBeInTheDocument();
  });
});
