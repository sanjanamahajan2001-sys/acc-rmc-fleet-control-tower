"""
Phase 8 — Workstream 1: Action Execution DTO Contracts & Response Envelopes.
Defines Pydantic request and response DTOs for action queue queries, recommendation acceptance,
execution confirmation, rejection, deferral, and error envelopes.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class ActionStatusEnum(str, Enum):
    """Authoritative Phase 8 action lifecycle state machine."""
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"
    DEFERRED = "DEFERRED"
    REJECTED = "REJECTED"


class DispatcherRoleEnum(str, Enum):
    """Supported authorization roles for action execution."""
    DISPATCHER = "DISPATCHER"
    SUPERVISOR = "SUPERVISOR"
    ADMIN = "ADMIN"


class AcceptActionRequestDTO(BaseModel):
    dispatcher_id: str = Field(..., min_length=2, description="Unique identity of the dispatcher accepting recommendation")
    dispatcher_role: DispatcherRoleEnum = Field(default=DispatcherRoleEnum.DISPATCHER, description="Role of the decision maker")
    idempotency_key: str = Field(..., min_length=8, description="Unique client key for duplicate execution protection")
    version_lock: int = Field(..., ge=1, description="Expected version_lock for optimistic concurrency protection")
    notes: Optional[str] = Field(default=None, description="Optional dispatcher acceptance notes")


class ConfirmExecutionRequestDTO(BaseModel):
    dispatcher_id: str = Field(..., min_length=2, description="Unique identity of the dispatcher confirming physical execution")
    dispatcher_role: DispatcherRoleEnum = Field(default=DispatcherRoleEnum.DISPATCHER, description="Role of confirming operator")
    idempotency_key: str = Field(..., min_length=8, description="Unique client key for duplicate execution protection")
    version_lock: int = Field(..., ge=1, description="Expected version_lock for optimistic concurrency protection")
    notes: Optional[str] = Field(default=None, description="Dispatcher notes describing the physical action performed")


class RejectActionRequestDTO(BaseModel):
    dispatcher_id: str = Field(..., min_length=2, description="Identity of operator rejecting recommendation")
    dispatcher_role: DispatcherRoleEnum = Field(default=DispatcherRoleEnum.DISPATCHER)
    idempotency_key: str = Field(..., min_length=8)
    version_lock: int = Field(..., ge=1)
    reason_code: str = Field(..., min_length=3, description="Explicit audit reason code for rejection")
    notes: Optional[str] = Field(default=None)


class DeferActionRequestDTO(BaseModel):
    dispatcher_id: str = Field(..., min_length=2)
    dispatcher_role: DispatcherRoleEnum = Field(default=DispatcherRoleEnum.DISPATCHER)
    idempotency_key: str = Field(..., min_length=8)
    version_lock: int = Field(..., ge=1)
    reason_code: str = Field(..., min_length=3)
    retry_at: Optional[str] = Field(default=None, description="ISO timestamp when action becomes active again")
    notes: Optional[str] = Field(default=None)


class ActionLogDTO(BaseModel):
    action_id: str
    recommendation_id: str
    prediction_snapshot_id: Optional[str] = None
    model_family: Optional[str] = None
    model_version: Optional[str] = None
    dataset_id: Optional[str] = None
    operation_date: Optional[str] = None
    plant_code: str
    customer_code: Optional[str] = None
    dispatch_id: Optional[str] = None
    dispatch_code: Optional[str] = None
    action_type: str
    action_parameters: Optional[Dict[str, Any]] = None
    predicted_risk_exposure_inr: Optional[float] = None
    estimated_avoided_exposure_inr: Optional[float] = None
    actual_avoided_loss_inr: Optional[float] = None
    action_status: ActionStatusEnum
    dispatcher_id: str
    dispatcher_role: DispatcherRoleEnum
    decision_timestamp: Optional[str] = None
    accepted_at: Optional[str] = None
    started_at: Optional[str] = None
    execution_confirmed_at: Optional[str] = None
    rejected_at: Optional[str] = None
    deferred_at: Optional[str] = None
    reason_code: Optional[str] = None
    dispatcher_notes: Optional[str] = None
    idempotency_key: str
    version_lock: int


class ActionQueueResponseDTO(BaseModel):
    items: List[ActionLogDTO]
    total_count: int
    pending_count: int
    accepted_count: int
    executed_count: int


class ActionOperationResponseDTO(BaseModel):
    success: bool = True
    message: str
    action: ActionLogDTO
    is_idempotent_replay: bool = False
