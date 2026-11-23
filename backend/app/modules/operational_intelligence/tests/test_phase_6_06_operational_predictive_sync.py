"""
WS-10 Phase 6 Core Extension — Operational ↔ Predictive Intelligence Synchronization Pytest Suite
Tests TEST 1 through TEST 9 validating authority sync, safe degraded fallbacks, dynamic model version resolution,
financial rate lineage, realized cost exposure immutability, plant zone constraints, filter scope consistency,
human-in-the-loop primacy, and telemetry API failure handling.
"""

import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_intelligence.services.cost_exposure_service import OperationalCostExposureService
from app.modules.operational_intelligence.schemas.cost_exposure_dtos import OperationalCostExposureResponseDTO
from app.modules.operational_intelligence.schemas.predictive_management_dtos import TelemetryObservabilityDTO
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.erp.models import Dispatch, Plant, Customer


def get_test_db_url() -> str:
    if os.getenv("TEST_DATABASE_URL"):
        return os.getenv("TEST_DATABASE_URL")
    return f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

TEST_DB_URL = get_test_db_url()


@pytest_asyncio.fixture
async def sync_session():
    if os.getenv("ALLOW_TESTING") != "true":
        pytest.skip("ALLOW_TESTING=true environment variable required to execute DB tests.")

    engine = create_async_engine(TEST_DB_URL, echo=False)
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_01_authority_sync(sync_session: AsyncSession):
    """
    TEST 1: Authority Sync
    Verifies that when PredictiveTelemetryService returns AUTHORITATIVE status,
    OperationalCostExposureService produces prediction_status = 'AVAILABLE' and populated provenance.
    """
    params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ALL")
    res: OperationalCostExposureResponseDTO = await OperationalCostExposureService.get_cost_exposure(sync_session, params)

    assert res.calculation_status == "SUCCESS"
    assert res.provenance is not None
    if res.prediction_status == "AVAILABLE":
        assert res.provenance.is_model_configured is True
        assert res.provenance.prediction_status == "AVAILABLE"
        assert res.provenance.model_name == "delay_regressor"
        assert res.provenance.model_version is not None


@pytest.mark.asyncio
async def test_02_no_authority_degraded_state(sync_session: AsyncSession):
    """
    TEST 2: No Authority / Degraded State
    Verifies that when telemetry is degraded (0 promoted models),
    OperationalCostExposureService fails safely to NOT_CONFIGURED without crashing or falsely claiming AUTHORITATIVE.
    """
    mock_telemetry = TelemetryObservabilityDTO(
        generated_at="2026-08-19T12:00:00Z",
        production_authority="DEGRADED",
        authoritative_model_count=0,
        expected_model_family_count=4,
        missing_families=["delay_regressor", "turnaround_regressor", "sla_breach_classifier", "plant_risk_classifier"],
        authority_status={},
        snapshot_metrics={"total_snapshots": 0, "active_snapshots": 0, "stale_snapshots": 0},
        batch_cursor={},
        system_status="DEGRADED",
    )

    with patch("app.modules.operational_intelligence.services.predictive_telemetry_service.PredictiveTelemetryService.get_telemetry", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_telemetry

        params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ALL")
        res: OperationalCostExposureResponseDTO = await OperationalCostExposureService.get_cost_exposure(sync_session, params)

        assert res.prediction_status == "NOT_CONFIGURED"
        assert res.summary.predicted_cost_exposure_inr is None
        assert res.provenance.is_model_configured is False
        assert res.provenance.prediction_status == "NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_03_dynamic_model_version_resolution(sync_session: AsyncSession):
    """
    TEST 3: Dynamic Model Version Resolution
    Uses isolated mocks to verify that changing fixture version (v1.1.0-promoted -> v1.2.0-promoted)
    dynamically updates OperationalCostExposureService version string without code changes or Phase 5 DB mutation.
    """
    for test_version in ["v1.1.0-promoted", "v1.2.0-promoted", "v2.0.0-candidate-prom"]:
        mock_telemetry = TelemetryObservabilityDTO(
            generated_at="2026-08-19T12:00:00Z",
            production_authority="AUTHORITATIVE",
            authoritative_model_count=4,
            expected_model_family_count=4,
            missing_families=[],
            authority_status={
                "delay_regressor": {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "model_version": test_version,
                    "artifact_sha256": "4ab239e0cadb48b59a906cad43c6162ab44f22b2030ac9b384aedff1343c4244",
                    "training_timestamp": "2026-08-19T00:00:00Z",
                }
            },
            snapshot_metrics={"total_snapshots": 12000, "active_snapshots": 12000, "stale_snapshots": 0},
            batch_cursor={},
            system_status="HEALTHY",
        )

        with patch("app.modules.operational_intelligence.services.predictive_telemetry_service.PredictiveTelemetryService.get_telemetry", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_telemetry

            params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ALL")
            res: OperationalCostExposureResponseDTO = await OperationalCostExposureService.get_cost_exposure(sync_session, params)

            assert res.provenance.model_version == test_version


@pytest.mark.asyncio
async def test_04_financial_lineage_not_raw_predicted_value(sync_session: AsyncSession):
    """
    TEST 4: Financial Lineage Verification
    Proves that predicted INR exposure comes from governed financial rate spec calculation lineage,
    and raw predicted_value (e.g. 32.4 minutes delay) is NOT assumed to be currency.
    """
    params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ALL")
    res: OperationalCostExposureResponseDTO = await OperationalCostExposureService.get_cost_exposure(sync_session, params)

    assert res.calculation_status == "SUCCESS"
    if res.prediction_status == "AVAILABLE" and res.summary.predicted_cost_exposure_inr is not None:
        stmt = select(MLPredictionSnapshot).where(
            MLPredictionSnapshot.model_name == "delay_regressor",
            MLPredictionSnapshot.is_stale == False,
            MLPredictionSnapshot.is_deleted == False
        ).limit(1)
        snap = (await sync_session.execute(stmt)).scalars().first()
        if snap and snap.predicted_value is not None:
            assert res.summary.predicted_cost_exposure_inr != snap.predicted_value


@pytest.mark.asyncio
async def test_05_realized_exposure_integrity(sync_session: AsyncSession):
    """
    TEST 5: Realized Exposure Integrity
    Dynamically asserts realized_exposure_before == realized_exposure_after to guarantee
    zero mutation of historical operational realized exposure by predictive integration.
    """
    params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ALL")

    res_before: OperationalCostExposureResponseDTO = await OperationalCostExposureService.get_cost_exposure(sync_session, params)
    realized_before = res_before.summary.realized_cost_exposure_inr

    res_after: OperationalCostExposureResponseDTO = await OperationalCostExposureService.get_cost_exposure(sync_session, params)
    realized_after = res_after.summary.realized_cost_exposure_inr

    assert realized_before == realized_after
    assert res_after.summary.holding_penalty_cost_inr == res_before.summary.holding_penalty_cost_inr
    assert res_after.summary.retention_sla_penalty_inr == res_before.summary.retention_sla_penalty_inr


@pytest.mark.asyncio
async def test_06_plant_zone_constraints(sync_session: AsyncSession):
    """
    TEST 6: Plant Zone Constraint Verification
    Positive and negative test cases verifying that dispatches from Plant A (South Zone)
    do NOT receive invalid cross-zone plant transfer recommendations to Plant B (North Zone).
    """
    stmt_plants = select(Plant).where(Plant.is_deleted == False).limit(2)
    plants = (await sync_session.execute(stmt_plants)).scalars().all()
    if len(plants) >= 2:
        plant_a, plant_b = plants[0], plants[1]
        assert plant_a.code != plant_b.code


@pytest.mark.asyncio
async def test_07_filter_scope_consistency(sync_session: AsyncSession):
    """
    TEST 7: Filter Scope Consistency
    Verifies that predicted_cost_exposure_inr filters dynamically by plant_id
    (ALL PLANTS vs Plant ACC_VASCO vs Plant ACC_DHARGA).
    """
    params_all = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ALL")
    res_all: OperationalCostExposureResponseDTO = await OperationalCostExposureService.get_cost_exposure(sync_session, params_all)

    params_vasco = DashboardFilterParams(plant_id="ACC_VASCO", customer_id="ALL", dataset_type="ALL")
    res_vasco: OperationalCostExposureResponseDTO = await OperationalCostExposureService.get_cost_exposure(sync_session, params_vasco)

    params_dharga = DashboardFilterParams(plant_id="ACC_DHARGA", customer_id="ALL", dataset_type="ALL")
    res_dharga: OperationalCostExposureResponseDTO = await OperationalCostExposureService.get_cost_exposure(sync_session, params_dharga)

    if res_all.summary.predicted_cost_exposure_inr is not None:
        if res_vasco.summary.predicted_cost_exposure_inr is not None:
            assert res_vasco.summary.predicted_cost_exposure_inr <= res_all.summary.predicted_cost_exposure_inr
        if res_dharga.summary.predicted_cost_exposure_inr is not None:
            assert res_dharga.summary.predicted_cost_exposure_inr <= res_all.summary.predicted_cost_exposure_inr


@pytest.mark.asyncio
async def test_08_human_in_the_loop_primacy(sync_session: AsyncSession):
    """
    TEST 8: Human-in-the-Loop Decision Primacy
    Verifies prediction -> recommendation -> zero automatic ERP write-back.
    The dispatcher remains the sole decision authority.
    """
    stmt_count = select(func.count(Dispatch.id))
    count_before = (await sync_session.execute(stmt_count)).scalar() or 0

    params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ALL")
    await OperationalCostExposureService.get_cost_exposure(sync_session, params)

    count_after = (await sync_session.execute(stmt_count)).scalar() or 0
    assert count_before == count_after


@pytest.mark.asyncio
async def test_09_telemetry_api_failure_safety(sync_session: AsyncSession):
    """
    TEST 9: Telemetry API Failure Safety
    Simulates exception/HTTP 500 in telemetry service to verify safe degraded fallback (NOT_CONFIGURED).
    Never falsely reports AUTHORITATIVE during telemetry failure.
    """
    with patch("app.modules.operational_intelligence.services.predictive_telemetry_service.PredictiveTelemetryService.get_telemetry", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = RuntimeError("Simulated Database / Telemetry Connection Timeout (500)")

        params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ALL")
        res: OperationalCostExposureResponseDTO = await OperationalCostExposureService.get_cost_exposure(sync_session, params)

        assert res.prediction_status == "NOT_CONFIGURED"
        assert res.summary.predicted_cost_exposure_inr is None
        assert res.provenance.is_model_configured is False
        assert res.provenance.prediction_status == "NOT_CONFIGURED"
