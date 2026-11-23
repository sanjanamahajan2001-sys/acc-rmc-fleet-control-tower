"""
WS-06.3 Dispatch Optimization Router.
Provides additive readiness, optimization run, impact summary, and planner decision API endpoints.
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any

from app.core.database import get_db_session
from app.modules.operational_dashboard.widgets.dispatch_optimization.services.readiness_engine import OptimizationReadinessEngine
from app.modules.operational_dashboard.widgets.dispatch_optimization.services.solver_engine import DispatchOptimizationSolverEngine
from app.modules.operational_dashboard.widgets.dispatch_optimization.services.impact_engine import OptimizationImpactEngine
from app.modules.operational_dashboard.widgets.dispatch_optimization.dtos import (
    OptimizationReadinessDTO,
    OptimizationRunRequestDTO,
    OptimizationRunResponseDTO,
)
from app.modules.operational_dashboard.widgets.operational_intelligence.planner_action_dtos import (
    PlannerActionIngestionDTO,
    PlannerActionResponseDTO,
)
from app.modules.operational_dashboard.widgets.operational_intelligence.services.planner_action_service import (
    PlannerActionService,
)

dispatch_optimization_router = APIRouter(prefix="/dispatch-optimization", tags=["Dispatch Optimization"])
router = dispatch_optimization_router


@dispatch_optimization_router.get("/readiness", response_model=OptimizationReadinessDTO)
async def get_dispatch_optimization_readiness(
    plant_id: Optional[str] = Query(None, description="Optional plant code filter"),
    customer_id: Optional[str] = Query(None, description="Optional customer code filter"),
    dataset_type: Optional[str] = Query("ALL", description="Dataset type: REAL_ONLY, SYNTHETIC_ONLY, ALL"),
    session: AsyncSession = Depends(get_db_session),
):
    filters = {
        "plant_id": plant_id if plant_id != "ALL" else None,
        "customer_id": customer_id if customer_id != "ALL" else None,
        "dataset_type": dataset_type or "ALL",
    }
    return await OptimizationReadinessEngine.evaluate_readiness(session, filters)


@dispatch_optimization_router.post("/runs", response_model=OptimizationRunResponseDTO)
async def trigger_optimization_run(
    request: OptimizationRunRequestDTO,
    session: AsyncSession = Depends(get_db_session),
):
    """Triggers deterministic optimization run returning candidate scenarios and Pareto non-domination scores."""
    return await DispatchOptimizationSolverEngine.execute_optimization_run(session, request)


@dispatch_optimization_router.post("/impact", response_model=Dict[str, Any])
async def evaluate_optimization_impact(
    request: OptimizationRunRequestDTO,
    session: AsyncSession = Depends(get_db_session),
):
    """Evaluates baseline vs scenario impact deltas and reconciles total delay components."""
    run_response = await DispatchOptimizationSolverEngine.execute_optimization_run(session, request)
    return OptimizationImpactEngine.evaluate_run_impact(run_response)


@dispatch_optimization_router.post("/actions", response_model=PlannerActionResponseDTO)
async def record_planner_action(
    action_ingestion: PlannerActionIngestionDTO,
    session: AsyncSession = Depends(get_db_session),
):
    """Records planner decision (ACCEPT, MODIFY, REJECT) directly through Phase 5.7 Planner Action Audit Boundary to PostgreSQL."""
    try:
        return await PlannerActionService.record_planner_action(session, action_ingestion)
    except ValueError as exc:
        err_msg = str(exc)
        if "STALE_SNAPSHOT" in err_msg:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=err_msg)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=err_msg)
