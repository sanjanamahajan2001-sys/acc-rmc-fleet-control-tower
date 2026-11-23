"""
WS-09 Phase 7.7 Operational Predictive Intelligence DTOs

Defines schemas for:
- Operational prediction snapshot items with contextual entity enrichment (dispatch, plant, customer, vehicle)
- Operational prioritization vectors (top predicted delay, SLA breach risk)
- Comprehensive operational workspace response
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OperationalPredictionItemDTO(BaseModel):
    """Enriched prediction snapshot item containing operational entity context."""

    id: str = Field(..., description="PostgreSQL primary key UUID")
    prediction_snapshot_id: str = Field(..., description="Domain snapshot identifier SNAP-YYYY-XXXX")
    idempotency_key: str = Field(..., description="Idempotency key")
    prediction_timestamp: str = Field(..., description="ISO-8601 timestamp when prediction was generated")
    prediction_status: str = Field(..., description="Prediction authority status (AUTHORITATIVE or NOT_CONFIGURED)")
    model_name: str = Field(..., description="Candidate model family name")
    model_version: str = Field(..., description="Promoted model version tag")
    artifact_sha256: str = Field(..., description="SHA-256 hash of trained model artifact")
    feature_set_version: str = Field(..., description="FeatureSet version (e.g. FeatureSetV1)")
    dispatch_id: str = Field(..., description="Associated dispatch UUID")
    dispatch_code: str = Field(..., description="Human-readable dispatch code")
    plant_code: Optional[str] = Field(None, description="Associated plant code")
    plant_name: Optional[str] = Field(None, description="Human-readable plant name")
    customer_code: Optional[str] = Field(None, description="Associated customer code")
    customer_name: Optional[str] = Field(None, description="Human-readable customer name")
    vehicle_code: Optional[str] = Field(None, description="Associated vehicle code")
    target_name: str = Field(..., description="Target name being predicted")
    predicted_value: Optional[float] = Field(None, description="Predicted numerical value or class label")
    confidence_score: Optional[float] = Field(None, description="Model output confidence score (0.0 to 1.0)")
    input_features: Dict[str, Any] = Field(default_factory=dict, description="Input feature snapshot")
    prediction_outputs: Dict[str, Any] = Field(default_factory=dict, description="Raw model prediction outputs")
    lineage_metadata: Optional[Dict[str, Any]] = Field(None, description="Full lineage metadata")
    financial_exposure_inr: Optional[float] = Field(None, description="Delay cost exposure in INR")
    sla_penalty_risk_inr: Optional[float] = Field(None, description="SLA penalty risk in INR")
    plant_congestion_risk_inr: Optional[float] = Field(None, description="Plant congestion risk in INR")
    idle_queue_cost_inr: Optional[float] = Field(None, description="Idle queue cost exposure in INR")
    total_financial_risk_inr: Optional[float] = Field(None, description="Total financial risk exposure in INR")
    currency: str = Field("INR", description="Explicit currency code (INR)")
    calculation_lineage: Optional[Dict[str, Any]] = Field(None, description="Phase 3 calculation lineage metadata")


class OperationalPrioritizationDTO(BaseModel):
    """Ranked operational risk vectors derived from prediction snapshots."""

    top_delayed_dispatches: List[OperationalPredictionItemDTO] = Field(
        default_factory=list, description="Top dispatches ranked by highest predicted delay"
    )
    high_sla_risk_dispatches: List[OperationalPredictionItemDTO] = Field(
        default_factory=list, description="Top dispatches ranked by SLA breach probability"
    )
    high_plant_risk_dispatches: List[OperationalPredictionItemDTO] = Field(
        default_factory=list, description="Top dispatches ranked by plant risk"
    )


class OperationalPredictiveResponseDTO(BaseModel):
    """Complete WS-09 Phase 7.7 Operational Predictive Response Payload."""

    overall_authority_status: str = Field(..., description="NOT_CONFIGURED or AUTHORITATIVE")
    promoted_model_count: int = Field(..., description="Total active promoted models")
    total_snapshots_found: int = Field(..., description="Total snapshots matching global filters")
    prioritization: OperationalPrioritizationDTO = Field(
        ..., description="Ranked operational risk vectors"
    )
    snapshots: List[OperationalPredictionItemDTO] = Field(
        default_factory=list, description="Paginated/filtered prediction snapshot history"
    )
    calculation_status: str = Field(..., description="SUCCESS, NO_RECORDS, or NOT_CONFIGURED")
    calculation_notes: str = Field(..., description="Operational governance and summary notes")
