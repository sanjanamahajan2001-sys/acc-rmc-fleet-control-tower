export interface APIResponseMeta {
  timestamp: string;
  correlation_id: string;
  request_id: string;
  api_version: string;
  request_duration_ms: number;
}

export interface APIErrorDetail {
  code: string;
  message: string;
  details?: Record<string, unknown> | Array<unknown> | null;
}

export interface APIResponse<T = unknown> {
  success: boolean;
  data: T | null;
  error: APIErrorDetail | null;
  meta: APIResponseMeta;
}
