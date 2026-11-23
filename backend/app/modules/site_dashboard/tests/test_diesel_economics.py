"""
Unit Tests for Diesel Economics Calculation Engine
"""

import pytest
from app.modules.site_dashboard.services.diesel_economics_service import DieselEconomicsService, DieselEconomicsDTO


def test_diesel_economics_zero_excess():
    res = DieselEconomicsService.calculate_diesel_economics(0.0, 0.0)
    assert res.holding_cost_inr == 0.0
    assert res.unloading_cost_inr == 0.0
    assert res.total_cost_inr == 0.0
    assert res.holding_liters == 0.0
    assert res.unloading_liters == 0.0
    assert res.total_liters == 0.0


def test_diesel_economics_exact_calculation():
    # 100 excess holding mins * 0.05 L/min = 5.0 Liters
    # 5.0 Liters * 95.94 ₹/L = 479.70 ₹
    # 200 excess unloading mins * 0.05 L/min = 10.0 Liters
    # 10.0 Liters * 95.94 ₹/L = 959.40 ₹
    res = DieselEconomicsService.calculate_diesel_economics(100.0, 200.0)
    assert res.holding_liters == 5.0
    assert res.unloading_liters == 10.0
    assert res.total_liters == 15.0
    assert res.holding_cost_inr == 479.70
    assert res.unloading_cost_inr == 959.40
    assert res.total_cost_inr == 1439.10


def test_diesel_economics_custom_rate():
    # 60 excess holding mins * 0.1 L/min = 6.0 Liters
    # 6.0 Liters * 100.0 ₹/L = 600.00 ₹
    res = DieselEconomicsService.calculate_diesel_economics(
        total_excess_holding_mins=60.0,
        total_excess_unloading_mins=0.0,
        diesel_price=100.0,
        idle_burn_rate=0.1,
    )
    assert res.holding_liters == 6.0
    assert res.holding_cost_inr == 600.0
