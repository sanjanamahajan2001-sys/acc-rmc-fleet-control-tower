/**
 * Route Analysis Decision Support Engine — Frontend Types & Data Contracts
 * Strict representation of WS-ROUT-1 through WS-ROUT-7 backend API schemas
 * plus TM Incident / Stuck TM Current-Traffic Decision Support.
 */

export type RouteAnalysisMode = 'NOW' | 'PLANNED';

export type RouteAnalysisGenerationStatus =
  | 'NOT_GENERATED'
  | 'GENERATING'
  | 'GENERATED'
  | 'FAILED'
  | 'REQUIRES_REGENERATION';

export interface RouteAnalysisBatchContext {
  batch_id: string | null;
  import_timestamp: string | null;
  total_erp_dispatches: number;
  unique_route_corridors?: number;
  eligible_corridors: number;
  analyzed_snapshots: number;
  alt_recommended_count: number;
  retain_approved_count: number;
  no_difference_count: number;
  historical_only_count: number;
  live_only_count: number;
  location_missing_count: number;
  generation_status: RouteAnalysisGenerationStatus;
  generated_timestamp: string | null;
  dispatch_count?: number;
  snapshot_count?: number;
}

export type SynthesisDecisionOutcome =
  | 'RECOMMEND_CURRENT_SOURCE'
  | 'RECOMMEND_ALTERNATIVE'
  | 'NO_CLEAR_DIFFERENCE'
  | 'HISTORICAL_COMPARISON_ONLY'
  | 'LIVE_ROUTE_ONLY'
  | 'NO_RECOMMENDATION'
  | 'CANDIDATE_ROUTE_UNAVAILABLE'
  | 'LOCATION_DATA_MISSING';

export type SynthesisCaseCategory =
  | 'C1_BOTH_AGREE_CURRENT'
  | 'C2_BOTH_AGREE_ALT'
  | 'C2_BOTH_AGREE_ALTERNATIVE'
  | 'C3_TRAFFIC_OVERRIDE_ALT'
  | 'C3_TRAFFIC_OVERRIDE_ALTERNATIVE'
  | 'C4_TRAFFIC_OVERRIDE_CURR'
  | 'C4_TRAFFIC_OVERRIDE_CURRENT'
  | 'C5_NOMINAL_DIFFERENCE_BELOW_SWITCH'
  | 'C5_MARGINAL_ALT_DIFFERENCE'
  | 'C6_IDENTICAL_ROUTE_ESTIMATE'
  | 'C7_HISTORICAL_ONLY'
  | 'C7_HISTORICAL_ONLY_GOOGLE_STALE_FAILED'
  | 'C8_LIVE_ROUTE_ONLY'
  | 'C8_LIVE_ROUTE_ONLY_HIST_INSUFFICIENT'
  | 'C9_NO_EVIDENCE'
  | 'C9_NO_EVIDENCE_AVAILABLE'
  | 'C10_CANDIDATE_ROUTE_FAILED'
  | 'C11_COORDINATES_MISSING';

export interface SpeedReadingInterval {
  start_polyline_point_index: number;
  end_polyline_point_index: number;
  speed_state: 'NORMAL' | 'SLOW' | 'TRAFFIC_JAM';
  color_hex: string;
}

export interface GoogleDetailedRoute {
  plant_id: string;
  plant_code: string;
  site_id: string;
  site_code: string;
  encoded_polyline: string;
  duration_seconds: number;
  duration_minutes: number;
  static_duration_seconds?: number | null;
  static_duration_minutes?: number | null;
  traffic_delay_minutes?: number | null;
  distance_meters: number;
  distance_km: number;
  speed_reading_intervals?: SpeedReadingInterval[];
  route_token?: string | null;
}

export interface CandidateComparisonItem {
  candidate_plant_id?: string;
  candidate_plant_code?: string;
  candidate_plant_name?: string;
  candidate_plant_latitude?: number | null;
  candidate_plant_longitude?: number | null;
  current_plant_id?: string;
  current_plant_code?: string;
  current_plant_name?: string;
  plant_id?: string;
  plant_code?: string;
  plant_name?: string;
  is_current_source?: boolean;
  is_recommended?: boolean;
  is_viable?: boolean;
  crow_fly_distance_km?: number;
  google_candidate_distance_km?: number | null;
  google_distance_km?: number | null;
  google_candidate_duration_minutes?: number | null;
  google_duration_in_traffic_mins?: number | null;
  google_candidate_static_minutes?: number | null;
  google_static_duration_mins?: number | null;
  google_candidate_traffic_delay_minutes?: number | null;
  google_traffic_delay_mins?: number | null;
  historical_candidate_p50_minutes?: number | null;
  historical_t1_p50_mins?: number | null;
  historical_t1_p25_mins?: number | null;
  historical_t1_p75_mins?: number | null;
  historical_t1_iqr_mins?: number | null;
  historical_candidate_sample_count?: number;
  historical_sample_count?: number;
  historical_candidate_confidence?: string;
  historical_confidence?: 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE' | 'INSUFFICIENT_DATA';
  historical_winner_status?: string;
}

export interface HistoricalEvidenceSummary {
  case_category?: string;
  is_overall_sufficient?: boolean;
  minutes_saved?: number | null;
  is_traffic_override?: boolean;
  eligible_dispatches_count?: number;
  [key: string]: any;
}

export interface GoogleEvidenceSummary {
  provider?: string;
  routing_preference?: string;
  is_live?: boolean;
  is_cached?: boolean;
  cache_age_seconds?: number;
  detailed_routes?: Record<string, GoogleDetailedRoute>;
  [key: string]: any;
}

export interface RouteAnalysisSynthesisResult {
  analysis_id: string;
  dispatch_id?: string | null;
  dispatch_number?: string | null;
  trip_number?: string | null;
  site_id: string;
  site_code?: string;
  site_name?: string;
  site_latitude?: number | null;
  site_longitude?: number | null;
  current_source_plant_id: string;
  current_source_plant_code?: string;
  current_source_plant_name?: string;
  current_source_plant_latitude?: number | null;
  current_source_plant_longitude?: number | null;
  recommended_plant_id: string | null;
  recommended_plant_code?: string | null;
  recommended_plant_name?: string | null;
  recommendation_status: SynthesisDecisionOutcome;
  primary_case_category: SynthesisCaseCategory;
  is_traffic_override: boolean;
  decision_reason_summary: string;
  minutes_saved: number | null;
  engine_version: string;
  policy_version: string;
  analysis_mode: RouteAnalysisMode;
  requested_departure_time: string | null;
  analysis_timestamp: string;
  is_google_fresh: boolean;
  is_google_stale_cache: boolean;
  google_cache_age_seconds: number;
  is_historical_sufficient: boolean;
  comparisons: CandidateComparisonItem[];
  historical_evidence: HistoricalEvidenceSummary | null;
  google_evidence: GoogleEvidenceSummary | null;
  detailed_route?: GoogleDetailedRoute | null;
  failure_reason_code?: string | null;
}

export interface RouteAnalysisExecutionRequest {
  site_id: string;
  current_source_plant_id: string;
  customer_id?: string;
  analysis_mode?: 'NOW' | 'PLANNED_DEPARTURE' | 'PLANNED';
  planned_departure_time?: string;
  operator_notes?: string;
  candidate_plant_ids?: string[];
  force_refresh_google?: boolean;
}

export interface RouteAnalysisSnapshotItem {
  analysis_id: string;
  dispatch_id?: string | null;
  dispatch_number?: string | null;
  trip_number?: string | null;
  customer_id: string | null;
  customer_name?: string | null;
  customer_code?: string | null;
  site_id: string | null;
  site_name?: string | null;
  site_code?: string | null;
  current_source_plant_id: string | null;
  current_source_plant_name?: string | null;
  current_source_plant_code?: string | null;
  recommended_plant_id: string | null;
  recommended_plant_name?: string | null;
  recommended_plant_code?: string | null;
  recommendation_status: SynthesisDecisionOutcome | string;
  primary_case_category?: SynthesisCaseCategory | string;
  failure_reason_code: string | null;
  analysis_mode: string;
  planned_departure_time: string | null;
  engine_version: string;
  policy_version: string;
  decision_reason_summary: string;
  minutes_saved?: number | null;
  analysis_context: string | null;
  operator_notes: string | null;
  erp_import_batch_id: string | null;
  data_freshness_seconds: number;
  is_cached_result: boolean;
  queried_at: string;
}

export interface RouteAnalysisOverviewFilters {
  plant_id?: string;
  customer_id?: string;
  site_id?: string;
  recommendation_status?: string;
  search_query?: string;
  analysis_mode?: RouteAnalysisMode;
}

// ============================================================
// TM INCIDENT / STUCK TM CURRENT-TRAFFIC DECISION SUPPORT TYPES
// ============================================================

export type TMIncidentDecisionState =
  | 'BEST_CURRENT_ACCESS'
  | 'NO_CURRENT_ROUTE_EVIDENCE'
  | 'PARTIAL_ROUTE_EVIDENCE'
  | 'INCIDENT_LOCATION_INVALID'
  | 'PLANT_COORDINATES_INCOMPLETE'
  | 'TRAFFIC_EVIDENCE_STALE'
  | 'NO_OPERATIONAL_PLANTS_AVAILABLE';

export interface OperationalPlantInfo {
  plant_id: string;
  plant_code: string;
  plant_name: string;
  latitude: number | null;
  longitude: number | null;
  is_active: boolean;
  location_type: string;
}

export interface OperationalPlantsListResponse {
  success: boolean;
  total_plants: number;
  plants: OperationalPlantInfo[];
}

export interface PlantIncidentAccessItem {
  plant_id: string;
  plant_code: string;
  plant_name: string;
  plant_latitude: number;
  plant_longitude: number;
  incident_latitude: number;
  incident_longitude: number;
  crow_fly_distance_km: number;
  road_distance_km: number | null;
  duration_minutes: number | null;
  static_duration_minutes: number | null;
  traffic_delay_minutes: number | null;
  route_status: string;
  failure_reason: string | null;
  ranking: number | null;
  is_best_access: boolean;
  google_queried_at: string | null;
  provider_response_at: string | null;
  cache_age_seconds: number;
  is_cached_result: boolean;
  is_stale: boolean;
  detailed_route: GoogleDetailedRoute | null;
}

export interface TMIncidentAccessResult {
  analysis_id: string;
  analysis_context: string;
  incident_type: string;
  reported_latitude: number;
  reported_longitude: number;
  reported_location_name: string | null;
  reported_timestamp: string | null;
  analysis_timestamp: string;
  dispatch_reference: string | null;
  vehicle_reference: string | null;
  operator_notes: string | null;
  operator_identity: string;
  best_access_plant_id: string | null;
  best_access_plant_code: string | null;
  best_access_plant_name: string | null;
  best_access_eta_minutes: number | null;
  best_access_distance_km: number | null;
  best_access_traffic_delay_minutes: number | null;
  decision_state: TMIncidentDecisionState;
  decision_summary: string;
  operational_advisory: string;
  historical_evidence_status: string;
  is_google_fresh: boolean;
  is_google_stale_cache: boolean;
  google_cache_age_seconds: number;
  google_queried_at?: string | null;
  candidate_access_matrix: PlantIncidentAccessItem[];
  engine_version: string;
  policy_version: string;
}

export interface TMIncidentAccessExecutionRequest {
  reported_latitude: number;
  reported_longitude: number;
  reported_location_name?: string;
  reported_timestamp?: string;
  dispatch_reference?: string;
  vehicle_reference?: string;
  operator_notes?: string;
  force_refresh?: boolean;
}

export interface TMIncidentAccessResponse {
  success: boolean;
  data: TMIncidentAccessResult;
  error?: string;
}

export interface GoogleApiUsageSummary {
  total_billable_requests_month: number;
  cached_requests_saved_month: number;
  monthly_allowance_limit: number;
  remaining_allowance: number;
  usage_percentage: number;
  status: 'HEALTHY' | 'WARNING' | 'CRITICAL' | 'EXCEEDED' | 'UNCONFIGURED';
  is_api_configured: boolean;
  billing_cycle_start: string;
  billing_cycle_end: string;
  last_queried_at?: string | null;
  estimated_cost_usd: number;
}

export interface GoogleApiUsageResponse {
  success: boolean;
  data: GoogleApiUsageSummary;
}

