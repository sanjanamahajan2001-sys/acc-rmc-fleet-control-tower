"""
WS-06.2 Data Contracts & DTO Specifications for Dispatch Optimization Control Center.
Defines authoritative Pydantic DTOs for run requests, run responses, readiness,
candidate scenarios, before/after impact matrices, and virtualized Gantt representations.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ============================================================================
# 1. ENUMERATIONS & STATE CONTRACTS
# ============================================================================

class OptimizationObjectiveEnum(str, Enum):
    """Supported candidate solver objectives."""
    BALANCED_OPERATIONS = "BALANCED_OPERATIONS"
    MINIMIZE_DELAY = "MINIMIZE_DELAY"
    MAXIMIZE_SLA = "MAXIMIZE_SLA"


class OptimizationRunStatusEnum(str, Enum):
    """Complete lifecycle state machine for optimization runs."""
    IDLE = "IDLE"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    REVIEW = "REVIEW"
    ACCEPTED = "ACCEPTED"
    MODIFIED = "MODIFIED"
    REJECTED = "REJECTED"
    STALE = "STALE"
    FAILED = "FAILED"
    NO_FEASIBLE_SOLUTION = "NO_FEASIBLE_SOLUTION"


class ReadinessStatusEnum(str, Enum):
    """Optimization readiness states."""
    READY = "READY"
    DEGRADED = "DEGRADED"
    NO_OBSERVATIONS = "NO_OBSERVATIONS"


class DatasetTypeEnum(str, Enum):
    """Authoritative dataset types."""
    REAL_ONLY = "REAL_ONLY"
    SYNTHETIC_ONLY = "SYNTHETIC_ONLY"
    ALL = "ALL"


# ============================================================================
# 2. RUN REQUEST & RESPONSE CONTRACTS
# ============================================================================

class OptimizationFilterParamsDTO(BaseModel):
    """Consumes existing DashboardFilterProvider filter contract."""
    plant_id: Optional[str] = Field(default="ALL", description="Plant filter ID or ALL")
    customer_id: Optional[str] = Field(default="ALL", description="Customer filter ID or ALL")
    dataset_type: str = Field(default="REAL_ONLY", description="REAL_ONLY | SYNTHETIC_ONLY | ALL")


class ObjectiveConfigDTO(BaseModel):
    """Configurable objective function weights and targets."""
    objective_type: OptimizationObjectiveEnum = Field(..., description="Target solver objective")
    weights: Dict[str, float] = Field(default_factory=dict, description="Versionable weights mapping")
    target_constraints: Dict[str, Any] = Field(default_factory=dict, description="Custom constraint overrides")


class OptimizationRunRequestDTO(BaseModel):
    """Request payload for triggering an optimization run (POST /runs)."""
    filters: OptimizationFilterParamsDTO
    objective_config: ObjectiveConfigDTO


# ============================================================================
# 3. READINESS DTO
# ============================================================================

class DataQualitySummaryDTO(BaseModel):
    total_dispatches: int = 0
    active_vehicle_count: int = 0
    plant_count: int = 0
    customer_count: int = 0
    missing_timestamp_count: int = 0
    missing_vehicle_count: int = 0


class OptimizationReadinessDTO(BaseModel):
    """Readiness status contract for WS-06.3 evaluation."""
    success: bool = True
    status: ReadinessStatusEnum
    reason_code: str = Field(..., description="Machine-readable readiness code")
    message: str = Field(..., description="Operator-facing readiness status message")
    quality_summary: DataQualitySummaryDTO
    blocking_conditions: List[str] = Field(default_factory=list)
    filters: OptimizationFilterParamsDTO


# ============================================================================
# 4. SNAPSHOT METADATA CONTRACT
# ============================================================================

class OptimizationSnapshotMetadataDTO(BaseModel):
    """Snapshot identity contract for stale plan rejection and Phase 5.7 audit."""
    optimization_run_id: str
    snapshot_hash: str = Field(..., description="Canonical SHA-256 fingerprint hash")
    dataset_id: str = Field(default="DEFAULT_DATASET")
    ingestion_watermark: str = Field(..., description="Timestamp of latest ERP load")
    dispatch_fingerprint_hash: str = Field(..., description="SHA-256 of canonical sorted dispatches")
    filter_scope: OptimizationFilterParamsDTO
    generated_at: str


# ============================================================================
# 5. IMPACT & SCENARIO DTOs
# ============================================================================

class MetricDeltaDTO(BaseModel):
    """Calculated metric delta distinguishing observed vs optimized values."""
    metric_name: str
    observed_baseline: float
    optimized_value: float
    net_delta: float
    percentage_change: float
    unit: str = ""


class BeforeAfterImpactMatrixDTO(BaseModel):
    """Before vs After impact comparison matrix."""
    sla_compliance: MetricDeltaDTO
    dispatch_accuracy_das: MetricDeltaDTO
    cumulative_delay_hours: MetricDeltaDTO
    plant_holding_delay_hours: MetricDeltaDTO
    site_retention_delay_hours: MetricDeltaDTO
    sequence_variance_delay_hours: MetricDeltaDTO


class CandidateScenarioDTO(BaseModel):
    """Individual candidate scenario proposal."""
    scenario_id: str = Field(..., description="Opaque scenario identifier (e.g. UUID / slug)")
    scenario_name: str = Field(..., description="Operator-facing scenario label")
    objective_type: OptimizationObjectiveEnum = Field(..., description="Solver objective used")
    pareto_score: float = Field(..., ge=0.0, le=100.0, description="Pareto trade-off score (0-100)")
    is_recommended: bool = False
    impact_matrix: BeforeAfterImpactMatrixDTO
    constraint_violations_count: int = 0
    constraint_notes: List[str] = Field(default_factory=list)
    gantt_items: List[Any] = Field(default_factory=list, description='Real solver-derived timeline items')


# ============================================================================
# 6. GANTT DATA DTOs
# ============================================================================

class RecommendationReasonDTO(BaseModel):
    """Audit-grade recommendation explanation DTO explaining WHY a dispatch departure was moved."""
    recommendation_reason_code: str = Field(..., description="Reason code (e.g. PLANT_HOLDING_BOTTLENECK_REDUCTION)")
    explanation: str = Field(..., description="Human readable explanation")
    baseline_departure_iso: str
    recommended_departure_iso: str
    shift_minutes: float
    objective_type: OptimizationObjectiveEnum
    constraints_satisfied: bool = True
    expected_sla_delta: float = 0.0
    expected_delay_delta_hours: float = 0.0
    solver_policy_version: str = "v1.0.0-PROPOSED"


class DispatchGanttItemDTO(BaseModel):
    """Single dispatch timeline bar representation for virtualized Gantt."""
    dispatch_id: str
    dispatch_number: str
    vehicle_id: str
    plant_id: str
    customer_id: str
    customer_name: Optional[str] = Field(default=None, description="Raw customer display name")
    effective_customer_name: Optional[str] = Field(default=None, description="Effective customer display name")
    
    # Raw DB string timestamps
    raw_time_out: str
    raw_time_in: str
    
    # Normalized date-anchored timestamps
    baseline_time_out_iso: str
    baseline_time_in_iso: str
    recommended_time_out_iso: str
    recommended_time_in_iso: str
    
    time_shift_mins: float = 0.0
    t1_transit_mins: float = 0.0
    t2a_holding_mins: float = 0.0
    t2c_retention_mins: float = 0.0
    sequence_order: int = 0
    recommendation_reason: Optional[RecommendationReasonDTO] = None


class OptimizationGanttResponseDTO(BaseModel):
    """Data-only payload for Gantt rendering."""
    optimization_run_id: str
    scenario_id: str
    total_vehicles: int
    total_dispatches: int
    items: List[DispatchGanttItemDTO]


# ============================================================================
# 7. RUN RESPONSE & ERROR CONTRACTS
# ============================================================================

class OptimizationRunResponseDTO(BaseModel):
    """Response payload for POST /runs and GET /runs/{run_id}."""
    success: bool = True
    optimization_run_id: str
    status: OptimizationRunStatusEnum
    snapshot: Optional[OptimizationSnapshotMetadataDTO] = None
    scenarios: List[CandidateScenarioDTO] = Field(default_factory=list)
    recommended_scenario_id: Optional[str] = None
    error_message: Optional[str] = None


class StandardAPIErrorDTO(BaseModel):
    """Standardized platform API error response schema."""
    success: bool = False
    error_code: str = Field(..., description="Machine readable error code (e.g. STALE_SNAPSHOT_CONFLICT)")
    message: str = Field(..., description="Operator-facing error detail")
    status_code: int = Field(..., description="HTTP Status Code (e.g. 409)")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
