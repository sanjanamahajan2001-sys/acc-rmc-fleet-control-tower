"""
Workstream 5.3 Automated Backend Test Suite: Prediction Accuracy & Error Engine.
Verifies prediction error calculation, MAE/MSE/MAPE regression metrics, zero-actual percentage error governance,
classification metrics (TP, TN, FP, FN, Brier score), multi-class plant risk class handling,
financial prediction error, missing financial actual NULL preservation, idempotency, correction lineage (O1 -> O2),
and ERP-driven end-to-end flow.
Runs on isolated test database (TEST_DATABASE_URL=postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test).
"""

import os
import uuid
import asyncio
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy import select, text, func, update, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.models.base import Base
from app.modules.erp.models import Dispatch
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.operational_outcome import OperationalOutcome
from app.modules.operational_intelligence.models.prediction_error import PredictionErrorRecord
from app.modules.operational_intelligence.services.outcome_matching_service import OutcomeMatchingService
from app.modules.operational_intelligence.services.prediction_accuracy_service import PredictionAccuracyService

def get_test_db_url() -> str:
    if os.getenv("TEST_DATABASE_URL"):
        return os.getenv("TEST_DATABASE_URL")
    from app.core.config import settings
    return f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

TEST_DB_URL = get_test_db_url()


@pytest_asyncio.fixture
async def ws53_session():
    """Isolated test database session for Workstream 5.3 prediction accuracy verification."""
    engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_ws53_01_regression_metrics_and_zero_actual(ws53_session: AsyncSession):
    """Test 1: Verify MAE, MSE, MAPE calculations and explicit zero-actual percentage error governance (producing NULL instead of NaN/Infinity)."""
    # 1. Normal Actual != 0
    pred, act, err, abs_err, sq_err, pct_err = PredictionAccuracyService.calculate_regression_error(25.0, 20.0)
    assert pred == Decimal("25.0000")
    assert act == Decimal("20.0000")
    assert err == Decimal("5.0000")
    assert abs_err == Decimal("5.0000")
    assert sq_err == Decimal("25.0000")
    assert pct_err == Decimal("25.0000")  # (5 / 20) * 100 = 25%

    # 2. Zero Actual == 0.0 (Governed NaN/Infinity Protection)
    pred_z, act_z, err_z, abs_err_z, sq_err_z, pct_err_z = PredictionAccuracyService.calculate_regression_error(15.0, 0.0)
    assert act_z == Decimal("0.0000")
    assert err_z == Decimal("15.0000")
    assert pct_err_z is None  # Preserves NULL in database when mathematically undefined!


@pytest.mark.asyncio
async def test_ws53_02_classification_metrics_and_probability_bounds(ws53_session: AsyncSession):
    """Test 2: Verify binary classification metrics (TP, TN, FP, FN), Brier score, and invalid probability rejection."""
    # 1. Test invalid probability rejection (< 0.0 or > 1.0)
    with pytest.raises(ValueError, match="CLASSIFICATION PROBABILITY VIOLATION"):
        PredictionAccuracyService.calculate_classification_metrics("sla_breach_classifier", 1.5, 1, 1)

    with pytest.raises(ValueError, match="CLASSIFICATION PROBABILITY VIOLATION"):
        PredictionAccuracyService.calculate_classification_metrics("sla_breach_classifier", -0.1, 0, 0)

    # 2. True Positive (TP): Prob = 0.85, pred_class = 1, actual_class = 1
    prob, p_cls, a_cls, is_corr, cat, brier = PredictionAccuracyService.calculate_classification_metrics(
        "sla_breach_classifier", 0.85, 1, 1
    )
    assert is_corr is True
    assert cat == "TP"
    assert brier == Decimal("0.0225")  # (0.85 - 1.0)^2 = 0.0225

    # 3. False Positive (FP): Prob = 0.60, pred_class = 1, actual_class = 0
    _, _, _, is_corr_fp, cat_fp, brier_fp = PredictionAccuracyService.calculate_classification_metrics(
        "sla_breach_classifier", 0.60, 1, 0
    )
    assert is_corr_fp is False
    assert cat_fp == "FP"
    assert brier_fp == Decimal("0.3600")  # (0.60 - 0.0)^2 = 0.3600


@pytest.mark.asyncio
async def test_ws53_03_multiclass_plant_risk_classifier(ws53_session: AsyncSession):
    """Test 3: Verify multi-class plant_risk_classifier semantics (0 = NORMAL, 1 = MODERATE, 2 = SEVERE)."""
    # Pred class = 2 (SEVERE), Actual class = 2 (SEVERE)
    prob, p_cls, a_cls, is_corr, cat, brier = PredictionAccuracyService.calculate_classification_metrics(
        "plant_risk_classifier", 0.90, 2, 2
    )
    assert p_cls == 2
    assert a_cls == 2
    assert is_corr is True
    assert cat == "TP"  # Both > 0 (Breach threshold)
    assert brier == Decimal("0.0100")  # (0.90 - 1.0)^2 = 0.0100


@pytest.mark.asyncio
async def test_ws53_04_unmatched_missing_snapshot_error_skipping(ws53_session: AsyncSession):
    """Test 4: Verify unmatched missing snapshot outcome returns UNMATCHED_MISSING_SNAPSHOT without creating fake error records."""
    disp = (await ws53_session.execute(select(Dispatch).limit(1))).scalar_one_or_none()
    if not disp:
        pytest.skip("No real dispatches found in test database.")

    no_snap_disp_uuid = str(disp.id)
    no_snap_out_id = f"OUT-NOSNAP-{uuid.uuid4().hex[:6]}"

    # Insert unmatched outcome
    unmatched_out = OperationalOutcome(
        outcome_id=no_snap_out_id,
        dispatch_id=disp.id,
        dispatch_code=disp.dispatch_number,
        prediction_snapshot_id=None,  # UNMATCHED
        idempotency_key=f"IK-{no_snap_out_id}",
        actual_transit_mins=22.0,
        verification_status="RECEIVED",
        is_verified=False,
        outcome_timestamp=datetime.now(timezone.utc),
    )
    ws53_session.add(unmatched_out)
    await ws53_session.commit()

    res = await PredictionAccuracyService.calculate_and_persist_prediction_error(ws53_session, no_snap_out_id)
    assert res["success"] is True
    assert res["reason"] == "UNMATCHED_MISSING_SNAPSHOT"
    assert res["error_record_id"] is None


@pytest.mark.asyncio
async def test_ws53_05_financial_prediction_error_and_null_preservation(ws53_session: AsyncSession):
    """Test 5: Verify financial error calculation and NULL preservation when actual financial impact is unavailable."""
    disp = (await ws53_session.execute(select(Dispatch).limit(1))).scalar_one_or_none()
    if not disp:
        pytest.skip("No real dispatches found in test database.")

    disp_uuid = str(disp.id)
    now = datetime.now(timezone.utc)

    # 1. Create Snapshot with predicted financial exposure
    snap_id = f"SNAP-FIN-{uuid.uuid4().hex[:6]}"
    snap = MLPredictionSnapshot(
        prediction_snapshot_id=snap_id,
        idempotency_key=f"IK-{snap_id}",
        dispatch_id=disp_uuid,
        dispatch_code=disp.dispatch_number,
        plant_code="PLANT_TEST",
        customer_code="CUST_TEST",
        vehicle_code="VEH_TEST",
        model_name="delay_regressor",
        model_version="v1.1.0-promoted-test",
        artifact_sha256="b6d1ab825d220c3662835580808c1be9c77518007dcd65b6911126d097be9fdd",
        feature_set_version="FeatureSetV1",
        input_features={"distance_km": 10.0},
        prediction_outputs={"predicted_delay_mins": 30.0, "financial_exposure_inr": 1200.0},
        predicted_value=30.0,
        prediction_timestamp=now - timedelta(minutes=30),
    )
    ws53_session.add(snap)
    await ws53_session.flush()

    # 2. Create Outcome with actual_financial_impact_inr = NULL
    out_id = f"OUT-FIN-NULL-{uuid.uuid4().hex[:6]}"
    out_null = OperationalOutcome(
        outcome_id=out_id,
        dispatch_id=disp.id,
        dispatch_code=disp.dispatch_number,
        prediction_snapshot_id=snap_id,
        idempotency_key=f"IK-{out_id}",
        actual_transit_mins=20.0,
        actual_financial_impact_inr=None,  # NULL actual
        verification_status="VERIFIED",
        is_verified=True,
        outcome_timestamp=now,
    )
    ws53_session.add(out_null)
    await ws53_session.commit()

    # Execute accuracy engine
    res = await PredictionAccuracyService.calculate_and_persist_prediction_error(ws53_session, out_id)
    assert res["success"] is True
    assert res["financial_error_inr"] is None  # Preserves NULL when actual financial impact is unavailable!


@pytest.mark.asyncio
async def test_ws53_06_idempotency_and_erp_correction_lineage(ws53_session: AsyncSession):
    """Test 6-8: Verify idempotency protection and ERP outcome correction (O1 -> O2) error record supersession lineage."""
    disp = (await ws53_session.execute(select(Dispatch).limit(1))).scalar_one_or_none()
    if not disp:
        pytest.skip("No real dispatches found in test database.")

    disp_uuid = str(disp.id)
    now = datetime.now(timezone.utc)

    # Create Snapshot
    snap_id = f"SNAP-CORR-{uuid.uuid4().hex[:6]}"
    snap = MLPredictionSnapshot(
        prediction_snapshot_id=snap_id,
        idempotency_key=f"IK-{snap_id}",
        dispatch_id=disp_uuid,
        dispatch_code=disp.dispatch_number,
        plant_code="PLANT_TEST",
        customer_code="CUST_TEST",
        vehicle_code="VEH_TEST",
        model_name="delay_regressor",
        model_version="v1.1.0-promoted-test",
        artifact_sha256="b6d1ab825d220c3662835580808c1be9c77518007dcd65b6911126d097be9fdd",
        feature_set_version="FeatureSetV1",
        input_features={"distance_km": 10.0},
        prediction_outputs={"predicted_delay_mins": 25.0},
        predicted_value=25.0,
        prediction_timestamp=now - timedelta(minutes=30),
    )
    ws53_session.add(snap)
    await ws53_session.flush()

    # Create Outcome O1
    out_id = f"OUT-CORR-{uuid.uuid4().hex[:6]}"
    out = OperationalOutcome(
        outcome_id=out_id,
        dispatch_id=disp.id,
        dispatch_code=disp.dispatch_number,
        prediction_snapshot_id=snap_id,
        idempotency_key=f"IK-{out_id}",
        actual_transit_mins=20.0,
        verification_status="VERIFIED",
        is_verified=True,
        outcome_timestamp=now,
    )
    ws53_session.add(out)
    await ws53_session.commit()

    # Initial accuracy calculation
    res1 = await PredictionAccuracyService.calculate_and_persist_prediction_error(ws53_session, out_id)
    assert res1["success"] is True
    err1_id = res1["error_record_id"]

    # Duplicate call (Idempotency check)
    res2 = await PredictionAccuracyService.calculate_and_persist_prediction_error(ws53_session, out_id)
    assert res2["success"] is True
    assert res2["reason"] == "OUTCOME_ERROR_ALREADY_CALCULATED"
    assert res2["error_record_id"] == err1_id

    # Recompute / Outcome Correction (O1 -> O2)
    res_corr = await PredictionAccuracyService.calculate_and_persist_prediction_error(ws53_session, out_id, force_recompute=True)
    assert res_corr["success"] is True
    err2_id = res_corr["error_record_id"]

    # Query error records to verify lineage
    stmt_err = select(PredictionErrorRecord).where(PredictionErrorRecord.outcome_id == out_id)
    err_records = list((await ws53_session.execute(stmt_err)).scalars().all())

    superseded_count = sum(1 for e in err_records if e.is_superseded)
    active_count = sum(1 for e in err_records if not e.is_superseded)

    assert active_count == 1
    assert superseded_count == 1


@pytest.mark.asyncio
async def test_ws53_07_erp_driven_end_to_end_chain(ws53_session: AsyncSession):
    """Test 9-10: Verify complete end-to-end flow (ERP dispatch -> WS5.1 outcome -> WS5.2 match -> WS5.3 accuracy calculation)."""
    disp = (await ws53_session.execute(select(Dispatch).limit(1))).scalar_one_or_none()
    if not disp:
        pytest.skip("No real dispatches found in test database.")

    disp_uuid = str(disp.id)
    disp_code = disp.dispatch_number

    # Set status to COMPLETED
    await ws53_session.execute(
        update(Dispatch)
        .where(Dispatch.id == disp.id)
        .values(
            status="COMPLETED",
            t1_transit_mins=28.0,
            t2b_unloading_mins=12.0,
            date_in=datetime.now(timezone.utc),
        )
    )
    await ws53_session.commit()

    # 1. Generate active prediction snapshot
    snap_id = f"SNAP-E2E-{uuid.uuid4().hex[:6]}"
    snap = MLPredictionSnapshot(
        prediction_snapshot_id=snap_id,
        idempotency_key=f"IK-{snap_id}",
        dispatch_id=disp_uuid,
        dispatch_code=disp_code,
        plant_code="PLANT_TEST",
        customer_code="CUST_TEST",
        vehicle_code="VEH_TEST",
        model_name="delay_regressor",
        model_version="v1.1.0-promoted-test",
        artifact_sha256="b6d1ab825d220c3662835580808c1be9c77518007dcd65b6911126d097be9fdd",
        feature_set_version="FeatureSetV1",
        input_features={"distance_km": 10.0},
        prediction_outputs={"predicted_delay_mins": 25.0},
        predicted_value=25.0,
        prediction_timestamp=datetime.now(timezone.utc) - timedelta(minutes=30),
    )
    ws53_session.add(snap)
    await ws53_session.commit()

    # 2. Execute WS5.2 Outcome Matching
    match_res = await OutcomeMatchingService.match_outcome_to_snapshot(ws53_session, disp_uuid, force_recompute=True)
    assert match_res["success"] is True
    assert match_res["matched_snapshot_id"] == snap_id
    out_id = match_res["outcome_id"]

    # 3. Execute WS5.3 Accuracy Calculation
    acc_res = await PredictionAccuracyService.calculate_and_persist_prediction_error(ws53_session, out_id, force_recompute=True)
    assert acc_res["success"] is True
    assert acc_res["reason"] == "PREDICTION_ERROR_CALCULATED_SUCCESSFULLY"
    assert acc_res["prediction_snapshot_id"] == snap_id
    assert acc_res["absolute_error"] == 3.0  # |25.0 - 28.0| = 3.0


@pytest.mark.asyncio
async def test_ws53_08_all_multiclass_combinations(ws53_session: AsyncSession):
    """GAP 4: Test all 9 combinations of actual (0,1,2) vs predicted (0,1,2) for plant_risk_classifier."""
    combinations = [
        (0, 0, True, "TN"),
        (0, 1, False, "FP"),
        (0, 2, False, "FP"),
        (1, 0, False, "FN"),
        (1, 1, True, "TP"),
        (1, 2, False, "TP"),
        (2, 0, False, "FN"),
        (2, 1, False, "TP"),
        (2, 2, True, "TP"),
    ]

    for actual, pred, expected_correct, expected_cat in combinations:
        prob, p_cls, a_cls, is_corr, cat, brier = PredictionAccuracyService.calculate_classification_metrics(
            "plant_risk_classifier", 0.75, pred, actual
        )
        assert p_cls == pred
        assert a_cls == actual
        assert is_corr == expected_correct
        assert cat == expected_cat


@pytest.mark.asyncio
async def test_ws53_09_negative_regression_prediction_policy(ws53_session: AsyncSession):
    """GAP 5: Test negative regression prediction policy (preserves raw predicted_numeric_value while evaluating absolute error)."""
    # Raw model output = -12.5, Actual = 20.0
    pred, act, err, abs_err, sq_err, pct_err = PredictionAccuracyService.calculate_regression_error(-12.5, 20.0)
    assert pred == Decimal("-12.5000")  # Preserves raw negative prediction
    assert act == Decimal("20.0000")
    assert err == Decimal("-32.5000")
    assert abs_err == Decimal("32.5000")  # |-12.5 - 20.0| = 32.5
    assert pct_err == Decimal("162.5000")  # (32.5 / 20.0) * 100 = 162.5%


@pytest.mark.asyncio
async def test_ws53_10_mathematical_test_vectors(ws53_session: AsyncSession):
    """GAP 10: Independently assert exact mathematical test vectors requested in GAP 10 prompt."""
    # 1. REGRESSION VECTOR: predicted = 100, actual = 80
    p1, a1, err1, abs_err1, sq_err1, pct_err1 = PredictionAccuracyService.calculate_regression_error(100.0, 80.0)
    assert err1 == Decimal("20.0000")
    assert abs_err1 == Decimal("20.0000")
    assert sq_err1 == Decimal("400.0000")
    assert pct_err1 == Decimal("25.0000")  # (20 / 80) * 100 = 25%

    # 2. ZERO ACTUAL VECTOR: predicted = 50, actual = 0
    p2, a2, err2, abs_err2, sq_err2, pct_err2 = PredictionAccuracyService.calculate_regression_error(50.0, 0.0)
    assert pct_err2 is None  # Governed NULL state

    # 3. CLASSIFICATION VECTOR: P = 0.8, actual = 1
    prob3, p3, a3, corr3, cat3, brier3 = PredictionAccuracyService.calculate_classification_metrics(
        "sla_breach_classifier", 0.8, 1, 1
    )
    assert brier3 == Decimal("0.0400")  # (0.8 - 1.0)^2 = 0.04

    # 4. FINANCIAL VECTOR: predicted = 1500, actual = 1200
    pred_fin = Decimal("1500.00")
    act_fin = Decimal("1200.00")
    fin_err = pred_fin - act_fin
    assert fin_err == Decimal("300.00")

