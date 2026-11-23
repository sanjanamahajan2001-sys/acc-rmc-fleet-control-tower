"""
Phase 3 Comprehensive Backend Certification Suite: Calculation Intelligence & Dimensional Correctness.
Runs exclusively on isolated test database (TEST_DATABASE_URL=postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test).
"""

import os
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.models.base import Base
from app.modules.operational_intelligence.models.calculation_rate_config import CalculationRateConfiguration
from app.modules.operational_intelligence.services.calculation_engine import (
    FinancialCalculationEngine,
    CalculationRateNotFoundError,
    METRIC_SEMANTIC_CONTRACT,
)
from app.modules.operational_intelligence.services.predictive_service import PredictiveIntelligenceService
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test",
)


@pytest_asyncio.fixture
async def test_session():
    """Isolated test database session for Phase 3 verification."""
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Check if rate rules exist
        stmt = select(CalculationRateConfiguration).where(CalculationRateConfiguration.rate_code == "HOLDING_IDLE_RATE")
        res = await session.execute(stmt)
        if not res.scalars().all():
            session.add(
                CalculationRateConfiguration(
                    rate_id=f"TEST-RATE-HOLDING-{uuid.uuid4().hex[:6]}",
                    rate_code="HOLDING_IDLE_RATE",
                    rate_value=Decimal("450.00"),
                    currency="INR",
                    effective_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
                    is_active=True,
                    metadata_payload={"authority_source": "Fleet Operations Tariff 2026"},
                )
            )
            session.add(
                CalculationRateConfiguration(
                    rate_id=f"TEST-RATE-SLA-{uuid.uuid4().hex[:6]}",
                    rate_code="SLA_BREACH_PENALTY",
                    rate_value=Decimal("2500.00"),
                    currency="INR",
                    effective_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
                    is_active=True,
                    metadata_payload={"authority_source": "RMC SLA Contract 2026"},
                )
            )
            session.add(
                CalculationRateConfiguration(
                    rate_id=f"TEST-RATE-RETENTION-{uuid.uuid4().hex[:6]}",
                    rate_code="CUSTOMER_RETENTION_RATE",
                    rate_value=Decimal("650.00"),
                    currency="INR",
                    effective_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
                    is_active=True,
                    metadata_payload={"authority_source": "LSA-2025 Demurrage Agreement"},
                )
            )
            session.add(
                CalculationRateConfiguration(
                    rate_id=f"TEST-RATE-CONGESTION-{uuid.uuid4().hex[:6]}",
                    rate_code="PLANT_CONGESTION_RISK",
                    rate_value=Decimal("1500.00"),
                    currency="INR",
                    effective_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
                    is_active=True,
                    metadata_payload={"authority_source": "Control Tower Manual 2026"},
                )
            )
            session.add(
                CalculationRateConfiguration(
                    rate_id=f"TEST-RATE-BENCHMARK-{uuid.uuid4().hex[:6]}",
                    rate_code="STANDARD_TURNAROUND_BENCHMARK",
                    rate_value=Decimal("120.00"),
                    currency="MINS",
                    effective_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
                    is_active=True,
                    metadata_payload={"authority_source": "SOP-2026 Turnaround Standard"},
                )
            )
            await session.commit()

        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_01_rate_configuration_creation(test_session: AsyncSession):
    rate = CalculationRateConfiguration(
        rate_id=f"RATE-CREATION-{uuid.uuid4().hex[:6]}",
        rate_code="TEST_CODE",
        rate_value=Decimal("500.00"),
        currency="INR",
        effective_from=datetime.now(timezone.utc),
        is_active=True,
    )
    test_session.add(rate)
    await test_session.commit()
    assert rate.id is not None


@pytest.mark.asyncio
async def test_02_global_rate_resolution(test_session: AsyncSession):
    rate_cfg = await FinancialCalculationEngine.resolve_authoritative_rate(test_session, "HOLDING_IDLE_RATE")
    assert rate_cfg.rate_value == Decimal("450.00")
    assert rate_cfg.plant_code is None


@pytest.mark.asyncio
async def test_03_plant_override_precedence(test_session: AsyncSession):
    plant_rate = CalculationRateConfiguration(
        rate_id=f"TEST-PLANT-{uuid.uuid4().hex[:6]}",
        rate_code="HOLDING_IDLE_RATE",
        rate_value=Decimal("520.00"),
        plant_code="ACC_KUNDAIM",
        currency="INR",
        effective_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
        is_active=True,
    )
    test_session.add(plant_rate)
    await test_session.commit()

    rate_cfg = await FinancialCalculationEngine.resolve_authoritative_rate(
        test_session, "HOLDING_IDLE_RATE", plant_code="ACC_KUNDAIM"
    )
    assert rate_cfg.rate_value == Decimal("520.00")


@pytest.mark.asyncio
async def test_04_customer_contract_override_precedence(test_session: AsyncSession):
    cust_rate = CalculationRateConfiguration(
        rate_id=f"TEST-CUST-{uuid.uuid4().hex[:6]}",
        rate_code="HOLDING_IDLE_RATE",
        rate_value=Decimal("580.00"),
        plant_code="ACC_KUNDAIM",
        customer_code="CUST_VIP_CONTRACT",
        currency="INR",
        effective_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
        is_active=True,
    )
    test_session.add(cust_rate)
    await test_session.commit()

    rate_cfg = await FinancialCalculationEngine.resolve_authoritative_rate(
        test_session, "HOLDING_IDLE_RATE", plant_code="ACC_KUNDAIM", customer_code="CUST_VIP_CONTRACT"
    )
    assert rate_cfg.rate_value == Decimal("580.00")


@pytest.mark.asyncio
async def test_05_effective_date_selection(test_session: AsyncSession):
    past_date = datetime(2025, 6, 1, tzinfo=timezone.utc)
    rate_cfg = await FinancialCalculationEngine.resolve_authoritative_rate(
        test_session, "HOLDING_IDLE_RATE", target_date=past_date
    )
    assert rate_cfg.effective_from <= past_date


@pytest.mark.asyncio
async def test_06_expired_rate_rejection(test_session: AsyncSession):
    exp_rate = CalculationRateConfiguration(
        rate_id=f"TEST-EXP-{uuid.uuid4().hex[:6]}",
        rate_code="EXPIRED_CODE",
        rate_value=Decimal("999.00"),
        currency="INR",
        effective_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
        effective_to=datetime(2021, 1, 1, tzinfo=timezone.utc),
        is_active=True,
    )
    test_session.add(exp_rate)
    await test_session.commit()

    with pytest.raises(CalculationRateNotFoundError):
        await FinancialCalculationEngine.resolve_authoritative_rate(
            test_session, "EXPIRED_CODE", target_date=datetime.now(timezone.utc)
        )


@pytest.mark.asyncio
async def test_07_future_rate_rejection(test_session: AsyncSession):
    fut_rate = CalculationRateConfiguration(
        rate_id=f"TEST-FUT-{uuid.uuid4().hex[:6]}",
        rate_code="FUTURE_CODE",
        rate_value=Decimal("999.00"),
        currency="INR",
        effective_from=datetime(2030, 1, 1, tzinfo=timezone.utc),
        is_active=True,
    )
    test_session.add(fut_rate)
    await test_session.commit()

    with pytest.raises(CalculationRateNotFoundError):
        await FinancialCalculationEngine.resolve_authoritative_rate(
            test_session, "FUTURE_CODE", target_date=datetime.now(timezone.utc)
        )


@pytest.mark.asyncio
async def test_08_missing_rate_not_configured(test_session: AsyncSession):
    with pytest.raises(CalculationRateNotFoundError):
        await FinancialCalculationEngine.resolve_authoritative_rate(test_session, "NON_EXISTENT_CODE")


@pytest.mark.asyncio
async def test_09_currency_validation(test_session: AsyncSession):
    usd_rate = CalculationRateConfiguration(
        rate_id=f"TEST-USD-{uuid.uuid4().hex[:6]}",
        rate_code="HOLDING_IDLE_RATE",
        rate_value=Decimal("100.00"),
        currency="USD",
        plant_code="ACC_USD_PLANT",
        effective_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
        is_active=True,
    )
    test_session.add(usd_rate)
    await test_session.commit()

    res = await FinancialCalculationEngine.compute_snapshot_financial_exposure(
        session=test_session,
        model_name="delay_regressor",
        predicted_value=10.0,
        confidence_score=0.8,
        plant_code="ACC_USD_PLANT",
        customer_code="CUST_TEST",
        input_features={},
    )
    assert res["calculation_status"] == "NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_10_delay_exposure_formula(test_session: AsyncSession):
    exp = FinancialCalculationEngine.calculate_delay_exposure(30.0, Decimal("450.00"))
    assert exp == Decimal("225.00")


@pytest.mark.asyncio
async def test_11_sla_penalty_emv_formula(test_session: AsyncSession):
    emv = FinancialCalculationEngine.calculate_sla_penalty_emv(0.5401, Decimal("2500.00"))
    assert emv == Decimal("1350.25")


@pytest.mark.asyncio
async def test_12_idle_cost_formula(test_session: AsyncSession):
    cost = FinancialCalculationEngine.calculate_idle_queue_cost(15.0, Decimal("650.00"))
    assert cost == Decimal("162.50")


@pytest.mark.asyncio
async def test_13_decimal_rounding_correctness(test_session: AsyncSession):
    exp = FinancialCalculationEngine.calculate_delay_exposure(18.662, Decimal("450.00"))
    assert exp == Decimal("139.97")  # 18.662 / 60 * 450 = 139.965 -> 139.97 ROUND_HALF_UP


@pytest.mark.asyncio
async def test_14_historical_rate_preservation(test_session: AsyncSession):
    old_date = datetime(2025, 2, 1, tzinfo=timezone.utc)
    rate_cfg = await FinancialCalculationEngine.resolve_authoritative_rate(
        test_session, "HOLDING_IDLE_RATE", target_date=old_date
    )
    assert rate_cfg.rate_value == Decimal("450.00")


@pytest.mark.asyncio
async def test_15_calculation_version_lineage(test_session: AsyncSession):
    res = await FinancialCalculationEngine.compute_snapshot_financial_exposure(
        session=test_session,
        model_name="delay_regressor",
        predicted_value=20.0,
        confidence_score=0.9,
        plant_code="ACC_KUNDAIM",
        customer_code="DEFAULT_CUSTOMER",
        input_features={"plant_queue_avg_30d": 15.0},
    )
    assert res["calculation_lineage"]["calculation_version"] == "v1.0.0"
    assert "holding_rate" in res["calculation_lineage"]


@pytest.mark.asyncio
async def test_16_prediction_snapshot_linkage(test_session: AsyncSession):
    resp = await PredictiveIntelligenceService.get_operational_predictive_intelligence(
        session=test_session, params=DashboardFilterParams()
    )
    assert resp.calculation_status in ("SUCCESS", "NOT_CONFIGURED")


@pytest.mark.asyncio
async def test_17_null_zero_handling(test_session: AsyncSession):
    res = await FinancialCalculationEngine.compute_snapshot_financial_exposure(
        session=test_session,
        model_name="delay_regressor",
        predicted_value=0.0,
        confidence_score=None,
        plant_code="ACC_KUNDAIM",
        customer_code="DEFAULT_CUSTOMER",
        input_features={"plant_queue_avg_30d": 0},
    )
    assert res["financial_exposure_inr"] == 0.0


@pytest.mark.asyncio
async def test_18_large_value_numerical_safety(test_session: AsyncSession):
    exp = FinancialCalculationEngine.calculate_delay_exposure(1000000.0, Decimal("450.00"))
    assert exp == Decimal("7500000.00")


@pytest.mark.asyncio
async def test_19_no_hardcoded_fallback(test_session: AsyncSession):
    with pytest.raises(CalculationRateNotFoundError):
        await FinancialCalculationEngine.resolve_authoritative_rate(test_session, "DELETED_CODE_NO_FALLBACK")


@pytest.mark.asyncio
async def test_20_repeat_calculation_deterministic(test_session: AsyncSession):
    res1 = await FinancialCalculationEngine.compute_snapshot_financial_exposure(
        session=test_session,
        model_name="turnaround_regressor",
        predicted_value=208.4307,
        confidence_score=None,
        plant_code="ACC_KUNDAIM",
        customer_code="DEFAULT_CUSTOMER",
        input_features={"plant_queue_avg_30d": 15.0},
    )
    res2 = await FinancialCalculationEngine.compute_snapshot_financial_exposure(
        session=test_session,
        model_name="turnaround_regressor",
        predicted_value=208.4307,
        confidence_score=None,
        plant_code="ACC_KUNDAIM",
        customer_code="DEFAULT_CUSTOMER",
        input_features={"plant_queue_avg_30d": 15.0},
    )
    assert res1["total_financial_risk_inr"] == res2["total_financial_risk_inr"]


@pytest.mark.asyncio
async def test_21_option_a_dimensional_correctness_plant_congestion(test_session: AsyncSession):
    """Test 21: Option A dimensional correctness (prob * duration_hours * rate = ₹)."""
    # 0.3858 prob * 30 mins (0.5 hrs) * ₹1500/hr = ₹289.35
    risk = FinancialCalculationEngine.calculate_plant_congestion_risk(0.3858, 30.0, Decimal("1500.00"))
    assert risk == Decimal("289.35")

    # Zero prob -> ₹0.00
    zero_p_risk = FinancialCalculationEngine.calculate_plant_congestion_risk(0.0, 30.0, Decimal("1500.00"))
    assert zero_p_risk == Decimal("0.00")

    # Zero duration -> ₹0.00
    zero_dur_risk = FinancialCalculationEngine.calculate_plant_congestion_risk(0.3858, 0.0, Decimal("1500.00"))
    assert zero_dur_risk == Decimal("0.00")
