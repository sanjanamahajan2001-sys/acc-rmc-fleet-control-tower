export type AlertSeverity = 'CRITICAL' | 'WARNING' | 'INFO';
export type AlertStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED' | 'ARCHIVED';
export type AlertType = 'PLANT_HOLDING_BOTTLENECK' | 'SITE_RETENTION_EXCESSIVE' | 'TRANSIT_DELAY_EXCESSIVE' | 'DEGRADED_DATA_QUALITY';

export interface OperationalAlertItem {
  id: string;
  alert_fingerprint: string;
  alert_type: string;
  severity: AlertSeverity;
  status: AlertStatus;
  plant_id?: string;
  customer_id?: string;
  dispatch_id?: string;
  dataset_id?: string;
  metric_name: string;
  actual_value: number;
  threshold_value: number;
  unit: string;
  business_impact: string;
  evidence_json: Record<string, any>;
  recommended_action: string;
  detected_at: string;
  evaluated_at: string;
  rule_version: string;
  acknowledged_by?: string;
  acknowledged_at?: string;
  triage_notes?: string;
  resolved_by?: string;
  resolved_at?: string;
  resolution_reason?: string;
  archived_at?: string;
}

export interface OperationalAlertSummary {
  total_active_alerts: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
  acknowledged_count: number;
  dataset_context?: {
    operational_date: string;
    total_dispatches: number;
    last_imported_at: string;
    dataset_id: string;
    status: string;
  };
}
