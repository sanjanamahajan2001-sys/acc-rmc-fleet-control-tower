/**
 * ERP Module TypeScript Type Definitions
 * Represents WS1.6 REST API and SSE Event contracts.
 */

export type ImportPipelineStage =
  | 'QUEUED'
  | 'ACQUIRING'
  | 'PARSING'
  | 'VALIDATING'
  | 'PERSISTING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export interface ImportJobResponse {
  id: string;
  job_number: string;
  status: string;
  file_name: string;
  file_hash: string;
  total_rows: number;
  processed_rows: number;
  error_count: number;
  inserted_rows?: number;
  updated_rows?: number;
  uploaded_by?: string;
  completed_at?: string;
  is_reset?: boolean;
  reset_at?: string;
  dataset_period?: string;
  file_type?: string;
  is_active_dataset?: boolean;
  created_at: string;
  updated_at: string;
}

export interface ImportProgressSnapshot {
  job_id: string;
  stage: ImportPipelineStage;
  status: string;
  rows_processed: number;
  rows_total: number;
  rows_validated: number;
  rows_persisted: number;
  rows_failed: number;
  percentage: number;
  elapsed_seconds: number;
  eta_seconds: number;
  throughput_rows_per_sec: number;
  worker_id: string;
  memory_mb: number;
  current_sheet: string | null;
  batch_number: number;
}

export interface VersionedSSEEvent {
  schema_version: string;
  event_type: string;
  snapshot: ImportProgressSnapshot;
}

export interface PaginatedResponse<T> {
  items: T[];
  total_records: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

export interface ERPImportStatistics {
  total_imports: number;
  completed_imports: number;
  failed_imports: number;
  retried_imports: number;
  total_rows_imported: number;
  active_rows?: number;
  active_imports?: number;
  archived_imports?: number;
  is_reset_active?: boolean;
  average_duration_seconds: number;
  average_throughput_rows_per_sec: number;
  average_eta_seconds: number;
  average_validation_duration_seconds: number;
  average_persistence_duration_seconds: number;
}

export interface AuditLogItem {
  id: string;
  job_id: string;
  action: string;
  details: Record<string, any> | null;
  created_at: string;
}

export interface JobActionResponse {
  job_number: string;
  action: string;
  previous_status: string;
  new_status: string;
  message: string;
}
