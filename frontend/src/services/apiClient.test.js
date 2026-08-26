/** Unit tests for the shared API client envelope handling. */
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError, api, clearToken, getToken, setToken } from './apiClient';

describe('apiClient token storage', () => {
  beforeEach(() => clearToken());

  it('stores and reads the access token', () => {
    setToken('sample-token');
    expect(getToken()).toBe('sample-token');
  });

  it('clears the access token on sign out', () => {
    setToken('sample-token');
    clearToken();
    expect(getToken()).toBeNull();
  });
});

describe('apiClient envelope handling', () => {
  it('returns the data field of a successful response', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({ success: true, data: { id: 7 }, error: null }),
      })
    );

    await expect(api.get('/anything')).resolves.toEqual({ id: 7 });
  });

  it('throws an ApiError carrying the code and message', async () => {
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

    await expect(api.get('/admin/reports')).rejects.toMatchObject({
      name: 'ApiError',
      status: 403,
      code: 'permission_denied',
    });
  });

  it('reports a network error when fetch rejects', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));

    await expect(api.get('/health')).rejects.toBeInstanceOf(ApiError);
  });
});
