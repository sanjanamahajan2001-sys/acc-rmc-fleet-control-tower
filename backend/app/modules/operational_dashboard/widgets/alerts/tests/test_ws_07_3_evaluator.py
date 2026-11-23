"""
WS-07.3 Backend PyTest Test Suite for Alert Rules Evaluation Engine (Final Closure).
"""
import uuid
import time
import pytest
from app.core.database import AsyncSessionFactory
from app.modules.operational_dashboard.widgets.dispatch_analysis.repository import DispatchAnalysisRepository
from app.modules.operational_dashboard.widgets.dispatch_optimization.services.readiness_engine import OptimizationReadinessEngine
from app.modules.operational_dashboard.widgets.alerts.evaluator_engine import AlertRulesEvaluatorEngine, RULE_VERSION

# -----------------------------------------------------------------------------
# 1. RULE BOUNDARY & NULL SEMANTICS TESTS
# -----------------------------------------------------------------------------

def test_rule_1_plant_holding_boundaries_and_null():
    dispatch_id = str(uuid.uuid4())

    # 19.99 -> NO ALERT
    res = AlertRulesEvaluatorEngine.evaluate_dispatches([{
        "dispatch_id": dispatch_id, "plant_code": "ACC_VASCO", "customer_code": "CUST_01", "t2a_holding_mins": 19.99
    }])
    assert len(res) == 0

    # 20.00 -> NO ALERT
    res = AlertRulesEvaluatorEngine.evaluate_dispatches([{
        "dispatch_id": dispatch_id, "plant_code": "ACC_VASCO", "customer_code": "CUST_01", "t2a_holding_mins": 20.00
    }])
    assert len(res) == 0

    # 20.01 -> ALERT
    res = AlertRulesEvaluatorEngine.evaluate_dispatches([{
        "dispatch_id": dispatch_id, "plant_code": "ACC_VASCO", "customer_code": "CUST_01", "t2a_holding_mins": 20.01
    }])
    assert len(res) == 1
    assert res[0]["alert_type"] == "PLANT_HOLDING_BOTTLENECK"
    assert res[0]["severity"] == "CRITICAL"

    # NULL -> NO ALERT
    res = AlertRulesEvaluatorEngine.evaluate_dispatches([{
        "dispatch_id": dispatch_id, "plant_code": "ACC_VASCO", "customer_code": "CUST_01", "t2a_holding_mins": None
    }])
    assert len(res) == 0

def test_rule_2_site_retention_boundaries_and_null():
    dispatch_id = str(uuid.uuid4())

    # 19.99 -> NO ALERT
    res = AlertRulesEvaluatorEngine.evaluate_dispatches([{
        "dispatch_id": dispatch_id, "plant_code": "ACC_VASCO", "customer_code": "CUST_01", "t2c_retention_mins": 19.99
    }])
    assert len(res) == 0

    # 20.00 -> NO ALERT
    res = AlertRulesEvaluatorEngine.evaluate_dispatches([{
        "dispatch_id": dispatch_id, "plant_code": "ACC_VASCO", "customer_code": "CUST_01", "t2c_retention_mins": 20.00
    }])
    assert len(res) == 0

    # 20.01 -> ALERT
    res = AlertRulesEvaluatorEngine.evaluate_dispatches([{
        "dispatch_id": dispatch_id, "plant_code": "ACC_VASCO", "customer_code": "CUST_01", "t2c_retention_mins": 20.01
    }])
    assert len(res) == 1
    assert res[0]["alert_type"] == "SITE_RETENTION_EXCESSIVE"
    assert res[0]["severity"] == "WARNING"

    # NULL -> NO ALERT
    res = AlertRulesEvaluatorEngine.evaluate_dispatches([{
        "dispatch_id": dispatch_id, "plant_code": "ACC_VASCO", "customer_code": "CUST_01", "t2c_retention_mins": None
    }])
    assert len(res) == 0

def test_rule_3_transit_delay_boundaries_and_null():
    dispatch_id = str(uuid.uuid4())

    # 59.99 -> NO ALERT
    res = AlertRulesEvaluatorEngine.evaluate_dispatches([{
        "dispatch_id": dispatch_id, "plant_code": "ACC_VASCO", "customer_code": "CUST_01", "t1_transit_mins": 59.99
    }])
    assert len(res) == 0

    # 60.00 -> NO ALERT
    res = AlertRulesEvaluatorEngine.evaluate_dispatches([{
        "dispatch_id": dispatch_id, "plant_code": "ACC_VASCO", "customer_code": "CUST_01", "t1_transit_mins": 60.00
    }])
    assert len(res) == 0

    # 60.01 -> ALERT
    res = AlertRulesEvaluatorEngine.evaluate_dispatches([{
        "dispatch_id": dispatch_id, "plant_code": "ACC_VASCO", "customer_code": "CUST_01", "t1_transit_mins": 60.01
    }])
    assert len(res) == 1
    assert res[0]["alert_type"] == "TRANSIT_DELAY_EXCESSIVE"
    assert res[0]["severity"] == "WARNING"

    # NULL -> NO ALERT
    res = AlertRulesEvaluatorEngine.evaluate_dispatches([{
        "dispatch_id": dispatch_id, "plant_code": "ACC_VASCO", "customer_code": "CUST_01", "t1_transit_mins": None
    }])
    assert len(res) == 0

def test_rule_4_degraded_data_quality_with_readiness():
    # READY status -> 0 DEGRADED candidates
    res_ready = AlertRulesEvaluatorEngine.evaluate_readiness(
        readiness_status="READY",
        quality_summary={"missing_timestamp_count": 0},
        blocking_conditions=[],
    )
    assert res_ready is None

    # DEGRADED status -> 1 INFO candidate
    res_degraded = AlertRulesEvaluatorEngine.evaluate_readiness(
        readiness_status="DEGRADED",
        quality_summary={"missing_timestamp_count": 12},
        blocking_conditions=["MISSING_TIMESTAMPS"],
    )
    assert res_degraded is not None
    assert res_degraded["alert_type"] == "DEGRADED_DATA_QUALITY"
    assert res_degraded["severity"] == "INFO"
    assert res_degraded["dispatch_id"] is None # Single dataset-scope alert, NOT per-dispatch

# -----------------------------------------------------------------------------
# 2. FINGERPRINT VARIATION MATRIX & DETERMINISM TESTS
# -----------------------------------------------------------------------------

def test_fingerprint_variation_matrix():
    disp_id = str(uuid.uuid4())
    fp_base = AlertRulesEvaluatorEngine.generate_canonical_fingerprint("PLANT_HOLDING_BOTTLENECK", "ACC_VASCO", "CUST_01", disp_id, "v1.0.0")

    # Format & Length: 64 hex chars
    assert len(fp_base) == 64
    assert all(c in "0123456789abcdef" for c in fp_base)

    # Identical inputs -> Same fingerprint
    fp_same = AlertRulesEvaluatorEngine.generate_canonical_fingerprint("PLANT_HOLDING_BOTTLENECK", "ACC_VASCO", "CUST_01", disp_id, "v1.0.0")
    assert fp_base == fp_same

    # Alert type changed -> Different
    assert fp_base != AlertRulesEvaluatorEngine.generate_canonical_fingerprint("SITE_RETENTION_EXCESSIVE", "ACC_VASCO", "CUST_01", disp_id, "v1.0.0")

    # Plant changed -> Different
    assert fp_base != AlertRulesEvaluatorEngine.generate_canonical_fingerprint("PLANT_HOLDING_BOTTLENECK", "ACC_KUNDAIM", "CUST_01", disp_id, "v1.0.0")

    # Customer changed -> Different
    assert fp_base != AlertRulesEvaluatorEngine.generate_canonical_fingerprint("PLANT_HOLDING_BOTTLENECK", "ACC_VASCO", "CUST_02", disp_id, "v1.0.0")

    # Dispatch ID changed -> Different
    assert fp_base != AlertRulesEvaluatorEngine.generate_canonical_fingerprint("PLANT_HOLDING_BOTTLENECK", "ACC_VASCO", "CUST_01", str(uuid.uuid4()), "v1.0.0")

    # Rule version changed -> Different
    assert fp_base != AlertRulesEvaluatorEngine.generate_canonical_fingerprint("PLANT_HOLDING_BOTTLENECK", "ACC_VASCO", "CUST_01", disp_id, "v2.0.0")

def test_repeated_deterministic_evaluation():
    sample_dispatches = [
        {"dispatch_id": str(uuid.uuid4()), "plant_code": "ACC_VASCO", "customer_code": "CUST_01", "t2a_holding_mins": 25.0, "t2c_retention_mins": 30.0},
        {"dispatch_id": str(uuid.uuid4()), "plant_code": "ACC_KUNDAIM", "customer_code": "CUST_02", "t1_transit_mins": 75.0},
    ]

    res_1 = AlertRulesEvaluatorEngine.evaluate_dispatches(sample_dispatches, dataset_id="DS-001")
    res_2 = AlertRulesEvaluatorEngine.evaluate_dispatches(sample_dispatches, dataset_id="DS-001")

    assert len(res_1) == len(res_2)
    assert res_1 == res_2 # Exact equality across ordering, fingerprints, and payloads

def test_generated_data_exclusion():
    disp_id_real = str(uuid.uuid4())
    disp_id_gen = str(uuid.uuid4())

    dispatches = [
        {"dispatch_id": disp_id_real, "plant_code": "ACC_VASCO", "customer_code": "CUST_01", "t2a_holding_mins": 30.0, "is_generated": False},
        {"dispatch_id": disp_id_gen, "plant_code": "ACC_VASCO", "customer_code": "CUST_01", "t2a_holding_mins": 30.0, "is_generated": True}, # Excluded
    ]

    res = AlertRulesEvaluatorEngine.evaluate_dispatches(dispatches)
    assert len(res) == 1
    assert res[0]["dispatch_id"] == disp_id_real

def test_error_and_non_evaluable_semantics():
    dispatches_invalid = [
        {"dispatch_id": None, "t2a_holding_mins": 30.0}, # Missing ID
        {"dispatch_id": "", "t2a_holding_mins": 30.0}, # Empty ID
        {"dispatch_id": "None", "t2a_holding_mins": 30.0}, # String None
    ]

    res = AlertRulesEvaluatorEngine.evaluate_dispatches(dispatches_invalid)
    assert len(res) == 0 # Non-evaluable records safely skipped without raising errors

# -----------------------------------------------------------------------------
# 3. FIVE-SCOPE INTEGRATION & PERFORMANCE TESTS AGAINST REAL POSTGRESQL DATA
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_five_scope_evaluator_against_postgresql():
    async with AsyncSessionFactory() as session:
        # Scope V-01: Global (3532 dispatches evaluated -> 2689 total alerts generated)
        t_start = time.time()
        dispatches_v01 = await DispatchAnalysisRepository.get_scoped_dispatches(session, {"plant_id": "ALL", "customer_id": "ALL", "dataset_type": "REAL_ONLY"})
        res_v01 = AlertRulesEvaluatorEngine.evaluate_dispatches(dispatches_v01)
        t_duration = time.time() - t_start

        assert len(dispatches_v01) == 3532
        assert len(res_v01) == 2689
        assert t_duration < 0.50 # Performance requirement: Bulk evaluation under 500ms

        # Scope V-02: Vasco (1174 dispatches -> 612 alerts)
        dispatches_v02 = await DispatchAnalysisRepository.get_scoped_dispatches(session, {"plant_id": "ACC_VASCO", "customer_id": "ALL", "dataset_type": "REAL_ONLY"})
        res_v02 = AlertRulesEvaluatorEngine.evaluate_dispatches(dispatches_v02)
        assert len(dispatches_v02) == 1174
        assert len(res_v02) == 612

        # Scope V-03: Kundaim (1065 dispatches -> 852 alerts)
        dispatches_v03 = await DispatchAnalysisRepository.get_scoped_dispatches(session, {"plant_id": "ACC_KUNDAIM", "customer_id": "ALL", "dataset_type": "REAL_ONLY"})
        res_v03 = AlertRulesEvaluatorEngine.evaluate_dispatches(dispatches_v03)
        assert len(dispatches_v03) == 1065
        assert len(res_v03) == 852

        # Scope V-04: Customer Scope (3 dispatches -> 3 alerts)
        dispatches_v04 = await DispatchAnalysisRepository.get_scoped_dispatches(session, {"plant_id": "ACC_KUNDAIM", "customer_id": "CUST_AARA_HOTELS", "dataset_type": "REAL_ONLY"})
        res_v04 = AlertRulesEvaluatorEngine.evaluate_dispatches(dispatches_v04)
        assert len(dispatches_v04) == 3
        assert len(res_v04) == 3

        # Scope V-05: Empty Scope
        dispatches_v05 = await DispatchAnalysisRepository.get_scoped_dispatches(session, {"plant_id": "NO_DATA_SCOPE", "customer_id": "ALL", "dataset_type": "REAL_ONLY"})
        res_v05 = AlertRulesEvaluatorEngine.evaluate_dispatches(dispatches_v05)
        assert len(dispatches_v05) == 0
        assert len(res_v05) == 0

        # Scope V-05A: Non-Existent Plant Scope
        dispatches_v05a = await DispatchAnalysisRepository.get_scoped_dispatches(session, {"plant_id": "NON_EXISTENT_PLANT", "customer_id": "ALL", "dataset_type": "REAL_ONLY"})
        res_v05a = AlertRulesEvaluatorEngine.evaluate_dispatches(dispatches_v05a)
        assert len(dispatches_v05a) == 0
        assert len(res_v05a) == 0
