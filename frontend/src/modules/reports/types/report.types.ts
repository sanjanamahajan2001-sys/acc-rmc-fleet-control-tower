export enum ReportFormat {
  PDF = 'PDF',
  XLSX = 'XLSX',
  JSON = 'JSON',
}

export enum ReportStatus {
  QUEUED = 'QUEUED',
  PROCESSING = 'PROCESSING',
  RUNNING = 'RUNNING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  SCOPE_VALIDATION_FAILED = 'SCOPE_VALIDATION_FAILED',
  NO_DATA = 'NO_DATA',
  PURGED = 'PURGED',
}

export enum ScopeValidationStatus {
  VALIDATED = 'VALIDATED',
  INVALID_SCOPE = 'INVALID_SCOPE',
  PARTIAL = 'PARTIAL',
}

export interface ReportScopeDTO {
  plant_id?: string;
  customer_id?: string;
  operation_date?: string;
  shift?: string;
  dataset_type?: string;
  start_date?: string;
  end_date?: string;
  [key: string]: unknown;
}

export interface ReportRequestDTO {
  report_id: string;
  format?: ReportFormat;
  scope?: ReportScopeDTO;
  requested_by?: string;
}

export interface ReportDefinitionDTO {
  report_id: string;
  title: string;
  description: string;
  source_service: string;
  supported_formats: ReportFormat[];
  category: string;
  permission_role: string;
  is_active: boolean;
}

export interface ReportExecutionResponse {
  execution_id: string;
  report_id: string;
  report_type: string;

  format: ReportFormat;
  requested_by: string;
  requested_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  duration_ms?: number | null;
  requested_scope: Record<string, unknown>;
  effective_scope: Record<string, unknown>;
  scope_fingerprint: string;
  scope_validation_status: ScopeValidationStatus;
  record_count: number;
  dataset_id?: string | null;
  status: ReportStatus;
  error_code?: string | null;
  error_message?: string | null;
  artifact_path?: string | null;
  file_size_bytes?: number | null;
}

export interface DownloadTokenResponse {
  execution_id: string;
  format: string;
  download_token: string;
  expires_in_minutes: number;
}

export interface ReportErrorDetail {
  code: string;
  message: string;
  details?: unknown;
}
