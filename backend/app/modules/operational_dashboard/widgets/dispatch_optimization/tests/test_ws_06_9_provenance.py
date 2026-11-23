from sqlalchemy.ext.asyncio import AsyncSession
"""
WS-06.9 Provenance & Recommendation Traceability PyTest Suite.
"""
import pytest
from app.modules.operational_dashboard.widgets.dispatch_optimization.services.traceability_engine import DispatchOptimizationTraceabilityEngine
from app.modules.operational_dashboard.widgets.dispatch_optimization.services.solver_policy import SolverConfigurationDTO
from app.modules.operational_dashboard.widgets.dispatch_optimization.dtos import OptimizationObjectiveEnum

def test_candidate_search_matrix_evaluation():
    dispatch = {
    "dispatch_id": "DSP-TEST-001",
    "dispatch_number": "DSP-1001",
    "plant_code": "ACC_KUNDAIM",
    "customer_code": "CUST_AARA_HOTELS",
    "vehicle_id": "GA07F7626",
    "time_out": "08:20:12",
    "time_in": "12:46:25",
    "t2a_holding_mins": 31.0,
    "t2c_retention_mins": 9.0,
    "dispatch_date": "2025-06-20",
    }

    config = SolverConfigurationDTO()

    # Test BALANCED_OPERATIONS
    shift_bal, reason_bal = DispatchOptimizationTraceabilityEngine.evaluate_dispatch_candidate(
    dispatch, None, OptimizationObjectiveEnum.BALANCED_OPERATIONS, config
    )
    assert shift_bal == 5.0
    assert reason_bal.recommendation_reason_code == "PLANT_HOLDING_BOTTLENECK_REDUCTION"
    assert reason_bal.recommended_departure_iso == "2025-06-20T08:25:12Z"

    # Test MAXIMIZE_SLA
    shift_sla, reason_sla = DispatchOptimizationTraceabilityEngine.evaluate_dispatch_candidate(
    dispatch, None, OptimizationObjectiveEnum.MAXIMIZE_SLA, config
    )
    assert shift_sla == 0.0
    assert reason_sla.recommendation_reason_code == "OPTIMAL_HISTORICAL_SPACING"
    assert reason_sla.recommended_departure_iso == "2025-06-20T08:20:12Z"

def test_negative_no_recommendation_case():
    dispatch_no_holding = {
    "dispatch_id": "DSP-TEST-002",
    "dispatch_number": "DSP-1002",
    "plant_code": "ACC_VASCO",
    "customer_code": "CUST_TEST",
    "vehicle_id": "GA02V1234",
    "time_out": "09:00:00",
    "time_in": "11:00:00",
    "t2a_holding_mins": 2.0,
    "t2c_retention_mins": 5.0,
    "dispatch_date": "2025-06-20",
    }

    config = SolverConfigurationDTO()
    shift, reason = DispatchOptimizationTraceabilityEngine.evaluate_dispatch_candidate(
    dispatch_no_holding, None, OptimizationObjectiveEnum.BALANCED_OPERATIONS, config
    )

    assert shift == 0.0
    assert reason.recommendation_reason_code == "OPTIMAL_HISTORICAL_SPACING"
    assert "satisfies all candidate operational constraints" in reason.explanation
