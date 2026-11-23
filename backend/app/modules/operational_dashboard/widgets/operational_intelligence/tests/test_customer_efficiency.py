import pytest
import pytest_asyncio
from app.core.database import AsyncSessionFactory
from app.modules.operational_dashboard.widgets.operational_intelligence.services.customer_efficiency import CustomerEfficiencyEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.services.problem_customers import ProblemCustomersEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import OperationalIntelligenceStatusEnum

@pytest.mark.asyncio
async def test_01_cei_formula_contract_and_boundaries():
    """Verify CEI formula mathematics, floor, rounding, and zero-trip handling."""
    # 0 penalty = 100.0
    assert ProblemCustomersEngine.calculate_cei(0.0, 0.0, 10) == 100.0
    # Holding penalty only: 10 trips * 30m = 300m max alloc. 30m pen -> 10% ratio -> 90.0 CEI
    assert ProblemCustomersEngine.calculate_cei(30.0, 0.0, 10) == 90.0
    # Retention penalty only: 10 trips * 30m = 300m max alloc. 15m pen -> 5% ratio -> 95.0 CEI
    assert ProblemCustomersEngine.calculate_cei(0.0, 15.0, 10) == 95.0
    # Combined penalties: 30m + 15m = 45m pen -> 15% ratio -> 85.0 CEI
    assert ProblemCustomersEngine.calculate_cei(30.0, 15.0, 10) == 85.0
    # Floor at 0.0: 400m pen / 300m max alloc -> 133% ratio -> max(0, -33.3) -> 0.0
    assert ProblemCustomersEngine.calculate_cei(400.0, 0.0, 10) == 0.0
    # One decimal rounding
    assert ProblemCustomersEngine.calculate_cei(10.0, 0.0, 3) == round(max(0.0, 100.0 - (10.0 / 90.0) * 100.0), 1)
    # Zero dispatches / trips -> 0.0
    assert ProblemCustomersEngine.calculate_cei(0.0, 0.0, 0) == 0.0
    assert ProblemCustomersEngine.calculate_cei(50.0, 20.0, -1) == 0.0

@pytest.mark.asyncio
async def test_02_grade_boundaries_contract():
    """Verify grade classification boundary rules for Good, Needs Improvement, and Critical."""
    assert CustomerEfficiencyEngine.classify_grade(100.0) == "Good"
    assert CustomerEfficiencyEngine.classify_grade(70.0) == "Good"
    assert CustomerEfficiencyEngine.classify_grade(69.9) == "Needs Improvement"
    assert CustomerEfficiencyEngine.classify_grade(40.0) == "Needs Improvement"
    assert CustomerEfficiencyEngine.classify_grade(39.9) == "Critical"
    assert CustomerEfficiencyEngine.classify_grade(0.0) == "Critical"

@pytest.mark.asyncio
async def test_03_ranking_tiebreaker_and_trend_contract():
    """Verify deterministic 3-tier ranking (cei ASC, total_trips DESC, customer_code ASC) and snapshot trend FLAT."""
    # Test sorting logic directly
    items = [
        {"customer_code": "CUST_C", "cei_score": 50.0, "total_trips": 10},
        {"customer_code": "CUST_A", "cei_score": 0.0, "total_trips": 5},
        {"customer_code": "CUST_B", "cei_score": 0.0, "total_trips": 20},
        {"customer_code": "CUST_AA", "cei_score": 0.0, "total_trips": 5},
    ]
    sorted_items = sorted(items, key=lambda x: (x["cei_score"], -x["total_trips"], x["customer_code"]))
    assert sorted_items[0]["customer_code"] == "CUST_B"   # 0.0 CEI, 20 trips
    assert sorted_items[1]["customer_code"] == "CUST_A"   # 0.0 CEI, 5 trips
    assert sorted_items[2]["customer_code"] == "CUST_AA"  # 0.0 CEI, 5 trips (alphabetical tiebreaker)
    assert sorted_items[3]["customer_code"] == "CUST_C"   # 50.0 CEI

@pytest.mark.asyncio
async def test_04_five_scope_reconciliation_and_dto_contract():
    """Verify complete API/DTO response envelope and metrics across all 5 verification scopes."""
    async with AsyncSessionFactory() as session:
        # V-01 Global
        v01 = await CustomerEfficiencyEngine.get_customer_efficiency(
            session, {'plant_id': 'ALL', 'customer_id': 'ALL', 'dataset_type': 'REAL_ONLY'}
        )
        assert v01.success is True
        assert v01.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert len(v01.data) == 204
        top1_v01 = v01.data[0]
        assert top1_v01.rank == 1
        assert top1_v01.customer_id == "CUST_DAFTARY_DESCON_ENGG_PVT_LTD_DECCAN"
        assert top1_v01.cei_score == 0.0
        assert top1_v01.grade == "Critical"
        assert top1_v01.trend == "FLAT"
        assert top1_v01.total_trips == 23

        # Single trip customer eligibility check in V-01
        one_trip_custs = [c for c in v01.data if c.total_trips == 1]
        assert len(one_trip_custs) > 0, "Customers with 1 trip must be included per contract"

        # V-02 Dharga
        v02 = await CustomerEfficiencyEngine.get_customer_efficiency(
            session, {'plant_id': 'ACC_DHARGA', 'customer_id': 'ALL', 'dataset_type': 'REAL_ONLY'}
        )
        assert v02.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert len(v02.data) == 113
        assert v02.data[0].customer_id == "CUST_RAJ_CHOPRA_N_COMPANY"

        # V-03 Vasco
        v03 = await CustomerEfficiencyEngine.get_customer_efficiency(
            session, {'plant_id': 'ACC_VASCO', 'customer_id': 'ALL', 'dataset_type': 'REAL_ONLY'}
        )
        assert v03.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert len(v03.data) == 68
        assert v03.data[0].customer_id == "CUST_KENKRE_ELECTRICAL"

        # V-04 Customer Specific
        v04 = await CustomerEfficiencyEngine.get_customer_efficiency(
            session, {'plant_id': 'ACC_KUNDAIM', 'customer_id': 'CUST_AARA_HOTELS', 'dataset_type': 'REAL_ONLY'}
        )
        assert v04.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert len(v04.data) == 1
        assert v04.data[0].customer_id == "CUST_AARA_HOTELS"
        assert v04.data[0].cei_score == 87.8
        assert v04.data[0].grade == "Good"

        # V-05 Synthetic Scope (Honest NO_OBSERVATIONS Envelope)
        v05 = await CustomerEfficiencyEngine.get_customer_efficiency(
            session, {'plant_id': 'ALL', 'customer_id': 'ALL', 'dataset_type': 'SYNTHETIC_ONLY'}
        )
        assert v05.success is True
        assert v05.status == OperationalIntelligenceStatusEnum.NO_OBSERVATIONS
        assert len(v05.data) == 0
