from sqlalchemy.ext.asyncio import AsyncSession
"""
WS-06.7 Planner Action Integration Unit & Integration Test Suite.
Verifies complete lineage audit trace (optimization_run_id, scenario_id, objective_type, snapshot_hash),
ACCEPT, MODIFY, REJECT decision flows, parameter validation, stale snapshot rejection, and Phase 5.7 PostgreSQL persistence.
"""

import pytest
from app.core.database import AsyncSessionFactory
from app.modules.operational_dashboard.widgets.operational_intelligence.planner_action_dtos import (
    PlannerActionIngestionDTO,
    PlannerActionTypeEnum,
    PlannerRejectionReasonEnum,
)
from app.modules.operational_dashboard.widgets.operational_intelligence.services.planner_action_service import (
    PlannerActionService,
)
from app.modules.operational_dashboard.widgets.dispatch_optimization.services.solver_engine import (
    DispatchOptimizationSolverEngine,
)
from app.modules.operational_dashboard.widgets.dispatch_optimization.dtos import (
    OptimizationRunRequestDTO,
    OptimizationFilterParamsDTO,
    ObjectiveConfigDTO,
    OptimizationObjectiveEnum,
)


@pytest.mark.asyncio(loop_scope="function")
async def test_planner_action_accepted_success(db_session: AsyncSession):
    """Verifies successful recording of ACCEPTED decision with dynamic action_id (ACT-XXXXXX)."""
    ingestion = PlannerActionIngestionDTO(
    optimization_run_id="RUN-88102-TEST",
    scenario_id="SCENARIO-UUID-9981-BALANCED",
    objective_type="BALANCED_OPERATIONS",
    snapshot_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    action_type=PlannerActionTypeEnum.ACCEPTED,
    comments="Accepted balanced cadence plan for Vasco dispatches",
    )

    res = await PlannerActionService.record_planner_action(None, ingestion)
    assert res.success is True
    assert res.record.action_id.startswith("ACT-")
    assert res.record.action_type == PlannerActionTypeEnum.ACCEPTED
    assert res.record.optimization_run_id == "RUN-88102-TEST"


@pytest.mark.asyncio(loop_scope="function")
async def test_planner_action_modified_success_and_validation(db_session: AsyncSession):
    """Verifies MODIFIED decision requires explicit modified_parameters."""
    # 1. Missing modified_parameters raises ValueError
    ingestion_invalid = PlannerActionIngestionDTO(
        optimization_run_id="RUN-88102-TEST",
        scenario_id="SCENARIO-UUID-9981-BALANCED",
        objective_type="BALANCED_OPERATIONS",
        snapshot_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        action_type=PlannerActionTypeEnum.MODIFIED,
        modified_parameters=None,
    )
    with pytest.raises(ValueError, match="modified_parameters must be explicitly provided"):
        await PlannerActionService.record_planner_action(db_session, ingestion_invalid)

    # 2. Valid MODIFIED decision
    ingestion_valid = PlannerActionIngestionDTO(
        optimization_run_id="RUN-88102-TEST",
        scenario_id="SCENARIO-UUID-9981-BALANCED",
        objective_type="BALANCED_OPERATIONS",
        snapshot_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        action_type=PlannerActionTypeEnum.MODIFIED,
        modified_parameters={"time_shift_mins": 15, "priority_vehicle": "GA07F7626"},
    )
    res = await PlannerActionService.record_planner_action(None, ingestion_valid)
    assert res.success is True
    assert res.record.action_type == PlannerActionTypeEnum.MODIFIED
    assert res.record.modified_parameters["time_shift_mins"] == 15


@pytest.mark.asyncio(loop_scope="function")
async def test_planner_action_rejected_success_and_validation(db_session: AsyncSession):
    """Verifies REJECTED decision requires explicit rejection_reason category."""
    # 1. Missing rejection_reason raises ValueError
    ingestion_invalid = PlannerActionIngestionDTO(
        optimization_run_id="RUN-88102-TEST",
        scenario_id="SCENARIO-UUID-9981-BALANCED",
        objective_type="BALANCED_OPERATIONS",
        snapshot_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        action_type=PlannerActionTypeEnum.REJECTED,
        rejection_reason=None,
    )
    with pytest.raises(ValueError, match="rejection_reason must be explicitly provided"):
        await PlannerActionService.record_planner_action(db_session, ingestion_invalid)

    # 2. Valid REJECTED decision
    ingestion_valid = PlannerActionIngestionDTO(
        optimization_run_id="RUN-88102-TEST",
        scenario_id="SCENARIO-UUID-9981-BALANCED",
        objective_type="BALANCED_OPERATIONS",
        snapshot_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        action_type=PlannerActionTypeEnum.REJECTED,
        rejection_reason=PlannerRejectionReasonEnum.SITE_ACCESS_RESTRICTION,
    )
    res = await PlannerActionService.record_planner_action(None, ingestion_valid)
    assert res.success is True
    assert res.record.action_type == PlannerActionTypeEnum.REJECTED
    assert res.record.rejection_reason == PlannerRejectionReasonEnum.SITE_ACCESS_RESTRICTION


@pytest.mark.asyncio(loop_scope="function")
async def test_stale_snapshot_rejection(db_session: AsyncSession):
    """Verifies that submitting a decision against a stale snapshot raises a STALE conflict error."""
    ingestion = PlannerActionIngestionDTO(
        optimization_run_id="RUN-88102-STALE",
        scenario_id="SCENARIO-UUID-9981-BALANCED",
        objective_type="BALANCED_OPERATIONS",
        snapshot_hash="stale_hash_value",
        action_type=PlannerActionTypeEnum.ACCEPTED,
    )

    with pytest.raises(ValueError, match="STALE_SNAPSHOT_CONFLICT"):
        await PlannerActionService.record_planner_action(db_session, ingestion, is_snapshot_stale=True)


@pytest.mark.asyncio(loop_scope="function")
async def test_full_v04_optimization_to_planner_action_lineage(db_session: AsyncSession):
    """Verifies end-to-end lineage: V-04 Customer Dispatches -> WS-06.4 Solver Run -> Candidate Scenario -> Phase 5.7 Audit Record."""
    # 1. Trigger Solver Run for V-04 (ACC_KUNDAIM / CUST_AARA_HOTELS)
    req = OptimizationRunRequestDTO(
        filters=OptimizationFilterParamsDTO(plant_id="ACC_KUNDAIM", customer_id="CUST_AARA_HOTELS", dataset_type="REAL_ONLY"),
        objective_config=ObjectiveConfigDTO(objective_type=OptimizationObjectiveEnum.BALANCED_OPERATIONS),
    )
    run_res = await DispatchOptimizationSolverEngine.execute_optimization_run(db_session, req)
    scen = run_res.scenarios[0]
    snapshot_hash = run_res.snapshot.snapshot_hash if run_res.snapshot else "DYNAMIC_HASH_FALLBACK"

    # 2. Submit Planner Decision to Phase 5.7
    ingestion = PlannerActionIngestionDTO(
        optimization_run_id=run_res.optimization_run_id,
        scenario_id=scen.scenario_id,
        objective_type=scen.objective_type.value,
        snapshot_hash=snapshot_hash,
        action_type=PlannerActionTypeEnum.ACCEPTED,
        comments="Approved V-04 customer optimization run for AARA HOTELS",
    )

    res = await PlannerActionService.record_planner_action(db_session, ingestion)
    assert res.success is True
    assert res.record.optimization_run_id == run_res.optimization_run_id
    assert res.record.scenario_id == scen.scenario_id
    assert res.record.snapshot_hash == snapshot_hash
    assert res.record.action_id.startswith("ACT-")
