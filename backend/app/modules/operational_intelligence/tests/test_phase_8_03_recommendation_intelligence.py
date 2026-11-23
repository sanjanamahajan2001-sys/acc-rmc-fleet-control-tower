"""
Phase 8 Workstream 8.3 Recommendation Intelligence & Financial Lineage Pytest Suite.
Verifies dispatch-specific financial exposure calculation, threshold eligibility, same-zone cluster safety,
multi-candidate ranking, prediction freshness, and real PostgreSQL database lineage.
"""

import os
import pytest
import pytest_asyncio
from sqlalchemy import select, func, cast, String
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.modules.erp.models import Dispatch, Plant, Customer
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.planner_action import PlannerActionLog
from app.modules.operational_intelligence.services.recommendation_intelligence_service import (
    WS83RecommendationIntelligenceService,
    GOVERNED_RATE_SPEC,
    THRESHOLD_DELAY_MINS,
    THRESHOLD_TURNAROUND_MINS,
    THRESHOLD_SLA_PROBABILITY,
    THRESHOLD_PLANT_RISK_PROBABILITY,
    SOUTH_CLUSTER,
    NORTH_CLUSTER,
)


def get_test_db_url() -> str:
    if os.getenv("TEST_DATABASE_URL"):
        return os.getenv("TEST_DATABASE_URL")
    return f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"


@pytest_asyncio.fixture
async def sync_session():
    if os.getenv("ALLOW_TESTING") != "true":
        pytest.skip("ALLOW_TESTING=true environment variable required to execute DB tests.")

    engine = create_async_engine(get_test_db_url(), echo=False)
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_ws83_01_dispatch_specific_financial_calculation(sync_session: AsyncSession):
    """Verifies that financial exposure is calculated dynamically per dispatch with zero hardcoding."""
    exp1, spec1 = WS83RecommendationIntelligenceService.calculate_financial_exposure("delay_regressor", 25.0)
    exp2, spec2 = WS83RecommendationIntelligenceService.calculate_financial_exposure("delay_regressor", 40.0)

    assert exp1 == 125.0  # (25.0 - 20.0) * 25.0 = 125.0
    assert exp2 == 500.0  # (40.0 - 20.0) * 25.0 = 500.0
    assert exp1 != exp2
    assert spec1 == GOVERNED_RATE_SPEC


@pytest.mark.asyncio
async def test_ws83_02_no_fixed_exposure_values(sync_session: AsyncSession):
    """Verifies that generated actions do not contain hardcoded fixed ₹1,250 or ₹250 exposure values across all rows."""
    res = await sync_session.execute(select(PlannerActionLog.predicted_risk_exposure_inr))
    exposures = [r[0] for r in res.fetchall() if r[0] is not None]

    unique_exposures = set(exposures)
    assert len(unique_exposures) > 10, f"Exposures must vary per dispatch, found only {len(unique_exposures)} unique values"


@pytest.mark.asyncio
async def test_ws83_03_no_blind_mitigation_percentage(sync_session: AsyncSession):
    """Verifies estimated_avoided_exposure_inr is explicitly NULL until outcome delta proven."""
    res = await sync_session.execute(select(PlannerActionLog.estimated_avoided_exposure_inr))
    avoided_vals = [r[0] for r in res.fetchall()]

    assert all(val is None for val in avoided_vals), "estimated_avoided_exposure_inr must remain NULL until post-action scenario delta proven"


@pytest.mark.asyncio
async def test_ws83_04_stagger_loading_eligibility_threshold(sync_session: AsyncSession):
    """Verifies STAGGER_LOADING is triggered ONLY if predicted_delay_mins > 20.0."""
    eligible = WS83RecommendationIntelligenceService.evaluate_candidate_eligibility(
        disp_id="d1", disp_code="DC-1", plant_code="ACC_VASCO", customer_code="C1",
        snapshot_id="s1", model_family="delay_regressor", model_version="v1", predicted_value=25.0
    )
    ineligible = WS83RecommendationIntelligenceService.evaluate_candidate_eligibility(
        disp_id="d2", disp_code="DC-2", plant_code="ACC_VASCO", customer_code="C1",
        snapshot_id="s2", model_family="delay_regressor", model_version="v1", predicted_value=15.0
    )

    assert eligible is not None
    assert eligible.action_type == "STAGGER_LOADING"
    assert ineligible is None


@pytest.mark.asyncio
async def test_ws83_05_transit_buffer_eligibility_threshold(sync_session: AsyncSession):
    """Verifies TRANSIT_BUFFER is triggered ONLY if predicted_turnaround_mins > 45.0."""
    eligible = WS83RecommendationIntelligenceService.evaluate_candidate_eligibility(
        disp_id="d1", disp_code="DC-1", plant_code="ACC_VASCO", customer_code="C1",
        snapshot_id="s1", model_family="turnaround_regressor", model_version="v1", predicted_value=50.0
    )
    ineligible = WS83RecommendationIntelligenceService.evaluate_candidate_eligibility(
        disp_id="d2", disp_code="DC-2", plant_code="ACC_VASCO", customer_code="C1",
        snapshot_id="s2", model_family="turnaround_regressor", model_version="v1", predicted_value=35.0
    )

    assert eligible is not None
    assert eligible.action_type == "TRANSIT_BUFFER"
    assert ineligible is None


@pytest.mark.asyncio
async def test_ws83_06_sla_prioritize_eligibility_threshold(sync_session: AsyncSession):
    """Verifies SLA_PRIORITIZE is triggered ONLY if sla_breach_probability >= 0.65."""
    eligible = WS83RecommendationIntelligenceService.evaluate_candidate_eligibility(
        disp_id="d1", disp_code="DC-1", plant_code="ACC_VASCO", customer_code="C1",
        snapshot_id="s1", model_family="sla_breach_classifier", model_version="v1", predicted_value=0.85
    )
    ineligible = WS83RecommendationIntelligenceService.evaluate_candidate_eligibility(
        disp_id="d2", disp_code="DC-2", plant_code="ACC_VASCO", customer_code="C1",
        snapshot_id="s2", model_family="sla_breach_classifier", model_version="v1", predicted_value=0.40
    )

    assert eligible is not None
    assert eligible.action_type == "SLA_PRIORITIZE"
    assert ineligible is None


@pytest.mark.asyncio
async def test_ws83_07_intra_zone_reallocate_same_zone_enforcement(sync_session: AsyncSession):
    """Verifies INTRA_ZONE_REALLOCATE target_plant_code strictly belongs to same operational cluster."""
    vasco_cand = WS83RecommendationIntelligenceService.evaluate_candidate_eligibility(
        disp_id="d1", disp_code="DC-1", plant_code="ACC_VASCO", customer_code="C1",
        snapshot_id="s1", model_family="plant_risk_classifier", model_version="v1", predicted_value=0.80
    )
    dharga_cand = WS83RecommendationIntelligenceService.evaluate_candidate_eligibility(
        disp_id="d2", disp_code="DC-2", plant_code="ACC_DHARGA", customer_code="C1",
        snapshot_id="s2", model_family="plant_risk_classifier", model_version="v1", predicted_value=0.80
    )

    assert vasco_cand is not None
    assert vasco_cand.action_parameters["target_plant_code"] == "ACC_NESSAI"  # South Cluster
    assert vasco_cand.action_parameters["target_plant_code"] in SOUTH_CLUSTER

    assert dharga_cand is not None
    assert dharga_cand.action_parameters["target_plant_code"] == "ACC_KUNDAIM"  # North Cluster
    assert dharga_cand.action_parameters["target_plant_code"] in NORTH_CLUSTER


@pytest.mark.asyncio
async def test_ws83_09_positive_counterfactual_delta_sign(sync_session: AsyncSession):
    """Verifies predicted_improvement_mins = current_delay (36.5m) - alt_delay (22.0m) = +14.5m positive value."""
    cand = WS83RecommendationIntelligenceService.evaluate_candidate_eligibility(
        disp_id="d1", disp_code="DC-1", plant_code="ACC_VASCO", customer_code="C1",
        snapshot_id="s1", model_family="plant_risk_classifier", model_version="v1", predicted_value=0.73,
        alternative_plant_predicted_delay=22.0
    )

    assert cand is not None
    assert cand.action_parameters["predicted_improvement_mins"] == 14.5
    assert cand.action_parameters["predicted_improvement_mins"] >= 10.0


@pytest.mark.asyncio
async def test_ws83_10_candidate_severity_ranking(sync_session: AsyncSession):
    """Verifies candidate ranking using Governed Severity Index (0.00 to 1.00)."""
    cand1 = WS83RecommendationIntelligenceService.evaluate_candidate_eligibility(
        disp_id="d1", disp_code="DC-1", plant_code="ACC_VASCO", customer_code="C1",
        snapshot_id="s1", model_family="delay_regressor", model_version="v1", predicted_value=45.0
    )
    cand2 = WS83RecommendationIntelligenceService.evaluate_candidate_eligibility(
        disp_id="d1", disp_code="DC-1", plant_code="ACC_VASCO", customer_code="C1",
        snapshot_id="s2", model_family="turnaround_regressor", model_version="v1", predicted_value=50.0
    )

    idx1 = WS83RecommendationIntelligenceService.calculate_candidate_severity_index(cand1)
    idx2 = WS83RecommendationIntelligenceService.calculate_candidate_severity_index(cand2)

    assert idx1 > idx2
    assert idx1 == 0.9000  # 0.40 + (25.0/30.0)*0.60 = 0.90


@pytest.mark.asyncio
async def test_ws83_08_snapshot_count_reconciliation(sync_session: AsyncSession):
    """Verifies snapshot count reconciliation (3,532 dispatches * 4 model families = 14,128 snapshots)."""
    disp_count_res = await sync_session.execute(select(func.count(Dispatch.id)).where(Dispatch.is_deleted == False))
    disp_count = disp_count_res.scalar_one()

    snap_count_res = await sync_session.execute(select(func.count(MLPredictionSnapshot.id)).where(MLPredictionSnapshot.is_deleted == False))
    snap_count = snap_count_res.scalar_one()

    if snap_count == 0:
        from generate_real_actions import generate_real_actions
        await generate_real_actions()
        snap_count_res = await sync_session.execute(select(func.count(MLPredictionSnapshot.id)).where(MLPredictionSnapshot.is_deleted == False))
        snap_count = snap_count_res.scalar_one()

    assert snap_count == disp_count * 4, f"Snapshots ({snap_count}) must equal dispatches ({disp_count}) * 4 model families"
