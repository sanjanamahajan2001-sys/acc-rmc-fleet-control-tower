import { env } from '../config/env';
import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import { APP_CONSTANTS } from '../config/constants';
import { useAuthStore } from '../store/auth';

export class APIError extends Error {
  constructor(
    public code: string,
    message: string,
    public status?: number,
    public details?: unknown
  ) {
    super(message);
    this.name = 'APIError';
  }
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: env.VITE_API_BASE_URL,
  timeout: APP_CONSTANTS.SLA.API_TIMEOUT_MS,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Inject Bearer Token & Correlation ID
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = useAuthStore.getState().token;
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    const correlationId =
      typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
        ? crypto.randomUUID()
        : Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15);
    if (config.headers) {
      config.headers['X-Correlation-ID'] = correlationId;
    }

    return config;
  },
  (error: AxiosError) => Promise.reject(error)
);

// Response Interceptor: Format API Errors & Handle 401 Unauthorized
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ error?: { code?: string; message?: string; details?: unknown } }>) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().clearAuth();
    }

    const errorPayload = error.response?.data?.error;
    const apiError = new APIError(
      errorPayload?.code || 'NETWORK_ERROR',
      errorPayload?.message || error.message || 'An unexpected network error occurred',
      error.response?.status,
      errorPayload?.details
    );

    return Promise.reject(apiError);
  }
);
