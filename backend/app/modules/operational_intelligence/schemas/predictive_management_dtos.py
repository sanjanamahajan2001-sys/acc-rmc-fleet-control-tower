"""
WS-10 Phase 6.4 REST Predictive Management DTOs
Defines Pydantic request and response contracts for batch inference triggers,
snapshot invalidation, and runtime telemetry observability.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class BatchRunRequestDTO(BaseModel):
    max_dispatches: int = Field(default=200, ge=1, le=1000, description="Number of dispatches to process (1-1000).")
    force_reprocess: bool = Field(default=False, description="If true, bypasses snapshot reuse and forces re-inference.")


class InvalidateSnapshotsRequestDTO(BaseModel):
    dispatch_id: Optional[str] = Field(default=None, description="Target dispatch UUID for invalidation.")
    model_family: Optional[str] = Field(default=None, description="Target model family for invalidation.")
    reason: str = Field(..., min_length=5, description="Explicit operational audit reason for snapshot invalidation.")

    @model_validator(mode="after")
    def validate_positive_target(self):
        if not self.dispatch_id and not self.model_family:
            raise ValueError("At least one positive targeting criterion ('dispatch_id' or 'model_family') must be provided.")
        return self


class InvalidationResponseDTO(BaseModel):
    invalidated_snapshots_count: int
    dispatch_id: Optional[str]
    model_family: Optional[str]
    reason: str
    timestamp: str


class TelemetryObservabilityDTO(BaseModel):
    generated_at: str
    production_authority: str
    authoritative_model_count: int
    expected_model_family_count: int
    missing_families: List[str]
    authority_status: Dict[str, Any]
    snapshot_metrics: Dict[str, int]
    batch_cursor: Dict[str, Any]
    system_status: str
