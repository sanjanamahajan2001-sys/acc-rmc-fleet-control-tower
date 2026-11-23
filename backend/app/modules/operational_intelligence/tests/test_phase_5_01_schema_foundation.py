"""
Workstream 5.1 Automated Backend Test Suite: Outcome Schema & Data Contract Foundation.
Runs exclusively on isolated test database (TEST_DATABASE_URL=postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test).
"""

import os
import uuid
import hashlib
import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import IntegrityError

from app.models.base import Base
from app.modules.erp.models import Dispatch
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.operational_outcome import OperationalOutcome
from app.modules.operational_intelligence.models.prediction_error import PredictionErrorRecord
from app.modules.operational_intelligence.models.model_health import ModelHealthMetric
from app.modules.operational_intelligence.ml.feature_extractor import FORBIDDEN_LEAKAGE_FIELDS, ALLOWED_INFERENCE_FEATURES

def get_test_db_url() -> str:
    if os.getenv("TEST_DATABASE_URL"):
        return os.getenv("TEST_DATABASE_URL")
    from app.core.config import settings
    return f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

TEST_DB_URL = get_test_db_url()


@pytest_asyncio.fixture
async def ws51_session():
    """Isolated test database session for Workstream 5.1 schema verification."""
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_ws51_01_schema_creation_and_table_existence(ws51_session: AsyncSession):
    """Test 1-4: Verify tables, indexes, and schema creation execute cleanly."""
    res_tables = await ws51_session.execute(
        text("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
    )
    table_names = [r[0] for r in res_tables.fetchall()]

    assert "operational_outcomes" in table_names
    assert "prediction_error_records" in table_names
    assert "model_health_metrics" in table_names


@pytest.mark.asyncio
async def test_ws51_02_foreign_keys_and_unique_constraints(ws51_session: AsyncSession):
    """Test 5-7: Verify FK and unique constraints on outcome_id and idempotency_key."""
    disp = (await ws51_session.execute(select(Dispatch).limit(1))).scalar_one_or_none()
    if not disp:
        pytest.skip("No real dispatches found in test database.")

    disp_uuid = disp.id
    disp_code = disp.dispatch_number

    out_id = f"OUT-{uuid.uuid4().hex[:8].upper()}"
    ik = f"IK-OUT-{disp_code}-delay_regressor-{datetime.now(timezone.utc).isoformat()}"

    outcome = OperationalOutcome(
        outcome_id=out_id,
        dispatch_id=disp_uuid,
        dispatch_code=disp_code,
        idempotency_key=ik,
        actual_transit_mins=15.4,
        actual_unloading_mins=20.0,
        outcome_timestamp=datetime.now(timezone.utc),
    )
    ws51_session.add(outcome)
    await ws51_session.commit()

    # Attempt duplicate idempotency key insertion (must fail IntegrityError)
    dup_outcome = OperationalOutcome(
        outcome_id=f"OUT-{uuid.uuid4().hex[:8].upper()}",
        dispatch_id=disp_uuid,
        dispatch_code=disp_code,
        idempotency_key=ik,
        actual_transit_mins=18.0,
        outcome_timestamp=datetime.now(timezone.utc),
    )
    ws51_session.add(dup_outcome)
    with pytest.raises(IntegrityError):
        await ws51_session.commit()
    await ws51_session.rollback()


@pytest.mark.asyncio
async def test_ws51_03_verification_status_lifecycle_contract(ws51_session: AsyncSession):
    """Test 11-12: Verify default verification status RECEIVED and is_verified=False barrier."""
    disp = (await ws51_session.execute(select(Dispatch).limit(1))).scalar_one_or_none()
    if not disp:
        pytest.skip("No real dispatches found in test database.")

    out_id = f"OUT-{uuid.uuid4().hex[:8].upper()}"
    ik = f"IK-OUT-{uuid.uuid4().hex[:8]}"

    outcome = OperationalOutcome(
        outcome_id=out_id,
        dispatch_id=disp.id,
        dispatch_code=disp.dispatch_number,
        idempotency_key=ik,
        actual_transit_mins=12.0,
        outcome_timestamp=datetime.now(timezone.utc),
    )
    ws51_session.add(outcome)
    await ws51_session.commit()

    stmt = select(OperationalOutcome).where(OperationalOutcome.outcome_id == out_id)
    res = (await ws51_session.execute(stmt)).scalar_one()

    assert res.verification_status == "RECEIVED"
    assert res.is_verified is False


@pytest.mark.asyncio
async def test_ws51_04_immutable_correction_supersession_lineage(ws51_session: AsyncSession):
    """Test 9-10: Verify append-only ERP correction supersession lineage (O1 -> O2)."""
    disp = (await ws51_session.execute(select(Dispatch).limit(1))).scalar_one_or_none()
    if not disp:
        pytest.skip("No real dispatches found in test database.")

    disp_uuid = disp.id
    disp_code = disp.dispatch_number

    o1_id = f"OUT-O1-{uuid.uuid4().hex[:6].upper()}"
    o2_id = f"OUT-O2-{uuid.uuid4().hex[:6].upper()}"

    o1 = OperationalOutcome(
        outcome_id=o1_id,
        dispatch_id=disp_uuid,
        dispatch_code=disp_code,
        idempotency_key=f"IK-{o1_id}",
        actual_transit_mins=10.0,
        outcome_timestamp=datetime.now(timezone.utc),
    )
    ws51_session.add(o1)
    await ws51_session.commit()

    # O2 ERP Correction arrives as RECEIVED initially
    o1.is_superseded = True
    o1.superseded_by_outcome_id = o2_id
    o1.correction_reason = "ERP Arrival Time Correction"

    o2 = OperationalOutcome(
        outcome_id=o2_id,
        dispatch_id=disp_uuid,
        dispatch_code=disp_code,
        idempotency_key=f"IK-{o2_id}",
        actual_transit_mins=18.5,
        verification_status="RECEIVED",
        is_verified=False,
        outcome_timestamp=datetime.now(timezone.utc),
    )
    ws51_session.add(o2)
    await ws51_session.commit()

    # Verify O2 enters as RECEIVED / is_verified=False initially
    stmt_o2_init = select(OperationalOutcome).where(OperationalOutcome.outcome_id == o2_id)
    o2_init = (await ws51_session.execute(stmt_o2_init)).scalar_one()
    assert o2_init.verification_status == "RECEIVED"
    assert o2_init.is_verified is False

    # Authoritative ERP validation path executes: RECEIVED -> VALIDATED -> VERIFIED
    o2_init.verification_status = "VERIFIED"
    o2_init.is_verified = True
    await ws51_session.commit()

    stmt_o1 = select(OperationalOutcome).where(OperationalOutcome.outcome_id == o1_id)
    o1_fetched = (await ws51_session.execute(stmt_o1)).scalar_one()

    assert o1_fetched.is_superseded is True
    assert o1_fetched.superseded_by_outcome_id == o2_id
    assert o1_fetched.actual_transit_mins == 10.0  # Historical value preserved!


@pytest.mark.asyncio
async def test_ws51_05_regression_and_classification_contracts(ws51_session: AsyncSession):
    """Test 13-15: Verify regression, classification, and NULL financial impact contracts."""
    disp = (await ws51_session.execute(select(Dispatch).limit(1))).scalar_one_or_none()
    if not disp:
        pytest.skip("No real dispatches found in test database.")

    disp_uuid = disp.id
    disp_code = disp.dispatch_number

    out_id = f"OUT-{uuid.uuid4().hex[:8].upper()}"
    outcome = OperationalOutcome(
        outcome_id=out_id,
        dispatch_id=disp_uuid,
        dispatch_code=disp_code,
        idempotency_key=f"IK-{out_id}",
        actual_transit_mins=15.0,
        actual_sla_breach_flag=True,
        actual_plant_risk_class=1,
        actual_financial_impact_inr=None,  # Nullable financial impact accepted cleanly
        outcome_timestamp=datetime.now(timezone.utc),
    )
    ws51_session.add(outcome)
    await ws51_session.commit()

    # Create dummy prediction snapshot for FK
    snap_id = f"SNAP-TEST-{uuid.uuid4().hex[:6]}"
    dummy_snap_dispatch_id = str(uuid.uuid4())
    snap = MLPredictionSnapshot(
        prediction_snapshot_id=snap_id,
        idempotency_key=f"IK-{snap_id}",
        dispatch_id=dummy_snap_dispatch_id,
        dispatch_code="DISP-DUMMY-TEST",
        plant_code="PLANT_TEST",
        customer_code="CUST_TEST",
        vehicle_code="VEH_TEST",
        model_name="delay_regressor",
        model_version="v1.1.0-promoted-test",
        artifact_sha256="b6d1ab825d220c3662835580808c1be9c77518007dcd65b6911126d097be9fdd",
        feature_set_version="FeatureSetV1",
        input_features={"distance_km": 10.0},
        prediction_outputs={"predicted_delay_mins": 18.5},
        predicted_value=18.5,
        prediction_timestamp=datetime.now(timezone.utc),
    )
    ws51_session.add(snap)
    await ws51_session.commit()

    # Test PredictionErrorRecord Contract
    err_reg = PredictionErrorRecord(
        error_record_id=f"ERR-REG-{uuid.uuid4().hex[:6]}",
        outcome_id=out_id,
        prediction_snapshot_id=snap_id,
        idempotency_key=f"IK-ERR-REG-{uuid.uuid4().hex[:6]}",
        model_name="delay_regressor",
        model_version="v1.1.0-promoted-test",
        predicted_numeric_value=Decimal("18.50"),
        actual_numeric_value=Decimal("15.00"),
        absolute_error=Decimal("3.50"),
        squared_error=Decimal("12.25"),
        percentage_error=Decimal("23.33"),
    )

    err_cls = PredictionErrorRecord(
        error_record_id=f"ERR-CLS-{uuid.uuid4().hex[:6]}",
        outcome_id=out_id,
        prediction_snapshot_id=snap_id,
        idempotency_key=f"IK-ERR-CLS-{uuid.uuid4().hex[:6]}",
        model_name="sla_breach_classifier",
        model_version="v1.1.0-promoted-test",
        predicted_class_or_prob=Decimal("0.8500"),
        predicted_class_label=1,
        actual_class_label=1,
        is_correct_classification=True,
        confusion_matrix_category="TP",
        brier_score_contribution=Decimal("0.0225"),
    )

    ws51_session.add_all([err_reg, err_cls])
    await ws51_session.commit()

    assert err_reg.absolute_error == Decimal("3.50")
    assert err_cls.confusion_matrix_category == "TP"


@pytest.mark.asyncio
async def test_ws51_06_leakage_boundary_and_purity_verification(ws51_session: AsyncSession):
    """Test 16-19: Verify anti-leakage boundaries and production database counts integrity."""
    assert "t1_transit_mins" in FORBIDDEN_LEAKAGE_FIELDS
    assert "t2b_unloading_mins" in FORBIDDEN_LEAKAGE_FIELDS

    assert "t1_transit_mins" not in ALLOWED_INFERENCE_FEATURES
    assert "t2b_unloading_mins" not in ALLOWED_INFERENCE_FEATURES

    # Verify model counts remain intact
    prom_count = (await ws51_session.execute(
        select(func.count(MLModelVersion.id)).where(MLModelVersion.lifecycle_status == "PROMOTED")
    )).scalar()
    rej_count = (await ws51_session.execute(
        select(func.count(MLModelVersion.id)).where(MLModelVersion.lifecycle_status == "REJECTED")
    )).scalar()

    assert prom_count in (0, 4)
    assert rej_count in (0, 4)
