"""
WS-09 Phase 7.6 Predictive Intelligence API DTOs
Defines schemas for backend endpoints returning prediction authority state, active model version information,
prediction snapshot inference responses, and historical snapshot records.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class ModelAuthorityItemDTO(BaseModel):
    """Authority status for a single model family."""
    model_name: str
    target_name: str
    model_category: str
    prediction_authority: str  # 'NOT_CONFIGURED' or 'AUTHORITATIVE'
    active_version: Optional[str] = None
    artifact_sha256: Optional[str] = None
    feature_set_version: str = "FeatureSetV1"
    last_promoted_at: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class PredictiveAuthorityOverviewDTO(BaseModel):
    """Overall predictive workspace authority overview."""
    overall_authority_status: str  # 'NOT_CONFIGURED' or 'AUTHORITATIVE'
    total_model_families: int = 4
    promoted_model_count: int = 0
    rejected_model_count: int = 4
    models: List[ModelAuthorityItemDTO]
    calculation_status: str  # 'NOT_CONFIGURED' or 'SUCCESS'
    calculation_notes: str

    model_config = ConfigDict(frozen=True)


class InferenceSnapshotResponseDTO(BaseModel):
    """Response DTO for real-time inference request."""
    prediction_snapshot_id: str
    idempotency_key: str
    prediction_timestamp: str
    prediction_status: str  # 'NOT_CONFIGURED' or 'AUTHORITATIVE'
    model_name: str
    model_version: Optional[str] = None
    artifact_sha256: Optional[str] = None
    feature_set_version: str = "FeatureSetV1"
    dispatch_id: str
    dispatch_code: str
    input_features: Dict[str, Any]
    prediction_outputs: Dict[str, Any]
    predicted_value: Optional[float] = None
    confidence_score: Optional[float] = None
    lineage_metadata: Dict[str, Any]

    model_config = ConfigDict(frozen=True)


class PredictiveSnapshotItemDTO(BaseModel):
    """Single item in snapshot history list."""
    id: str
    prediction_snapshot_id: str
    idempotency_key: str
    prediction_timestamp: str
    prediction_status: str
    model_name: str
    model_version: str
    artifact_sha256: str
    feature_set_version: str
    dispatch_id: str
    dispatch_code: str
    plant_code: str
    customer_code: str
    vehicle_code: str
    input_features: Dict[str, Any]
    prediction_outputs: Dict[str, Any]
    predicted_value: Optional[float] = None
    confidence_score: Optional[float] = None
    lineage_metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(frozen=True)


class PredictiveSnapshotHistoryResponseDTO(BaseModel):
    """Response DTO for historical prediction snapshot queries."""
    total_snapshots: int
    snapshots: List[PredictiveSnapshotItemDTO]
    calculation_status: str
    calculation_notes: str

    model_config = ConfigDict(frozen=True)
