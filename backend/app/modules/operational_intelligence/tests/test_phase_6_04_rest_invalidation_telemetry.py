"""
WS-10 Phase 6.4 REST Predictive Management & Telemetry Verification Suite
Exhaustively certifies:
1. Batch Management REST Endpoint (POST /fleet-api/v1/operational-intelligence/predictive/batch-run).
2. Snapshot Invalidation REST Endpoint (POST /fleet-api/v1/operational-intelligence/predictive/invalidate-snapshots).
3. Runtime Telemetry Observability REST Endpoint (GET /fleet-api/v1/operational-intelligence/predictive/telemetry).
4. Authority Immunity & Phase 5 Safety Boundaries.
"""

import uuid
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.config import settings
from app.modules.erp.models import Dispatch, Ticket, Order, Customer, Plant, Vehicle, Driver
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.ml_batch_cursor import MLBatchProcessingCursor
from app.modules.operational_intelligence.services.authoritative_resolver import AuthoritativeModelResolver
from app.modules.operational_intelligence.services.batch_prediction_engine import BatchPredictionEngine
from app.modules.operational_intelligence.services.predictive_telemetry_service import PredictiveTelemetryService
from app.modules.operational_intelligence.routers.predictive_management_router import _batch_run_lock
from app.modules.operational_intelligence.tests.conftest import TestAsyncSessionFactory, test_engine

BASE_URL = "/fleet-api/v1/operational-intelligence/predictive"


@pytest_asyncio.fixture
async def ws64_session():
    """Isolated session fixture for WS6.4 testing."""
    async with test_engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ml_batch_processing_cursors (
                id UUID PRIMARY KEY,
                batch_job_name VARCHAR(100) NOT NULL UNIQUE,
                last_processed_timestamp TIMESTAMPTZ,
                last_processed_dispatch_id VARCHAR(100),
                total_dispatches_processed BIGINT NOT NULL DEFAULT 0,
                total_snapshots_generated BIGINT NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                created_by VARCHAR(100),
                updated_by VARCHAR(100),
                is_deleted BOOLEAN NOT NULL DEFAULT false,
                deleted_at TIMESTAMPTZ,
                version INT NOT NULL DEFAULT 1
            );
        """))
        await conn.execute(text("DELETE FROM ml_batch_processing_cursors;"))
        await conn.execute(text("DELETE FROM dispatches WHERE dispatch_number LIKE 'DISP-%';"))

    async with TestAsyncSessionFactory() as session:
        await session.rollback()
        yield session


from app.dependencies.common import get_db_session

@pytest_asyncio.fixture
async def api_client(ws64_session: AsyncSession):
    """Async HTTP client fixture for REST API endpoints with session dependency override."""
    async def _override_get_db():
        yield ws64_session

    app.dependency_overrides[get_db_session] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def _seed_all_promoted_models(session: AsyncSession) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    families = ["delay_regressor", "turnaround_regressor", "sla_breach_classifier", "plant_risk_classifier"]
    model_ids = {}

    for fam in families:
        uid = uuid.uuid4().hex[:6]
        sha = hashlib.sha256(f"art-{fam}-{uid}".encode()).hexdigest()
        mid = uuid.uuid4()
        model_ids[fam] = mid
        model = MLModelVersion(
            id=mid,
            model_name=fam,
            model_category="REGRESSION" if "regressor" in fam else "CLASSIFICATION",
            algorithm="LIGHTGBM",
            target_name="target",
            training_dataset_id=f"DS-{uid}",
            artifact_path=f"/tmp/virtual_art_{fam}_{uid}.pkl",
            artifact_sha256=sha,
            artifact_size_bytes=2048,
            training_timestamp=now,
            model_version=f"v1.1.0-prom-{uid}",
            feature_set_version="FeatureSetV1",
            lifecycle_status="PROMOTED",
            is_deleted=False,
        )
        session.add(model)

    await session.commit()

    max_ts_res = await session.execute(text("SELECT max(created_at), max(id::text) FROM dispatches;"))
    row = max_ts_res.first()
    max_ts, max_id = row[0] if row else None, row[1] if row else None

    cursor = MLBatchProcessingCursor(
        id=str(uuid.uuid4()),
        batch_job_name="DISPATCH_BATCH_INFERENCE_CURSOR",
        last_processed_timestamp=max_ts,
        last_processed_dispatch_id=max_id,
        total_dispatches_processed=0,
        total_snapshots_generated=0,
    )
    session.add(cursor)
    await session.commit()
    return model_ids


def _make_dummy_snapshot(dispatch_id: str, model_name: str = "delay_regressor", is_stale: bool = False, model_version_id: Optional[Any] = None) -> MLPredictionSnapshot:
    now = datetime.now(timezone.utc)
    return MLPredictionSnapshot(
        id=uuid.uuid4(),
        prediction_snapshot_id=f"SNAP-{uuid.uuid4().hex[:8]}",
        idempotency_key=f"IK-{uuid.uuid4().hex[:8]}",
        prediction_timestamp=now,
        prediction_status="GENERATED",
        model_version_id=model_version_id if model_version_id else uuid.uuid4(),
        model_name=model_name,
        model_version="v1.0.0-prom",
        artifact_sha256="sha-dummy",
        feature_set_version="FeatureSetV1",
        dispatch_id=dispatch_id,
        dispatch_code="DISP-TEST-01",
        plant_code="PLANT-TEST-01",
        customer_code="CUST-TEST-01",
        vehicle_code="VEH-TEST-01",
        input_features={"feature": 1.0},
        prediction_outputs={"raw_output": 12.5},
        predicted_value=12.5,
        confidence_score=0.9,
        is_stale=is_stale,
    )


# ============================================================================
# Suite 1: Batch Management Endpoint Tests (1–5)
# ============================================================================

@pytest.mark.asyncio
async def test_ws64_01_batch_run_success(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 1: POST /predictive/batch-run triggers batch prediction engine and returns HTTP 200."""
    await _seed_all_promoted_models(ws64_session)

    res_max = await ws64_session.execute(text("SELECT COALESCE(max(created_at), now()) FROM dispatches;"))
    base_time = res_max.scalar()
    now = (base_time + timedelta(hours=1)).replace(microsecond=0)

    u1 = uuid.uuid4()
    p = Plant(id=uuid.uuid4(), name="ACC VASCO", code=f"PLANT-{uuid.uuid4().hex[:6]}")
    ws64_session.add(p)
    v = Vehicle(id=uuid.uuid4(), code=f"VEH-{uuid.uuid4().hex[:6]}", license_plate="GA01V1234")
    ws64_session.add(v)
    drv = Driver(id=uuid.uuid4(), employee_id=f"EMP-{uuid.uuid4().hex[:6]}", name="John Doe")
    ws64_session.add(drv)
    c = Customer(id=uuid.uuid4(), name="CUST-REST-01", code=f"CUST-{uuid.uuid4().hex[:6]}")
    ws64_session.add(c)
    o = Order(id=uuid.uuid4(), customer_id=c.id, order_number=f"ORD-{uuid.uuid4().hex[:6]}", order_date=now)
    ws64_session.add(o)
    t = Ticket(id=uuid.uuid4(), order_id=o.id, plant_id=p.id, ticket_number=f"TICK-{uuid.uuid4().hex[:6]}", ticket_date=now, delivered_volume_m3=6.0)
    ws64_session.add(t)
    d = Dispatch(id=u1, ticket_id=t.id, vehicle_id=v.id, driver_id=drv.id, plant_id=p.id, customer_id=c.id, dispatch_number=f"DISP-{uuid.uuid4().hex[:6]}", dispatch_date=now, created_at=now)
    ws64_session.add(d)
    await ws64_session.commit()

    response = await api_client.post(
        f"{BASE_URL}/batch-run",
        json={"max_dispatches": 10, "force_reprocess": False},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["dispatches_processed"] == 1
    assert body["data"]["snapshots_created"] == 4
    assert body["data"]["force_reprocess_requested"] is False


@pytest.mark.asyncio
async def test_ws64_02_batch_run_empty_noop(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 2: POST /predictive/batch-run when database is up-to-date returns HTTP 200 with 0 processed dispatches."""
    await _seed_all_promoted_models(ws64_session)

    response = await api_client.post(
        f"{BASE_URL}/batch-run",
        json={"max_dispatches": 20},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["dispatches_processed"] == 0


@pytest.mark.asyncio
async def test_ws64_03_batch_run_max_dispatches_bounds(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 3: POST /predictive/batch-run with max_dispatches out of bounds (0 or 1001) returns HTTP 422."""
    await _seed_all_promoted_models(ws64_session)

    # Test lower bound 0
    resp1 = await api_client.post(f"{BASE_URL}/batch-run", json={"max_dispatches": 0})
    assert resp1.status_code == 422

    # Test upper bound 1001
    resp2 = await api_client.post(f"{BASE_URL}/batch-run", json={"max_dispatches": 1001})
    assert resp2.status_code == 422
@pytest.mark.asyncio
async def test_ws64_04_batch_run_concurrency_lock(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 4: Concurrent POST /predictive/batch-run when lock is acquired returns HTTP 409 BATCH_ALREADY_RUNNING."""
    await _seed_all_promoted_models(ws64_session)

    async with _batch_run_lock:
        response = await api_client.post(
            f"{BASE_URL}/batch-run",
            json={"max_dispatches": 5},
        )
        assert response.status_code == 409
        assert "BATCH_ALREADY_RUNNING" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_ws64_05_batch_run_force_reprocess(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 5: POST /predictive/batch-run with force_reprocess=True passes parameter to batch prediction engine."""
    await _seed_all_promoted_models(ws64_session)

    response = await api_client.post(
        f"{BASE_URL}/batch-run",
        json={"max_dispatches": 10, "force_reprocess": True},
    )
    assert response.status_code == 200
    assert response.json()["data"]["force_reprocess_requested"] is True


# ============================================================================
# Suite 2: Snapshot Invalidation REST Endpoint Tests (6–14)
# ============================================================================

@pytest.mark.asyncio
async def test_ws64_06_invalidation_dispatch_scoped(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 6: POST /predictive/invalidate-snapshots targeting dispatch_id invalidates matching active snapshots."""
    models = await _seed_all_promoted_models(ws64_session)

    u1 = str(uuid.uuid4())
    snap = _make_dummy_snapshot(dispatch_id=u1, model_name="delay_regressor", model_version_id=models["delay_regressor"])
    ws64_session.add(snap)
    await ws64_session.commit()

    response = await api_client.post(
        f"{BASE_URL}/invalidate-snapshots",
        json={"dispatch_id": u1, "reason": "Customer updated delivery location"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["invalidated_snapshots_count"] == 1
    assert body["data"]["dispatch_id"] == u1

    # Verify DB state
    updated_snap = await ws64_session.get(MLPredictionSnapshot, snap.id)
    assert updated_snap.is_stale is True


@pytest.mark.asyncio
async def test_ws64_07_invalidation_model_family_scoped(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 7: POST /predictive/invalidate-snapshots targeting model_family invalidates matching snapshots."""
    models = await _seed_all_promoted_models(ws64_session)

    snap = _make_dummy_snapshot(dispatch_id=str(uuid.uuid4()), model_name="plant_risk_classifier", model_version_id=models["plant_risk_classifier"])
    ws64_session.add(snap)
    await ws64_session.commit()

    response = await api_client.post(
        f"{BASE_URL}/invalidate-snapshots",
        json={"model_family": "plant_risk_classifier", "reason": "Model threshold re-calibration"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["invalidated_snapshots_count"] == 1


@pytest.mark.asyncio
async def test_ws64_08_invalidation_missing_target_rejection(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 8: POST /predictive/invalidate-snapshots with both target fields omitted returns HTTP 422."""
    response = await api_client.post(
        f"{BASE_URL}/invalidate-snapshots",
        json={"reason": "Testing unscoped request safety rejection"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_ws64_09_invalidation_invalid_dispatch_id(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 9: POST /predictive/invalidate-snapshots with malformed dispatch_id returns HTTP 400."""
    response = await api_client.post(
        f"{BASE_URL}/invalidate-snapshots",
        json={"dispatch_id": "not-a-valid-uuid", "reason": "Testing invalid dispatch UUID format"},
    )
    assert response.status_code == 400
    assert "Invalid dispatch_id UUID format" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_ws64_10_invalidation_invalid_model_family(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 10: POST /predictive/invalidate-snapshots with unknown model_family returns HTTP 400."""
    response = await api_client.post(
        f"{BASE_URL}/invalidate-snapshots",
        json={"model_family": "unknown_super_model", "reason": "Testing unknown model family rejection"},
    )
    assert response.status_code == 400
    assert "Unknown model_family" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_ws64_11_invalidation_required_reason_validation(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 11: POST /predictive/invalidate-snapshots missing reason or reason < 5 chars returns HTTP 422."""
    # Omitted reason
    resp1 = await api_client.post(
        f"{BASE_URL}/invalidate-snapshots",
        json={"model_family": "delay_regressor"},
    )
    assert resp1.status_code == 422

    # Reason < 5 chars
    resp2 = await api_client.post(
        f"{BASE_URL}/invalidate-snapshots",
        json={"model_family": "delay_regressor", "reason": "bad"},
    )
    assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_ws64_12_invalidation_zero_match(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 12: POST /predictive/invalidate-snapshots targeting non-existent dispatch returns HTTP 200 with count 0."""
    random_uuid = str(uuid.uuid4())
    response = await api_client.post(
        f"{BASE_URL}/invalidate-snapshots",
        json={"dispatch_id": random_uuid, "reason": "Non-existent dispatch test"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["invalidated_snapshots_count"] == 0


@pytest.mark.asyncio
async def test_ws64_13_invalidation_multiple_match(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 13: POST /predictive/invalidate-snapshots targeting a family invalidates all active matching snapshots."""
    models = await _seed_all_promoted_models(ws64_session)

    for _ in range(3):
        snap = _make_dummy_snapshot(dispatch_id=str(uuid.uuid4()), model_name="turnaround_regressor", model_version_id=models["turnaround_regressor"])
        ws64_session.add(snap)
    await ws64_session.commit()

    response = await api_client.post(
        f"{BASE_URL}/invalidate-snapshots",
        json={"model_family": "turnaround_regressor", "reason": "Batch turnaround model invalidation"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["invalidated_snapshots_count"] == 3


@pytest.mark.asyncio
async def test_ws64_14_invalidation_idempotency(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 14: Repeating invalidation call on already stale snapshots returns 0 newly invalidated count."""
    models = await _seed_all_promoted_models(ws64_session)

    u1 = str(uuid.uuid4())
    snap = _make_dummy_snapshot(dispatch_id=u1, model_name="sla_breach_classifier", model_version_id=models["sla_breach_classifier"])
    ws64_session.add(snap)
    await ws64_session.commit()

    # First invalidation
    resp1 = await api_client.post(
        f"{BASE_URL}/invalidate-snapshots",
        json={"dispatch_id": u1, "reason": "First invalidation call"},
    )
    assert resp1.json()["data"]["invalidated_snapshots_count"] == 1

    # Second invalidation (idempotent no-op)
    resp2 = await api_client.post(
        f"{BASE_URL}/invalidate-snapshots",
        json={"dispatch_id": u1, "reason": "Second invalidation call"},
    )
    assert resp2.json()["data"]["invalidated_snapshots_count"] == 0


# ============================================================================
# Suite 3: Authority Immunity & Phase 5 Safety Boundaries (15–18)
# ============================================================================

@pytest.mark.asyncio
async def test_ws64_15_invalidation_model_authority_immunity(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 15: Snapshot invalidation does NOT alter lifecycle_status of PROMOTED models in ml_model_versions."""
    await _seed_all_promoted_models(ws64_session)

    response = await api_client.post(
        f"{BASE_URL}/invalidate-snapshots",
        json={"model_family": "delay_regressor", "reason": "Authority immunity test"},
    )
    assert response.status_code == 200

    # Assert model version remains PROMOTED in database
    stmt = select(MLModelVersion).where(MLModelVersion.model_name == "delay_regressor", MLModelVersion.lifecycle_status == "PROMOTED")
    res = await ws64_session.execute(stmt)
    models = list(res.scalars().all())
    assert len(models) >= 1
    assert all(m.lifecycle_status == "PROMOTED" for m in models)


@pytest.mark.asyncio
async def test_ws64_16_invalidation_model_lifecycle_immunity(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 16: CANDIDATE and REJECTED models in ml_model_versions remain untouched by snapshot invalidation."""
    now = datetime.now(timezone.utc)
    cand_model = MLModelVersion(
        id=str(uuid.uuid4()),
        model_name="delay_regressor",
        model_category="REGRESSION",
        algorithm="LIGHTGBM",
        target_name="target",
        training_dataset_id="DS-CAND",
        artifact_path="/tmp/cand.pkl",
        artifact_sha256="cand-sha",
        artifact_size_bytes=1024,
        training_timestamp=now,
        model_version="v1.2.0-cand",
        feature_set_version="FeatureSetV1",
        lifecycle_status="CANDIDATE",
        is_deleted=False,
    )
    ws64_session.add(cand_model)
    await ws64_session.commit()

    await api_client.post(
        f"{BASE_URL}/invalidate-snapshots",
        json={"model_family": "delay_regressor", "reason": "Lifecycle immunity test"},
    )

    refreshed_cand = await ws64_session.get(MLModelVersion, cand_model.id)
    assert refreshed_cand.lifecycle_status == "CANDIDATE"


@pytest.mark.asyncio
async def test_ws64_17_frozen_phase_5_immunity(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 17: Frozen Phase 5 historical datasets remain untouched after REST invalidation calls."""
    res_datasets = await ws64_session.execute(text("SELECT count(*) FROM ml_datasets;"))
    ds_count_before = res_datasets.scalar()

    await api_client.post(
        f"{BASE_URL}/invalidate-snapshots",
        json={"model_family": "delay_regressor", "reason": "Phase 5 dataset immunity test"},
    )

    res_datasets_after = await ws64_session.execute(text("SELECT count(*) FROM ml_datasets;"))
    ds_count_after = res_datasets_after.scalar()
    assert ds_count_before == ds_count_after


@pytest.mark.asyncio
async def test_ws64_18_unauthorized_broad_invalidation_rejection(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 18: Unscoped broad invalidation request fails closed with HTTP 422."""
    response = await api_client.post(
        f"{BASE_URL}/invalidate-snapshots",
        json={"dispatch_id": None, "model_family": None, "reason": "Broad invalidation test"},
    )
    assert response.status_code == 422


# ============================================================================
# Suite 4: Telemetry Observability & Read-Only Tests (19–24)
# ============================================================================

@pytest.mark.asyncio
async def test_ws64_19_telemetry_four_family_authority(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 19: GET /telemetry reports 4 promoted families and production_authority=AUTHORITATIVE."""
    await _seed_all_promoted_models(ws64_session)

    response = await api_client.get(f"{BASE_URL}/telemetry")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["production_authority"] == "AUTHORITATIVE"
    assert data["authoritative_model_count"] == 4
    assert len(data["missing_families"]) == 0
    assert "delay_regressor" in data["authority_status"]


@pytest.mark.asyncio
async def test_ws64_20_telemetry_active_stale_counts(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 20: Telemetry accurately breaks down total_snapshots, stale_snapshots, active_snapshots."""
    models = await _seed_all_promoted_models(ws64_session)

    s1 = _make_dummy_snapshot(dispatch_id=str(uuid.uuid4()), is_stale=False, model_version_id=models["delay_regressor"])
    s2 = _make_dummy_snapshot(dispatch_id=str(uuid.uuid4()), is_stale=True, model_version_id=models["delay_regressor"])
    ws64_session.add_all([s1, s2])
    await ws64_session.commit()

    response = await api_client.get(f"{BASE_URL}/telemetry")
    assert response.status_code == 200
    metrics = response.json()["data"]["snapshot_metrics"]
    assert metrics["total_snapshots"] >= 2
    assert metrics["stale_snapshots"] >= 1
    assert metrics["active_snapshots"] == metrics["total_snapshots"] - metrics["stale_snapshots"]


@pytest.mark.asyncio
async def test_ws64_21_telemetry_cursor_accuracy(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 21: Telemetry reports current batch processing cursor timestamps and total processed count."""
    await _seed_all_promoted_models(ws64_session)

    response = await api_client.get(f"{BASE_URL}/telemetry")
    assert response.status_code == 200
    cursor_data = response.json()["data"]["batch_cursor"]
    assert "last_processed_timestamp" in cursor_data
    assert "total_dispatches_processed" in cursor_data


@pytest.mark.asyncio
async def test_ws64_22_telemetry_updates_after_invalidation(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 22: Stale snapshots count in telemetry increments after snapshot invalidation."""
    models = await _seed_all_promoted_models(ws64_session)

    u1 = str(uuid.uuid4())
    snap = _make_dummy_snapshot(dispatch_id=u1, is_stale=False, model_version_id=models["delay_regressor"])
    ws64_session.add(snap)
    await ws64_session.commit()

    # Initial telemetry
    res1 = await api_client.get(f"{BASE_URL}/telemetry")
    stale1 = res1.json()["data"]["snapshot_metrics"]["stale_snapshots"]

    # Invalidate
    await api_client.post(
        f"{BASE_URL}/invalidate-snapshots",
        json={"dispatch_id": u1, "reason": "Telemetry update test"},
    )

    # Telemetry after invalidation
    res2 = await api_client.get(f"{BASE_URL}/telemetry")
    stale2 = res2.json()["data"]["snapshot_metrics"]["stale_snapshots"]
    assert stale2 == stale1 + 1


@pytest.mark.asyncio
async def test_ws64_23_telemetry_updates_after_batch(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 23: Telemetry snapshot metrics update after executing a batch run."""
    await _seed_all_promoted_models(ws64_session)

    res_max = await ws64_session.execute(text("SELECT COALESCE(max(created_at), now()) FROM dispatches;"))
    base_time = res_max.scalar()
    now = (base_time + timedelta(hours=1)).replace(microsecond=0)

    p = Plant(id=uuid.uuid4(), name="ACC VASCO", code=f"PLANT-{uuid.uuid4().hex[:6]}")
    ws64_session.add(p)
    v = Vehicle(id=uuid.uuid4(), code=f"VEH-{uuid.uuid4().hex[:6]}", license_plate="GA01V1234")
    ws64_session.add(v)
    drv = Driver(id=uuid.uuid4(), employee_id=f"EMP-{uuid.uuid4().hex[:6]}", name="John Doe")
    ws64_session.add(drv)
    c = Customer(id=uuid.uuid4(), name="CUST-T23", code=f"CUST-{uuid.uuid4().hex[:6]}")
    ws64_session.add(c)
    o = Order(id=uuid.uuid4(), customer_id=c.id, order_number=f"ORD-{uuid.uuid4().hex[:6]}", order_date=now)
    ws64_session.add(o)
    t = Ticket(id=uuid.uuid4(), order_id=o.id, plant_id=p.id, ticket_number=f"TICK-{uuid.uuid4().hex[:6]}", ticket_date=now, delivered_volume_m3=6.0)
    ws64_session.add(t)
    d = Dispatch(id=uuid.uuid4(), ticket_id=t.id, vehicle_id=v.id, driver_id=drv.id, plant_id=p.id, customer_id=c.id, dispatch_number=f"DISP-{uuid.uuid4().hex[:6]}", dispatch_date=now, created_at=now)
    ws64_session.add(d)
    await ws64_session.commit()

    # Initial telemetry
    t1 = (await api_client.get(f"{BASE_URL}/telemetry")).json()["data"]["snapshot_metrics"]["total_snapshots"]

    # Run batch
    await api_client.post(f"{BASE_URL}/batch-run", json={"max_dispatches": 10})

    # Subsequent telemetry
    t2 = (await api_client.get(f"{BASE_URL}/telemetry")).json()["data"]["snapshot_metrics"]["total_snapshots"]
    assert t2 == t1 + 4  # 4 model families


@pytest.mark.asyncio
async def test_ws64_24_telemetry_read_only_guarantee(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 24: Repeated calls to GET /telemetry do NOT mutate cursor, prediction snapshots, or database state."""
    await _seed_all_promoted_models(ws64_session)

    res1 = await api_client.get(f"{BASE_URL}/telemetry")
    res2 = await api_client.get(f"{BASE_URL}/telemetry")
    d1 = res1.json()["data"]
    d2 = res2.json()["data"]
    d1.pop("generated_at", None)
    d2.pop("generated_at", None)
    if "batch_cursor" in d1:
        d1["batch_cursor"].pop("cursor_age_seconds", None)
    if "batch_cursor" in d2:
        d2["batch_cursor"].pop("cursor_age_seconds", None)
    assert d1 == d2


# ============================================================================
# Suite 5: Failure Handling & Atomic Rollback Tests (25–29)
# ============================================================================

@pytest.mark.asyncio
async def test_ws64_25_batch_service_failure_mapped(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 25: Unhandled BatchPredictionEngine exception is caught and mapped to HTTP 500."""
    with patch.object(BatchPredictionEngine, "process_incremental_batch", side_effect=RuntimeError("Simulated engine crash")):
        response = await api_client.post(
            f"{BASE_URL}/batch-run",
            json={"max_dispatches": 10},
        )
        assert response.status_code == 500
        assert "Batch execution failed" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_ws64_26_db_transaction_rollback(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 26: Exception inside invalidation service triggers clean HTTP 500 without leaving open transaction."""
    with patch.object(PredictiveTelemetryService, "invalidate_snapshots", side_effect=RuntimeError("Simulated DB failure")):
        response = await api_client.post(
            f"{BASE_URL}/invalidate-snapshots",
            json={"model_family": "delay_regressor", "reason": "Transaction rollback test"},
        )
        assert response.status_code == 500


@pytest.mark.asyncio
async def test_ws64_27_invalidation_transaction_rollback(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 27: Session execution failure during invalidation rolls back atomically without partial state changes."""
    models = await _seed_all_promoted_models(ws64_session)

    u1 = str(uuid.uuid4())
    snap = _make_dummy_snapshot(dispatch_id=u1, is_stale=False, model_version_id=models["delay_regressor"])
    ws64_session.add(snap)
    await ws64_session.commit()

    with patch.object(AsyncSession, "execute", side_effect=RuntimeError("Simulated SQL failure")):
        response = await api_client.post(
            f"{BASE_URL}/invalidate-snapshots",
            json={"dispatch_id": u1, "reason": "Atomic rollback test"},
        )
        assert response.status_code == 500

    # Verify snapshot remains active (not stale)
    refreshed = await ws64_session.get(MLPredictionSnapshot, snap.id)
    assert refreshed.is_stale is False


@pytest.mark.asyncio
async def test_ws64_28_no_partial_invalidation(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 28: Targeted invalidation is atomic across multiple matching snapshots."""
    models = await _seed_all_promoted_models(ws64_session)

    u1 = str(uuid.uuid4())
    s1 = _make_dummy_snapshot(dispatch_id=u1, model_name="delay_regressor", model_version_id=models["delay_regressor"])
    s2 = _make_dummy_snapshot(dispatch_id=u1, model_name="turnaround_regressor", model_version_id=models["turnaround_regressor"])
    ws64_session.add_all([s1, s2])
    await ws64_session.commit()

    response = await api_client.post(
        f"{BASE_URL}/invalidate-snapshots",
        json={"dispatch_id": u1, "reason": "Atomic multi-invalidation test"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["invalidated_snapshots_count"] == 2


@pytest.mark.asyncio
async def test_ws64_29_no_cursor_corruption(ws64_session: AsyncSession, api_client: AsyncClient):
    """Test 29: Failed REST management API calls leave persistent MLBatchProcessingCursor in consistent state."""
    await _seed_all_promoted_models(ws64_session)

    # Initial cursor
    stmt = select(MLBatchProcessingCursor).where(MLBatchProcessingCursor.batch_job_name == "DISPATCH_BATCH_INFERENCE_CURSOR")
    c1 = (await ws64_session.execute(stmt)).scalars().first()
    ts1 = c1.last_processed_timestamp

    # Failed request
    with patch.object(BatchPredictionEngine, "process_incremental_batch", side_effect=RuntimeError("Engine failure")):
        await api_client.post(f"{BASE_URL}/batch-run", json={"max_dispatches": 10})

    # Cursor unchanged
    c2 = (await ws64_session.execute(stmt)).scalars().first()
    assert c2.last_processed_timestamp == ts1
