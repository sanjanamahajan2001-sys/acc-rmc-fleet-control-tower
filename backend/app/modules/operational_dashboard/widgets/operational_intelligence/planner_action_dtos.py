"""
Phase 5.7 Planner Action Infrastructure Contracts.
Defines authoritative Pydantic DTOs for recording immutable planner decisions (ACCEPT, MODIFY, REJECT)
and lineage references (optimization_run_id, scenario_id, objective_type, snapshot_hash).
"""

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class PlannerActionTypeEnum(str, Enum):
    """Authoritative Phase 5.7 decision types."""
    ACCEPTED = "ACCEPTED"
    MODIFIED = "MODIFIED"
    REJECTED = "REJECTED"


class PlannerRejectionReasonEnum(str, Enum):
    """Authoritative Phase 5.7 rejection categories."""
    UNFEASIBLE_CADENCE = "UNFEASIBLE_CADENCE"
    PLANT_CAPACITY_LIMIT = "PLANT_CAPACITY_LIMIT"
    SITE_ACCESS_RESTRICTION = "SITE_ACCESS_RESTRICTION"
    DRIVER_AVAILABILITY = "DRIVER_AVAILABILITY"
    OPERATOR_OVERRIDE = "OPERATOR_OVERRIDE"


class PlannerActionIngestionDTO(BaseModel):
    """Request payload for recording a planner decision (POST /planner-actions)."""
    optimization_run_id: str = Field(..., description="Lineage ID of target optimization run")
    scenario_id: str = Field(..., description="Lineage ID of selected scenario")
    objective_type: str = Field(..., description="Semantic objective type (e.g. BALANCED_OPERATIONS)")
    snapshot_hash: str = Field(..., description="Canonical SHA-256 fingerprint hash for stale check")
    action_type: PlannerActionTypeEnum = Field(..., description="ACCEPTED | MODIFIED | REJECTED")
    
    modified_parameters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Required when action_type is MODIFIED"
    )
    rejection_reason: Optional[PlannerRejectionReasonEnum] = Field(
        default=None,
        description="Required when action_type is REJECTED"
    )
    comments: Optional[str] = Field(default=None, description="Optional operator notes")


class PlannerActionRecordDTO(BaseModel):
    """Audit record schema returned upon planner action submission."""
    action_id: str = Field(..., description="Unique immutable audit action ID")
    optimization_run_id: str
    scenario_id: str
    objective_type: str
    snapshot_hash: str
    action_type: PlannerActionTypeEnum
    modified_parameters: Optional[Dict[str, Any]] = None
    rejection_reason: Optional[PlannerRejectionReasonEnum] = None
    comments: Optional[str] = None
    submitted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PlannerActionResponseDTO(BaseModel):
    """Response payload for POST /planner-actions."""
    success: bool = True
    message: str = Field(..., description="Audit confirmation detail")
    record: PlannerActionRecordDTO
