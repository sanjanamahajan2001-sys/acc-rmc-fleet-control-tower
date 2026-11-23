"""
WS-06.11 Five-Scope Vertical Verification Dedicated Backend Test Suite.
"""
import pytest
from app.modules.operational_dashboard.widgets.dispatch_analysis.repository import DispatchAnalysisRepository
from app.modules.operational_dashboard.widgets.dispatch_optimization.services.solver_engine import DispatchOptimizationSolverEngine
from app.modules.operational_dashboard.widgets.dispatch_optimization.services.readiness_engine import OptimizationReadinessEngine
from app.modules.operational_dashboard.widgets.dispatch_optimization.dtos import (
    OptimizationRunRequestDTO,
    OptimizationFilterParamsDTO,
    ObjectiveConfigDTO,
    OptimizationObjectiveEnum,
)
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio(loop_scope="function")
async def test_five_scope_vertical_verification_all_scopes(db_session: AsyncSession):
    for code, flt_dict in [
        ("V-01", {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}),
        ("V-02", {"plant_id": "ACC_VASCO", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}),
        ("V-03", {"plant_id": "ACC_KUNDAIM", "customer_id": "ALL", "dataset_type": "REAL_ONLY"}),
        ("V-04", {"plant_id": "ACC_KUNDAIM", "customer_id": "CUST_AARA_HOTELS", "dataset_type": "REAL_ONLY"}),
        ("V-05", {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "SYNTHETIC_ONLY"}),
    ]:
        # 1. DB Repository Count
        dispatches = await DispatchAnalysisRepository.get_scoped_dispatches(db_session, flt_dict)
        expected_count = len(dispatches)

        # 2. Readiness Engine Count
        readiness = await OptimizationReadinessEngine.evaluate_readiness(db_session, flt_dict)
        readiness_count = readiness.quality_summary.total_dispatches if readiness.quality_summary else 0
        assert readiness_count == expected_count

        # 3. Solver Engine Execution
        req = OptimizationRunRequestDTO(
            filters=OptimizationFilterParamsDTO(**flt_dict),
            objective_config=ObjectiveConfigDTO(objective_type=OptimizationObjectiveEnum.BALANCED_OPERATIONS)
        )
        run_res = await DispatchOptimizationSolverEngine.execute_optimization_run(db_session, req)
        
        if expected_count > 0:
            assert len(run_res.scenarios) > 0
            gantt_items = run_res.scenarios[0].gantt_items
            assert len(gantt_items) == expected_count
            
            # Verify 100% ID identity mapping
            db_ids = [str(d.get("dispatch_id")) for d in dispatches]
            dto_ids = [item.dispatch_id for item in gantt_items]
            assert dto_ids == db_ids
            
            # Verify Plant / Customer Isolation
            if flt_dict["plant_id"] != "ALL":
                assert all(item.plant_id == flt_dict["plant_id"] for item in gantt_items)
            if flt_dict["customer_id"] != "ALL":
                assert all(item.customer_id == flt_dict["customer_id"] for item in gantt_items)
        else:
            assert run_res.status.value in ["NO_OBSERVATIONS", "NO_FEASIBLE_SOLUTION"]
            assert len(run_res.scenarios) == 0
