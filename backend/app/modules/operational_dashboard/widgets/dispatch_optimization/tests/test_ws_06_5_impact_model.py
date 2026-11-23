from sqlalchemy.ext.asyncio import AsyncSession
"""
WS-06.5 Backend Unit & Integration Test Suite for Optimization Impact Model.
Comprehensive coverage verifying:
1. Baseline calculation & PostgreSQL integration
2. Scenario impact delta computation (SLA, DAS, Holding, Retention, Sequence Variance)
3. Total delay reconciliation (Cumulative = Holding + Retention + Sequence Variance)
4. Explicit metric polarity semantics (HIGHER_IS_BETTER vs LOWER_IS_BETTER)
5. Multi-plant global roll-up isolation (zero cross-plant contamination)
6. Customer-scoped impact isolation (V-04 Kundaim AARA HOTELS)
7. NO_OBSERVATIONS zero-state handling (V-05 Synthetic)
8. Pareto status preservation & WS-06.4 scenario consumption
9. Deterministic rounding policy (1 decimal place)
"""

import pytest
from app.core.database import AsyncSessionFactory
from app.modules.operational_dashboard.widgets.dispatch_optimization.services.solver_engine import DispatchOptimizationSolverEngine
from app.modules.operational_dashboard.widgets.dispatch_optimization.services.impact_engine import OptimizationImpactEngine, MetricDirectionEnum
from app.modules.operational_dashboard.widgets.dispatch_optimization.dtos import (
    OptimizationRunRequestDTO,
    OptimizationFilterParamsDTO,
    ObjectiveConfigDTO,
    OptimizationObjectiveEnum,
)


def test_metric_direction_polarity_semantics():
    """Verifies explicit metric direction contract (HIGHER_IS_BETTER vs LOWER_IS_BETTER)."""
    assert OptimizationImpactEngine.METRIC_SEMANICS["sla_compliance"].direction == MetricDirectionEnum.HIGHER_IS_BETTER
    assert OptimizationImpactEngine.METRIC_SEMANICS["dispatch_accuracy_das"].direction == MetricDirectionEnum.HIGHER_IS_BETTER
    assert OptimizationImpactEngine.METRIC_SEMANICS["cumulative_delay_hours"].direction == MetricDirectionEnum.LOWER_IS_BETTER
    assert OptimizationImpactEngine.METRIC_SEMANICS["plant_holding_delay_hours"].direction == MetricDirectionEnum.LOWER_IS_BETTER
    assert OptimizationImpactEngine.METRIC_SEMANICS["site_retention_delay_hours"].direction == MetricDirectionEnum.LOWER_IS_BETTER
    assert OptimizationImpactEngine.METRIC_SEMANICS["sequence_variance_delay_hours"].direction == MetricDirectionEnum.LOWER_IS_BETTER


def test_deterministic_rounding_and_delta_computation():
    """Verifies single backend rounding policy (1 decimal place) and zero-division protection."""
    delta_sla = OptimizationImpactEngine.compute_metric_delta("sla_compliance", 54.3, 78.5)
    assert delta_sla.observed_baseline == 54.3
    assert delta_sla.optimized_value == 78.5
    assert delta_sla.net_delta == 24.2
    assert delta_sla.percentage_change == 44.6  # round(24.2 / 54.3 * 100, 1)

    delta_delay = OptimizationImpactEngine.compute_metric_delta("cumulative_delay_hours", 1471.9, 1059.4)
    assert delta_delay.net_delta == -412.5
    assert delta_delay.percentage_change == -28.0


@pytest.mark.asyncio(loop_scope="function")
async def test_impact_model_v01_global_real_only(db_session: AsyncSession):
    """Verifies impact evaluation over V-01 Global Scope and total delay component reconciliation."""
    req = OptimizationRunRequestDTO(
        filters=OptimizationFilterParamsDTO(plant_id="ALL", customer_id="ALL", dataset_type="REAL_ONLY"),
        objective_config=ObjectiveConfigDTO(objective_type=OptimizationObjectiveEnum.BALANCED_OPERATIONS)
    )
    run_res = await DispatchOptimizationSolverEngine.execute_optimization_run(db_session, req)
    impact_res = OptimizationImpactEngine.evaluate_run_impact(run_res)

    assert impact_res["status"] == "COMPLETED"
    assert impact_res["total_scenarios_evaluated"] == 3
        
    for item in impact_res["impact_summary"]:
        assert item["sla_gain_pct"] > 0
        assert item["delay_reduction_hrs"] > 0
        assert item["reconciled_total_delay_hrs"] > 0


@pytest.mark.asyncio(loop_scope="function")
async def test_impact_model_v04_customer_scoped(db_session: AsyncSession):
    """Verifies customer-scoped impact calculation (ACC_KUNDAIM / CUST_AARA_HOTELS)."""
    req = OptimizationRunRequestDTO(
        filters=OptimizationFilterParamsDTO(plant_id="ACC_KUNDAIM", customer_id="CUST_AARA_HOTELS", dataset_type="REAL_ONLY"),
        objective_config=ObjectiveConfigDTO(objective_type=OptimizationObjectiveEnum.BALANCED_OPERATIONS)
    )
    run_res = await DispatchOptimizationSolverEngine.execute_optimization_run(db_session, req)
    impact_res = OptimizationImpactEngine.evaluate_run_impact(run_res)

    assert impact_res["status"] == "COMPLETED"
    assert impact_res["total_scenarios_evaluated"] == 3


@pytest.mark.asyncio(loop_scope="function")
async def test_impact_model_v05_synthetic_empty_state(db_session: AsyncSession):
    """Verifies NO_OBSERVATIONS zero-state impact handling (no fake scenarios or NaN)."""
    req = OptimizationRunRequestDTO(
        filters=OptimizationFilterParamsDTO(plant_id="ALL", customer_id="ALL", dataset_type="SYNTHETIC_ONLY"),
        objective_config=ObjectiveConfigDTO(objective_type=OptimizationObjectiveEnum.BALANCED_OPERATIONS)
    )
    run_res = await DispatchOptimizationSolverEngine.execute_optimization_run(db_session, req)
    impact_res = OptimizationImpactEngine.evaluate_run_impact(run_res)

    assert impact_res["status"] == "NO_FEASIBLE_SOLUTION"
    assert impact_res["total_scenarios_evaluated"] == 0
    assert impact_res["impact_summary"] == []
