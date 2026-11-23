import { describe, it, expect, vi } from 'vitest';
import { apiClient, APIError } from '../api/client';
import { useAuthStore } from '../store/auth';

describe('Axios API Client Layer', () => {
  it('injects Bearer token and Correlation ID headers into requests', async () => {
    useAuthStore.getState().setAuth('test_access_token_123', {
      sub: 'user_1',
      jti: 'jti_1',
      type: 'access',
      exp: 9999999999,
      iat: 1000000000,
    });

    const mockAdapter = vi.fn().mockResolvedValue({
      data: { success: true, data: {}, error: null, meta: {} },
      status: 200,
      headers: {},
      config: {},
    });

    apiClient.defaults.adapter = mockAdapter;

    await apiClient.get('/test-endpoint');

    expect(mockAdapter).toHaveBeenCalled();
    const config = mockAdapter.mock.calls[0][0];
    expect(config.headers['Authorization']).toBe('Bearer test_access_token_123');
    expect(config.headers['X-Correlation-ID']).toBeDefined();
  });

  it('handles 401 response status by clearing auth state', async () => {
    const mockAdapter = vi.fn().mockRejectedValue({
      response: {
        status: 401,
        data: { error: { code: 'UNAUTHORIZED', message: 'Token expired' } },
      },
    });

    apiClient.defaults.adapter = mockAdapter;

    try {
      await apiClient.get('/protected-test');
    } catch (err) {
      expect(err).toBeInstanceOf(APIError);
      expect(useAuthStore.getState().token).toBeNull();
    }
  });
});
