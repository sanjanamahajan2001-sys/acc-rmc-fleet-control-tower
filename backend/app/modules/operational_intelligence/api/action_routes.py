"""
Phase 8 — Workstream 1: Action Execution REST API Router.
Exposes REST endpoints for action queue queries, recommendation acceptance,
execution confirmation, rejection, and deferral with standardized JSON error envelopes.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.common import get_db_session
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_intelligence.schemas.action_execution_dtos import (
    ActionQueueResponseDTO,
    ActionOperationResponseDTO,
    AcceptActionRequestDTO,
    ConfirmExecutionRequestDTO,
    RejectActionRequestDTO,
    DeferActionRequestDTO,
)
from app.modules.operational_intelligence.services.action_execution_service import (
    ActionExecutionService,
)

router = APIRouter(
    prefix="/actions",
    tags=["Phase 8 Action Execution Engine"],
)


@router.post("/generate", response_model=dict)
async def generate_action_recommendations(
    db: AsyncSession = Depends(get_db_session),
):
    """Triggers real-time ML prediction snapshots, alert intelligence, and Control Tower actions generation."""
    try:
        from generate_real_actions import generate_real_actions
        await generate_real_actions()
        return {"success": True, "message": "Actions & Predictive Intelligence auto-generated successfully!"}
    except Exception as err:
        return {"success": False, "message": f"Generation failed: {str(err)}"}


@router.get("", response_model=ActionQueueResponseDTO)
async def get_action_queue(
    plant_id: Optional[str] = Query(default="ALL"),
    customer_id: Optional[str] = Query(default="ALL"),
    dataset_type: Optional[str] = Query(default="ALL"),
    action_status: Optional[str] = Query(default=None),
    action_type: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
):
    """Returns filter-scoped action queue matching global dashboard filter parameters."""
    params = DashboardFilterParams(
        plant_id=plant_id, customer_id=customer_id, dataset_type=dataset_type
    )
    return await ActionExecutionService.get_action_queue(
        db, params, action_status=action_status, action_type=action_type
    )


@router.post("/{action_id}/accept", response_model=ActionOperationResponseDTO)
async def accept_recommendation(
    action_id: str,
    payload: AcceptActionRequestDTO,
    db: AsyncSession = Depends(get_db_session),
):
    """Dispatcher accepts recommendation intent (PENDING -> ACCEPTED)."""
    return await ActionExecutionService.accept_recommendation(
        session=db,
        action_id=action_id,
        dispatcher_id=payload.dispatcher_id,
        role=payload.dispatcher_role,
        idempotency_key=payload.idempotency_key,
        version_lock=payload.version_lock,
        notes=payload.notes,
    )


@router.post("/{action_id}/start", response_model=ActionOperationResponseDTO)
async def start_progress(
    action_id: str,
    payload: AcceptActionRequestDTO,
    db: AsyncSession = Depends(get_db_session),
):
    """Transitions action state ACCEPTED -> IN_PROGRESS."""
    return await ActionExecutionService.start_progress(
        session=db,
        action_id=action_id,
        dispatcher_id=payload.dispatcher_id,
        role=payload.dispatcher_role,
        idempotency_key=payload.idempotency_key,
        version_lock=payload.version_lock,
        notes=payload.notes,
    )


@router.post("/{action_id}/confirm-execution", response_model=ActionOperationResponseDTO)
async def confirm_execution(
    action_id: str,
    payload: ConfirmExecutionRequestDTO,
    db: AsyncSession = Depends(get_db_session),
):
    """Dispatcher explicitly confirms physical operational execution (ACCEPTED -> EXECUTED)."""
    return await ActionExecutionService.confirm_execution(
        session=db,
        action_id=action_id,
        dispatcher_id=payload.dispatcher_id,
        role=payload.dispatcher_role,
        idempotency_key=payload.idempotency_key,
        version_lock=payload.version_lock,
        notes=payload.notes,
    )


@router.post("/{action_id}/reject", response_model=ActionOperationResponseDTO)
async def reject_recommendation(
    action_id: str,
    payload: RejectActionRequestDTO,
    db: AsyncSession = Depends(get_db_session),
):
    """Rejects recommendation with explicit audit reason code (PENDING -> REJECTED)."""
    return await ActionExecutionService.reject_recommendation(
        session=db,
        action_id=action_id,
        dispatcher_id=payload.dispatcher_id,
        role=payload.dispatcher_role,
        idempotency_key=payload.idempotency_key,
        version_lock=payload.version_lock,
        reason_code=payload.reason_code,
        notes=payload.notes,
    )


@router.post("/{action_id}/defer", response_model=ActionOperationResponseDTO)
async def defer_recommendation(
    action_id: str,
    payload: DeferActionRequestDTO,
    db: AsyncSession = Depends(get_db_session),
):
    """Defers recommendation (PENDING -> DEFERRED)."""
    return await ActionExecutionService.defer_recommendation(
        session=db,
        action_id=action_id,
        dispatcher_id=payload.dispatcher_id,
        role=payload.dispatcher_role,
        idempotency_key=payload.idempotency_key,
        version_lock=payload.version_lock,
        reason_code=payload.reason_code,
        retry_at=payload.retry_at,
        notes=payload.notes,
    )
