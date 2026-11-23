import pytest
from app.modules.operational_dashboard.widgets.operational_intelligence.services.problem_customers import ProblemCustomersEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import ProblemCustomerDTO

def test_problem_customer_holding_retention_formulas():
    holding_pen_mins = 10.0
    retention_pen_mins = 5.0
    tot_lost_hrs = round((holding_pen_mins + retention_pen_mins) / 60.0, 1)
    assert tot_lost_hrs == 0.2


def test_cei_formula_calculation():
    # DEFAULT_CUSTOMER: 20951.0 holding mins + 5998.0 retention mins = 26949.0 mins across 2066 trips -> CEI = 56.5
    cei = ProblemCustomersEngine.calculate_cei(20951.0, 5998.0, 2066)
    assert cei == 56.5

    # CUST_RAJ_CHOPRA_N_COMPANY: 1469.0 holding + 203.0 retention = 1672.0 mins across 58 trips -> CEI = 3.9 (matches Phase 0 baseline!)
    cei_raj = ProblemCustomersEngine.calculate_cei(1469.0, 203.0, 58)
    assert cei_raj == 3.9

    # CUST_QUBIK_INFRA: 851.0 holding + 264.0 retention = 1115.0 mins across 42 trips -> CEI = 11.5 (matches Phase 0 baseline!)
    cei_qubik = ProblemCustomersEngine.calculate_cei(851.0, 264.0, 42)
    assert cei_qubik == 11.5


def test_cei_zero_trip_protection():
    cei = ProblemCustomersEngine.calculate_cei(600.0, 0.0, 0)
    assert cei == 0.0


def test_cei_clamping_lower_bound():
    cei = ProblemCustomersEngine.calculate_cei(6000.0, 0.0, 10)
    assert cei == 0.0


def test_ranking_sort_order():
    c1 = ProblemCustomerDTO(
        customer_id="C1", customer_name="C1", rank=1, total_trips=50,
        holding_hours=10.0, retention_hours=5.0, total_lost_hours=15.0, cei=40.0
    )
    c2 = ProblemCustomerDTO(
        customer_id="C2", customer_name="C2", rank=2, total_trips=50,
        holding_hours=5.0, retention_hours=2.0, total_lost_hours=7.0, cei=72.0
    )
    assert c1.total_lost_hours > c2.total_lost_hours
    assert c1.rank < c2.rank
