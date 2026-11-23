from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
from enum import Enum


class OperationalIntelligenceStatusEnum(str, Enum):
    AVAILABLE = "AVAILABLE"
    NO_OBSERVATIONS = "NO_OBSERVATIONS"
    DEGRADED = "DEGRADED"


class DispatchCadenceKPIsDTO(BaseModel):
    total_dispatches: int = Field(..., description="Total qualifying dispatches for scope")
    on_schedule_dispatches: int = Field(..., description="Dispatches meeting T2a <= 20m and T2c <= 10m")
    sla_compliance_pct: float = Field(..., description="Percentage of dispatches on-schedule")
    avg_interval_mins: float = Field(..., description="Mean departure interval between dispatches in minutes")
    interval_variance_mins: float = Field(..., description="Standard deviation variance of departure intervals")
    das_score_pct: float = Field(..., description="Certified Dispatch Accuracy Score")
    completed_dispatches: int = Field(..., description="Dispatches with completed return time")
    avg_loading_mins: float = Field(..., description="Mean plant holding time (T2a)")
    avg_transit_mins: float = Field(..., description="Mean transit time (T1)")
    recommended_interval_mins: float = Field(..., description="Target cadence interval for optimal sequence")
    cadence_status: str = Field(..., description="Pacing status: Optimal, Good, Warning, Critical")
    potential_delay_reduction_hrs: float = Field(..., description="Recoverable delay hours via pacing")


class DispatchCadenceKPIResponseDTO(BaseModel):
    success: bool = True
    status: OperationalIntelligenceStatusEnum
    data: Optional[DispatchCadenceKPIsDTO] = None
    filters: dict


class DispatchCadenceItemDTO(BaseModel):
    dispatch_id: str
    dispatch_number: str
    dispatch_date: str
    time_out: Optional[str]
    time_in: Optional[str]
    plant_code: str
    customer_code: str
    customer_name: str
    vehicle_id: str
    driver_name: str
    interval_mins: float
    variance_mins: float
    holding_mins: float
    retention_mins: float
    sla_status: str
    trip_status: str
    cadence_recommendation: str


class DispatchCadenceTableResponseDTO(BaseModel):
    success: bool = True
    status: OperationalIntelligenceStatusEnum
    data: List[DispatchCadenceItemDTO] = []
    filters: dict


class DelayCategoryDTO(BaseModel):
    category_name: str
    delay_hours: float
    percentage_contribution: float
    affected_trips_count: int
    severity: str
    recommendation: str


class DispatchDelayAnalyticsDTO(BaseModel):
    total_delay_hours: float
    buildup_delay_hours: float
    unload_delay_hours: float
    sequence_variance_delay_hours: float
    categories: List[DelayCategoryDTO] = []


class DispatchDelayAnalyticsResponseDTO(BaseModel):
    success: bool = True
    status: OperationalIntelligenceStatusEnum
    data: Optional[DispatchDelayAnalyticsDTO] = None
    filters: dict


class OperationalInsightItemDTO(BaseModel):
    id: str
    category: str
    title: str
    description: str
    impact_level: str
    primary_metric: str
    action_type: str
    target_interval_mins: float
    estimated_delay_reduction_hrs: float


class OperationalInsightsDTO(BaseModel):
    total_insights: int
    primary_pacing_strategy: str
    target_departure_interval_mins: float
    potential_recoverable_delay_hrs: float
    insights: List[OperationalInsightItemDTO] = []


class OperationalInsightsResponseDTO(BaseModel):
    success: bool = True
    status: OperationalIntelligenceStatusEnum
    data: Optional[OperationalInsightsDTO] = None
    filters: dict


class VehiclePerformanceDTO(BaseModel):
    vehicle_id: str
    driver_name: str
    plant_code: str
    trips_count: int
    volume_m3: float
    avg_holding_mins: float
    avg_retention_mins: float
    das_score_pct: float
    status: str


class CustomerVehicleReportDTO(BaseModel):
    customer_code: str
    customer_name: str
    total_dispatches: int
    total_volume_m3: float
    avg_holding_mins: float
    avg_retention_mins: float
    das_score_pct: float
    vehicles: List[VehiclePerformanceDTO] = []
    recent_dispatches: List[DispatchCadenceItemDTO] = []


class CustomerVehicleReportResponseDTO(BaseModel):
    success: bool = True
    status: OperationalIntelligenceStatusEnum
    data: List[CustomerVehicleReportDTO] = []
    filters: dict


# =============================================================================
# WS-ROUT-1: HISTORICAL T1 ROUTE EVIDENCE DTOs & ENUMS (FROZEN BLUEPRINT v1.2.1)
# =============================================================================


class HistoricalConfidenceLevel(str, Enum):
    """
    Deterministic Historical Confidence Classification (Blueprint Section 3.B & Governance):
    - HIGH: N >= 15 and IQR <= 20.0 minutes
    - MODERATE: 5 <= N < 15
    - LOW: 1 <= N < 5
    - NONE: N == 0
    """
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    NONE = "NONE"


class HistoricalWinnerOutcome(str, Enum):
    """
    Historical Winner Comparison Outcome between Current and Candidate Plant (Blueprint Section 4.A):
    - CURRENT_PLANT_FASTER: delta_hist <= -theta_hist (-2.0 mins)
    - CANDIDATE_PLANT_FASTER: delta_hist >= +theta_hist (+2.0 mins)
    - NO_MEANINGFUL_HISTORICAL_DIFFERENCE: abs(delta_hist) < theta_hist (2.0 mins)
    - INSUFFICIENT_EVIDENCE: One or both plants lack minimum required sample count (N < 5)
    """
    CURRENT_PLANT_FASTER = "CURRENT_PLANT_FASTER"
    CANDIDATE_PLANT_FASTER = "CANDIDATE_PLANT_FASTER"
    NO_MEANINGFUL_HISTORICAL_DIFFERENCE = "NO_MEANINGFUL_HISTORICAL_DIFFERENCE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class CleansedT1TripRecord(BaseModel):
    """
    Individual validated, cleansed ERP/VTS trip record passing all Stage 1-7 quality gates.
    """
    dispatch_id: str
    dispatch_number: str
    trip_number: Optional[str] = None
    plant_id: str
    plant_code: Optional[str] = None
    site_id: str
    site_code: Optional[str] = None
    dispatch_date: str
    plant_out_time: Optional[str] = None
    site_in_time: Optional[str] = None
    t1_transit_mins: float
    distance_km: float
    is_generated: bool = False
    source_lineage: Optional[dict] = None


class PlantSiteHistoricalMetricDTO(BaseModel):
    """
    Statistical percentile and distribution metrics for a single Plant -> Site corridor.
    """
    plant_id: str
    plant_code: str
    plant_name: str
    site_id: str
    site_code: str
    site_name: str
    sample_count: int
    p25_minutes: Optional[float] = None
    p50_minutes: Optional[float] = None  # Median transit duration
    p75_minutes: Optional[float] = None
    iqr_minutes: Optional[float] = None  # p75 - p25
    min_minutes: Optional[float] = None
    max_minutes: Optional[float] = None
    mean_minutes: Optional[float] = None
    confidence_level: HistoricalConfidenceLevel
    is_sufficient_sample: bool  # True if sample_count >= MIN_HISTORICAL_SAMPLE_COUNT (5)
    earliest_trip_date: Optional[str] = None
    latest_trip_date: Optional[str] = None
    cleansed_trip_ids: List[str] = Field(default_factory=list)


class HistoricalComparisonPairDTO(BaseModel):
    """
    Comparative delta and winner evaluation between Current Source Plant and an Alternative Candidate Plant.
    """
    current_plant_id: str
    current_plant_code: str
    candidate_plant_id: str
    candidate_plant_code: str
    site_id: str
    site_code: str
    current_p50_minutes: Optional[float] = None
    candidate_p50_minutes: Optional[float] = None
    delta_hist_minutes: Optional[float] = None  # p50(current) - p50(candidate)
    historical_winner_status: HistoricalWinnerOutcome
    winner_plant_id: Optional[str] = None
    winner_plant_code: Optional[str] = None
    tie_threshold_minutes: float = 2.0
    explanation: str


class HistoricalTransitEvidenceSummaryDTO(BaseModel):
    """
    Authoritative aggregate response returned by HistoricalRouteEvidenceService for consumption by WS-ROUT-3.
    """
    site_id: str
    site_code: str
    site_name: str
    current_source_plant_id: str
    current_source_plant_code: str
    analysis_timestamp: str
    historical_window_days: int
    window_start_date: str
    window_end_date: str
    plant_metrics: dict[str, PlantSiteHistoricalMetricDTO]  # keyed by str(plant_id)
    comparisons: List[HistoricalComparisonPairDTO]
    overall_historical_winner: Optional[HistoricalWinnerOutcome] = None
    overall_winner_plant_id: Optional[str] = None
    overall_winner_plant_code: Optional[str] = None
    is_overall_sufficient: bool
    data_source_attribution: str = "ERP_VTS_HISTORICAL_OPERATIONAL_DATA"


# =============================================================================
# WS-ROUT-2: GOOGLE ROUTES API v2 DTOs, ENUMS & PROVIDER CONTRACTS (FROZEN v1.2.1)
# =============================================================================


class RouteAnalysisMode(str, Enum):
    """Routing temporal mode."""
    NOW = "NOW"
    PLANNED_DEPARTURE = "PLANNED_DEPARTURE"


class TrafficSpeedState(str, Enum):
    """
    Google Routes speed reading interval states mapped to normalized domain tokens.
    UI Color Mapping (Presentation tokens only):
    - NORMAL: #10B981 (Green)
    - SLOW: #F59E0B (Amber)
    - TRAFFIC_JAM: #EF4444 (Red)
    """
    NORMAL = "NORMAL"
    SLOW = "SLOW"
    TRAFFIC_JAM = "TRAFFIC_JAM"


class SpeedReadingIntervalDTO(BaseModel):
    """Traffic speed reading interval along route polyline."""
    start_polyline_point_index: int
    end_polyline_point_index: int
    speed_state: TrafficSpeedState
    color_hex: str  # Presentation token


class RouteWaypointDTO(BaseModel):
    """Authoritative geographic waypoint."""
    latitude: float
    longitude: float
    label: Optional[str] = None


class GoogleCandidateMatrixItemDTO(BaseModel):
    """
    Tier 1 Matrix result for a single candidate plant corridor.
    """
    plant_id: str
    plant_code: str
    site_id: str
    site_code: str
    origin_index: int
    destination_index: int
    status: str  # OK, NOT_FOUND, ZERO_RESULTS, ERROR
    duration_seconds: Optional[int] = None
    duration_minutes: Optional[float] = None
    static_duration_seconds: Optional[int] = None
    static_duration_minutes: Optional[float] = None
    traffic_delay_minutes: Optional[float] = None  # Dtraffic = Troute - Tstatic
    distance_meters: Optional[int] = None
    distance_km: Optional[float] = None
    condition: Optional[str] = None
    error_message: Optional[str] = None


class GoogleDetailedRouteDTO(BaseModel):
    """
    Tier 2 Detailed route result for recommended/selected corridor.
    """
    plant_id: str
    plant_code: str
    site_id: str
    site_code: str
    encoded_polyline: str
    duration_seconds: int
    duration_minutes: float
    static_duration_seconds: Optional[int] = None
    static_duration_minutes: Optional[float] = None
    traffic_delay_minutes: Optional[float] = None
    distance_meters: int
    distance_km: float
    speed_reading_intervals: List[SpeedReadingIntervalDTO] = Field(default_factory=list)
    travel_advisory: Optional[dict] = None
    route_token: Optional[str] = None


class GoogleRouteEvidenceSummaryDTO(BaseModel):
    """
    Complete Google Routes Provider response payload structured for WS-ROUT-3 synthesis.
    """
    provider_name: str = "GOOGLE_ROUTES_V2"
    status: str  # SUCCESS, PARTIAL_SUCCESS, PROVIDER_FAILURE, CIRCUIT_OPEN, STALE_FALLBACK
    mode: RouteAnalysisMode
    requested_departure_time: Optional[str] = None
    response_timestamp: str
    is_fresh: bool  # True if cache_age <= 300s or freshly fetched
    is_stale_cache: bool = False  # True if served from expired cache upon refresh failure
    cache_age_seconds: float = 0.0
    matrix_items: dict[str, GoogleCandidateMatrixItemDTO] = Field(default_factory=dict)  # plant_id -> item
    detailed_routes: dict[str, GoogleDetailedRouteDTO] = Field(default_factory=dict)  # plant_id -> detailed
    failure_reason: Optional[str] = None
    http_status: Optional[int] = None
    circuit_state: str = "CLOSED"


# =============================================================================
# WS-ROUT-3: 2D SYNTHESIS RECOMMENDATION ENGINE DTOs & ENUMS (FROZEN v1.2.1)
# =============================================================================


class SynthesisDecisionOutcome(str, Enum):
    """
    Complete frozen 10-state decision outcomes (Blueprint Section 4.B):
    - RECOMMEND_CURRENT_SOURCE: Current source plant is recommended.
    - RECOMMEND_ALTERNATIVE: Alternative candidate plant is recommended.
    - NO_CLEAR_DIFFERENCE: Nominal difference (< theta_switch 10m or identical).
    - HISTORICAL_COMPARISON_ONLY: Live route failed/stale, but valid historical data exists.
    - LIVE_ROUTE_ONLY: Live route saves >= 10m, but historical data is insufficient (N < 5).
    - NO_RECOMMENDATION: Both Google and historical evidence are unavailable/insufficient.
    - CANDIDATE_ROUTE_UNAVAILABLE: Route calculation failed for candidate plant.
    - LOCATION_DATA_MISSING: Plant or site coordinates missing from master data.
    """
    RECOMMEND_CURRENT_SOURCE = "RECOMMEND_CURRENT_SOURCE"
    RECOMMEND_ALTERNATIVE = "RECOMMEND_ALTERNATIVE"
    NO_CLEAR_DIFFERENCE = "NO_CLEAR_DIFFERENCE"
    HISTORICAL_COMPARISON_ONLY = "HISTORICAL_COMPARISON_ONLY"
    LIVE_ROUTE_ONLY = "LIVE_ROUTE_ONLY"
    NO_RECOMMENDATION = "NO_RECOMMENDATION"
    CANDIDATE_ROUTE_UNAVAILABLE = "CANDIDATE_ROUTE_UNAVAILABLE"
    LOCATION_DATA_MISSING = "LOCATION_DATA_MISSING"


class SynthesisCaseCategory(str, Enum):
    """Synthesis matrix classification case."""
    C1_BOTH_AGREE_CURRENT = "C1_BOTH_AGREE_CURRENT"
    C2_BOTH_AGREE_ALTERNATIVE = "C2_BOTH_AGREE_ALTERNATIVE"
    C3_TRAFFIC_OVERRIDE_ALTERNATIVE = "C3_TRAFFIC_OVERRIDE_ALTERNATIVE"
    C4_TRAFFIC_OVERRIDE_CURRENT = "C4_TRAFFIC_OVERRIDE_CURRENT"
    C5_NOMINAL_DIFFERENCE_BELOW_SWITCH = "C5_NOMINAL_DIFFERENCE_BELOW_SWITCH"
    C6_IDENTICAL_ROUTE_ESTIMATE = "C6_IDENTICAL_ROUTE_ESTIMATE"
    C7_HISTORICAL_ONLY_GOOGLE_STALE_FAILED = "C7_HISTORICAL_ONLY_GOOGLE_STALE_FAILED"
    C8_LIVE_ROUTE_ONLY_HIST_INSUFFICIENT = "C8_LIVE_ROUTE_ONLY_HIST_INSUFFICIENT"
    C9_NO_EVIDENCE_AVAILABLE = "C9_NO_EVIDENCE_AVAILABLE"
    C10_CANDIDATE_ROUTE_FAILED = "C10_CANDIDATE_ROUTE_FAILED"
    C11_COORDINATES_MISSING = "C11_COORDINATES_MISSING"


class SynthesisCandidateComparisonDTO(BaseModel):
    """
    Candidate vs Current Source pair comparison metrics.
    """
    candidate_plant_id: str
    candidate_plant_code: str
    candidate_plant_name: str
    current_plant_id: str
    current_plant_code: str
    current_plant_name: str
    site_id: str
    site_code: str
    site_name: str

    # Google Route Evidence
    google_current_duration_minutes: Optional[float] = None
    google_candidate_duration_minutes: Optional[float] = None
    delta_route_minutes: Optional[float] = None  # Troute(curr) - Troute(alt)
    google_current_static_minutes: Optional[float] = None
    google_candidate_static_minutes: Optional[float] = None
    google_current_traffic_delay_minutes: Optional[float] = None
    google_candidate_traffic_delay_minutes: Optional[float] = None
    google_current_distance_km: Optional[float] = None
    google_candidate_distance_km: Optional[float] = None
    google_status: str = "OK"

    # Historical ERP Evidence
    historical_current_p50_minutes: Optional[float] = None
    historical_candidate_p50_minutes: Optional[float] = None
    delta_hist_minutes: Optional[float] = None  # p50(curr) - p50(alt)
    historical_current_sample_count: int = 0
    historical_candidate_sample_count: int = 0
    historical_current_confidence: HistoricalConfidenceLevel = HistoricalConfidenceLevel.NONE
    historical_candidate_confidence: HistoricalConfidenceLevel = HistoricalConfidenceLevel.NONE
    historical_winner_status: HistoricalWinnerOutcome = HistoricalWinnerOutcome.INSUFFICIENT_EVIDENCE

    # Pair Synthesis Result
    case_category: SynthesisCaseCategory
    outcome: SynthesisDecisionOutcome
    recommended_plant_id: Optional[str] = None
    recommended_plant_code: Optional[str] = None
    minutes_saved: Optional[float] = None
    explanation: str


class RouteAnalysisSynthesisResultDTO(BaseModel):
    """
    Authoritative complete 2D synthesis response contract with dispatch lineage.
    """
    # Scope & Identity
    analysis_id: str
    dispatch_id: Optional[str] = None
    dispatch_number: Optional[str] = None
    trip_number: Optional[str] = None
    site_id: str
    site_code: str
    site_name: str
    current_source_plant_id: str
    current_source_plant_code: str
    current_source_plant_name: str
    current_source_plant_latitude: Optional[float] = None
    current_source_plant_longitude: Optional[float] = None
    site_latitude: Optional[float] = None
    site_longitude: Optional[float] = None
    recommended_plant_id: Optional[str] = None
    recommended_plant_code: Optional[str] = None
    recommended_plant_name: Optional[str] = None

    # Decision Outcome
    recommendation_status: SynthesisDecisionOutcome
    primary_case_category: SynthesisCaseCategory
    is_traffic_override: bool = False
    decision_reason_summary: str
    minutes_saved: Optional[float] = None

    # Operational Engine Governance & Provenance
    engine_version: str = "v1.2.1"
    policy_version: str = "ROUTE_POLICY_v1.2.1"
    analysis_mode: RouteAnalysisMode
    requested_departure_time: Optional[str] = None
    analysis_timestamp: str

    # Thresholds applied
    theta_switch_minutes: float = 10.0
    theta_hist_minutes: float = 2.0
    min_historical_sample_count: int = 5

    # Freshness & Invariant state
    is_google_fresh: bool
    is_google_stale_cache: bool = False
    google_cache_age_seconds: float = 0.0
    is_historical_sufficient: bool

    # Structured Evidence Payloads (accepts either typed DTOs or JSON dictionaries from snapshot storage)
    comparisons: List[Any] = Field(default_factory=list)
    historical_evidence: Optional[Any] = None
    google_evidence: Optional[Any] = None
    detailed_route: Optional[Any] = None
    failure_reason_code: Optional[str] = None



# =============================================================================
# WS-ROUT-4: REST API REQUEST / RESPONSE DTOs (FROZEN v1.2.1)
# =============================================================================


class RouteAnalysisExecutionRequestDTO(BaseModel):
    """
    Request contract to trigger a Route Analysis decision query.
    """
    site_id: str = Field(..., description="Target delivery Site UUID or site code")
    customer_id: Optional[str] = Field(None, description="Optional Customer UUID or customer code")
    current_source_plant_id: Optional[str] = Field(None, description="Current approved plant UUID or code")
    analysis_mode: RouteAnalysisMode = Field(default=RouteAnalysisMode.NOW, description="NOW or PLANNED_DEPARTURE")
    planned_departure_time: Optional[datetime] = Field(None, description="Required if analysis_mode is PLANNED_DEPARTURE")
    operator_notes: Optional[str] = Field(None, description="Optional TM traffic note or operator context")
    analysis_context: Optional[str] = Field("ROUTINE", description="Context: ROUTINE, TM_TRAFFIC_ALERT, EMERGENCY")
    force_refresh: bool = Field(False, description="Bypass cache and force fresh Google Routes query")


class RouteAnalysisSnapshotItemDTO(BaseModel):
    """
    Summary item for historical audit snapshot list with enriched master data and dispatch lineage.
    """
    analysis_id: str
    dispatch_id: Optional[str] = None
    dispatch_number: Optional[str] = None
    trip_number: Optional[str] = None
    customer_id: Optional[str] = None
    customer_code: Optional[str] = None
    customer_name: Optional[str] = None
    site_id: Optional[str] = None
    site_code: Optional[str] = None
    site_name: Optional[str] = None
    current_source_plant_id: Optional[str] = None
    current_source_plant_code: Optional[str] = None
    current_source_plant_name: Optional[str] = None
    recommended_plant_id: Optional[str] = None
    recommended_plant_code: Optional[str] = None
    recommended_plant_name: Optional[str] = None
    recommendation_status: str
    primary_case_category: Optional[str] = None
    failure_reason_code: Optional[str] = None
    analysis_mode: str
    planned_departure_time: Optional[str] = None
    engine_version: str
    policy_version: str
    decision_reason_summary: str
    minutes_saved: Optional[float] = None
    analysis_context: Optional[str] = None
    operator_notes: Optional[str] = None
    erp_import_batch_id: Optional[str] = None
    data_freshness_seconds: int
    is_cached_result: bool
    queried_at: str


class RouteAnalysisBatchContextDTO(BaseModel):
    """
    Batch generation status and ERP lineage context with complete population metrics.
    """
    batch_id: Optional[str] = None
    import_timestamp: Optional[str] = None
    total_erp_dispatches: int = 0
    unique_route_corridors: int = 0
    eligible_corridors: int = 0  # Backward-compatible alias
    analyzed_snapshots: int = 0
    alt_recommended_count: int = 0
    retain_approved_count: int = 0
    no_difference_count: int = 0
    historical_only_count: int = 0
    live_only_count: int = 0
    location_missing_count: int = 0
    generation_status: str = "NOT_GENERATED"  # NOT_GENERATED, GENERATING, GENERATED, REQUIRES_REGENERATION
    generated_timestamp: Optional[str] = None


class RouteAnalysisBatchGenerateRequestDTO(BaseModel):
    """
    Batch generation request parameters.
    """
    force_refresh: bool = False
    analysis_mode: RouteAnalysisMode = Field(default=RouteAnalysisMode.NOW)
    planned_departure_time: Optional[datetime] = None


class RouteAnalysisBatchGenerateResponseDTO(BaseModel):
    """
    Batch generation execution response.
    """
    success: bool = True
    batch_id: Optional[str] = None
    generated_count: int = 0
    message: str = "Route analysis generated successfully"


class RouteAnalysisSnapshotResponseDTO(BaseModel):
    """
    Full snapshot response envelope.
    """
    success: bool = True
    data: RouteAnalysisSynthesisResultDTO


class RouteAnalysisHistoryResponseDTO(BaseModel):
    """
    Snapshot history response envelope with server-side pagination.
    """
    success: bool = True
    data: List[RouteAnalysisSnapshotItemDTO] = []
    total_count: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 1


# =============================================================================
# TM INCIDENT ACCESS / STUCK TM CURRENT-TRAFFIC DECISION SUPPORT DTOs
# =============================================================================


class TMIncidentDecisionState(str, Enum):
    """
    Decision state outcomes for TM Incident / Stuck TM Current-Traffic Decision Support.
    Explicitly separated from delivery C1-C11 decision matrix.
    """
    BEST_CURRENT_ACCESS = "BEST_CURRENT_ACCESS"
    NO_CURRENT_ROUTE_EVIDENCE = "NO_CURRENT_ROUTE_EVIDENCE"
    PARTIAL_ROUTE_EVIDENCE = "PARTIAL_ROUTE_EVIDENCE"
    INCIDENT_LOCATION_INVALID = "INCIDENT_LOCATION_INVALID"
    PLANT_COORDINATES_INCOMPLETE = "PLANT_COORDINATES_INCOMPLETE"
    TRAFFIC_EVIDENCE_STALE = "TRAFFIC_EVIDENCE_STALE"
    NO_OPERATIONAL_PLANTS_AVAILABLE = "NO_OPERATIONAL_PLANTS_AVAILABLE"


class TMIncidentAccessExecutionRequestDTO(BaseModel):
    """
    Operator incident request payload for TM stuck in traffic decision support.
    Operator identity is NEVER accepted from client body; resolved via auth session.
    """
    incident_type: str = Field(default="TM_STUCK_IN_TRAFFIC", description="Incident type")
    reported_latitude: float = Field(..., description="Operator-reported latitude")
    reported_longitude: float = Field(..., description="Operator-reported longitude")
    reported_location_name: Optional[str] = Field(None, description="Optional descriptive location name")
    reported_timestamp: Optional[datetime] = Field(None, description="Time driver reported the incident")
    dispatch_reference: Optional[str] = Field(None, description="Optional audit-only dispatch reference")
    vehicle_reference: Optional[str] = Field(None, description="Optional audit-only vehicle/TM reference")
    operator_notes: Optional[str] = Field(None, description="Optional operator contextual notes")
    force_refresh: bool = Field(False, description="Bypass cache for fresh Google Routes query")


class PlantIncidentAccessItemDTO(BaseModel):
    """
    Current-traffic road access candidate evaluation for an operational plant.
    """
    plant_id: str
    plant_code: str
    plant_name: str
    plant_latitude: float
    plant_longitude: float
    incident_latitude: float
    incident_longitude: float
    crow_fly_distance_km: float
    road_distance_km: Optional[float] = None
    duration_minutes: Optional[float] = None
    static_duration_minutes: Optional[float] = None
    traffic_delay_minutes: Optional[float] = None
    route_status: str = "OK"  # OK, UNAVAILABLE, ERROR
    failure_reason: Optional[str] = None
    ranking: Optional[int] = None
    is_best_access: bool = False
    google_queried_at: Optional[str] = None
    provider_response_at: Optional[str] = None
    cache_age_seconds: float = 0.0
    is_cached_result: bool = False
    is_stale: bool = False
    detailed_route: Optional[GoogleDetailedRouteDTO] = None


class TMIncidentAccessResultDTO(BaseModel):
    """
    Decision support result for TM incident access across all 4 operational Goa plants.
    """
    analysis_id: str
    analysis_context: str = "TM_INCIDENT_ACCESS"
    incident_type: str = "TM_STUCK_IN_TRAFFIC"
    reported_latitude: float
    reported_longitude: float
    reported_location_name: Optional[str] = None
    reported_timestamp: Optional[str] = None
    analysis_timestamp: str
    dispatch_reference: Optional[str] = None
    vehicle_reference: Optional[str] = None
    operator_notes: Optional[str] = None
    operator_identity: str
    best_access_plant_id: Optional[str] = None
    best_access_plant_code: Optional[str] = None
    best_access_plant_name: Optional[str] = None
    best_access_eta_minutes: Optional[float] = None
    best_access_distance_km: Optional[float] = None
    best_access_traffic_delay_minutes: Optional[float] = None
    decision_state: TMIncidentDecisionState
    decision_summary: str
    operational_advisory: str = (
        "Operational Advisory Only: This analysis uses the operator-reported incident location and "
        "current Google route estimates. Live TM location and truck availability are not evaluated. "
        "Final dispatch/action decision remains with Operations."
    )
    historical_evidence_status: str = "INSUFFICIENT_NO_INCIDENT_BASELINE"
    is_google_fresh: bool
    is_google_stale_cache: bool
    google_cache_age_seconds: float
    google_queried_at: Optional[str] = None
    candidate_access_matrix: List[PlantIncidentAccessItemDTO] = Field(default_factory=list)
    engine_version: str = "v1.2.1"
    policy_version: str = "INCIDENT_POLICY_v1.0.0"


class TMIncidentAccessResponseDTO(BaseModel):
    """
    API Response envelope for TM Incident Access Decision Support.
    """
    success: bool = True
    data: TMIncidentAccessResultDTO


class OperationalPlantInfoDTO(BaseModel):
    """
    Master data information for an active operational plant.
    """
    plant_id: str
    plant_code: str
    plant_name: str
    latitude: float
    longitude: float


class OperationalPlantsListResponseDTO(BaseModel):
    """
    Response envelope for operational plants master reference.
    """
    success: bool = True
    data: List[OperationalPlantInfoDTO] = Field(default_factory=list)



class GoogleApiUsageSummaryDTO(BaseModel):
    total_billable_requests_month: int = Field(
        ..., description="Total billable API request units executed in current calendar month"
    )
    cached_requests_saved_month: int = Field(
        ..., description="Total requests served by multi-tier cache without calling Google"
    )
    monthly_allowance_limit: int = Field(
        default=20000, description="Monthly free-tier / allowance threshold"
    )
    remaining_allowance: int = Field(
        ..., description="Estimated remaining request allowance for the current billing cycle"
    )
    usage_percentage: float = Field(
        ..., description="Percentage of monthly allowance consumed (0.0% - 100%+)"
    )
    status: str = Field(
        ..., description="HEALTHY, WARNING, CRITICAL, EXCEEDED, or UNCONFIGURED"
    )
    is_api_configured: bool = Field(
        ..., description="Whether GOOGLE_MAPS_ROUTES_API_KEY is configured in backend"
    )
    billing_cycle_start: str = Field(
        ..., description="ISO timestamp for start of current calendar month"
    )
    billing_cycle_end: str = Field(
        ..., description="ISO timestamp for end of current calendar month"
    )
    last_queried_at: Optional[str] = Field(
        None, description="Timestamp of the most recent Google Routes API call"
    )
    estimated_cost_usd: float = Field(
        default=0.0, description="Estimated GCP cost incurred after free credit"
    )


class GoogleApiUsageResponseDTO(BaseModel):
    success: bool = True
    data: GoogleApiUsageSummaryDTO
