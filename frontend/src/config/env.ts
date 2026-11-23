export interface EnvConfig {
  VITE_BASE_URL: string;
  VITE_API_BASE_URL: string;
  VITE_ENVIRONMENT: string;
  VITE_APP_TITLE: string;
}

export const env: EnvConfig = {
  VITE_BASE_URL: import.meta.env.VITE_BASE_URL || '/demo-fleet',
  VITE_API_BASE_URL: import.meta.env.VITE_API_BASE_URL || '/demo-api/v1',
  VITE_ENVIRONMENT: import.meta.env.VITE_ENVIRONMENT || 'production',
  VITE_APP_TITLE: import.meta.env.VITE_APP_TITLE || 'Demo Fleet Control Tower',
};
