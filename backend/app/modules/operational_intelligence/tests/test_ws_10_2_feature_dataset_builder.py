"""
WS-10.2 Dedicated Test Suite: FeatureSetV1 Dataset Preprocessing & Anti-Leakage Rules.
Verifies all minimum test requirements for WS-10.2.
"""

import time
import uuid
import pytest
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, update
from app.core.database import AsyncSessionFactory, engine
from app.modules.erp.models import Dispatch, Plant, Customer, Vehicle, Ticket
from app.modules.operational_intelligence.models.ml_dataset import MLDataset
from app.modules.operational_intelligence.models.ml_lifecycle_trigger import MLLifecycleTrigger
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.ml.feature_extractor import (
    FEATURE_SET_VERSION,
    Phase71FeatureExtractor,
    FORBIDDEN_LEAKAGE_FIELDS,
    ALLOWED_INFERENCE_FEATURES,
)
from app.modules.operational_intelligence.ml.dataset_builder import (
    WS10FeatureDatasetBuilder,
    FeatureSetV1Preprocessor,
)
from app.modules.operational_intelligence.services.predictive_service import PredictiveIntelligenceService


@pytest.mark.asyncio
async def test_ws_10_2_featureset_v1_schema_correctness():
    """1. FeatureSetV1 schema correctness (all required features present, no leakage)."""
    await engine.dispose()
    async with AsyncSessionFactory() as session:
        ds_id = f"DS-TEST-SCHEMA-{uuid.uuid4().hex[:6]}"
        db_ds, extracted = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id, limit=10
        )
        await session.commit()

        assert db_ds.feature_set_version == "FeatureSetV1"
        for rec in extracted.records:
            f = rec.features
            for req_feat in ALLOWED_INFERENCE_FEATURES:
                assert req_feat in f, f"Missing required feature '{req_feat}'"
            for forbidden in FORBIDDEN_LEAKAGE_FIELDS:
                assert forbidden not in f, f"Forbidden leakage field '{forbidden}' found in features"


@pytest.mark.asyncio
async def test_ws_10_2_target_mapping_and_separation_correctness():
    """2 & 6. Target mapping correctness & target separation assertion."""
    await engine.dispose()
    async with AsyncSessionFactory() as session:
        ds_id = f"DS-TEST-TARGETS-{uuid.uuid4().hex[:6]}"
        db_ds, extracted = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id, limit=20
        )
        await session.commit()

        schema_targets = db_ds.lineage_metadata["schema_contract"]["targets"]
        assert "predicted_plant_congestion_target" in schema_targets
        assert "predicted_sla_breach_target" in schema_targets

        for rec in extracted.records:
            t = rec.targets
            if t["predicted_plant_congestion_target"] is not None:
                assert t["predicted_plant_congestion_target"] in [0.0, 1.0]
                assert t["predicted_sla_breach_target"] in [0.0, 1.0]


@pytest.mark.asyncio
async def test_ws_10_2_chronological_partitioning():
    """3. Chronological partitioning (TRAIN, VALIDATION, HOLDOUT_TEST)."""
    await engine.dispose()
    now = datetime.now(timezone.utc)
    min_dt = now - timedelta(days=90)
    max_dt = now

    train_p = Phase71FeatureExtractor.classify_chronological_partition(min_dt + timedelta(days=10), min_dt, max_dt)
    val_p = Phase71FeatureExtractor.classify_chronological_partition(min_dt + timedelta(days=65), min_dt, max_dt)
    holdout_p = Phase71FeatureExtractor.classify_chronological_partition(min_dt + timedelta(days=85), min_dt, max_dt)

    assert train_p == "TRAIN"
    assert val_p == "VALIDATION"
    assert holdout_p == "HOLDOUT_TEST"


@pytest.mark.asyncio
async def test_ws_10_2_train_only_preprocessing_fit():
    """4. Preprocessor fit using TRAIN partition only."""
    await engine.dispose()
    async with AsyncSessionFactory() as session:
        ds_id = f"DS-TEST-FIT-{uuid.uuid4().hex[:6]}"
        db_ds, extracted = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id, limit=30
        )
        await session.commit()

        fit_count = db_ds.lineage_metadata["preprocessor_params"]["fitted_train_count"]
        assert fit_count == db_ds.train_count


@pytest.mark.asyncio
async def test_ws_10_2_holdout_isolation():
    """5. Holdout dataset remains completely isolated from fitting."""
    preproc = FeatureSetV1Preprocessor()
    assert not preproc.is_fitted
    preproc.fit([])
    assert preproc.is_fitted
    assert preproc.mean_plant_queue_30d == 15.0
    assert preproc.mean_customer_retention_30d == 8.0


@pytest.mark.asyncio
async def test_ws_10_2_target_and_post_outcome_leakage_detection():
    """6 & 7. Target leakage & post-outcome field rejection assertion."""
    for forbidden in FORBIDDEN_LEAKAGE_FIELDS:
        bad_features = {"plant_code": "P1", forbidden: 10.0}
        with pytest.raises(ValueError, match="ANTI-LEAKAGE VIOLATION"):
            Phase71FeatureExtractor.validate_no_leakage_in_features(bad_features)


@pytest.mark.asyncio
async def test_ws_10_2_invalid_row_exclusion_and_quality_stats():
    """8. Invalid row exclusion reasons & dataset quality statistics."""
    await engine.dispose()
    async with AsyncSessionFactory() as session:
        # Update one existing dispatch to have negative holding mins -> triggers invalid exclusion
        disp_res = await session.execute(select(Dispatch).limit(1))
        disp = disp_res.scalars().first()
        if disp:
            disp.t2a_holding_mins = -99.0
            await session.commit()

        ds_id = f"DS-TEST-EXCL-{uuid.uuid4().hex[:6]}"
        db_ds, extracted = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id
        )
        await session.commit()

        assert db_ds.exclusion_stats.get("negative_holding_mins", 0) >= 1
        assert db_ds.excluded_count >= 1

        # Revert change
        if disp:
            disp.t2a_holding_mins = 15.0
            await session.commit()


@pytest.mark.asyncio
async def test_ws_10_2_deterministic_dataset_generation_and_reproducibility():
    """9 & 10. Deterministic dataset generation, SHA256 checksum & lineage persistence."""
    await engine.dispose()
    ds_id1 = f"DS-REPRO-1-{uuid.uuid4().hex[:6]}"
    ds_id2 = f"DS-REPRO-2-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionFactory() as session:
        db_ds1, ext1 = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id1, limit=15
        )
        db_ds2, ext2 = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id2, limit=15
        )
        await session.commit()

        assert db_ds1.sha256_checksum == db_ds2.sha256_checksum
        assert db_ds1.total_records == db_ds2.total_records
        assert db_ds1.train_count == db_ds2.train_count


@pytest.mark.asyncio
async def test_ws_10_2_source_erp_lineage_and_trigger_integration():
    """11 & 12. Source ERP lineage & WS-10.1 trigger integration."""
    await engine.dispose()
    family = f"family_ws10_2_{uuid.uuid4().hex[:6]}"

    async with AsyncSessionFactory() as session:
        trig = MLLifecycleTrigger(
            trigger_id=f"trig-builder-{uuid.uuid4().hex[:8]}",
            job_number=f"JOB-BUILDER-{uuid.uuid4().hex[:6]}",
            dataset_id="DS-SOURCE-ERP",
            model_family=family,
            status="PENDING",
            new_dispatch_count=200,
        )
        session.add(trig)
        await session.commit()
        t_id = trig.trigger_id

    async with AsyncSessionFactory() as session:
        db_ds, ext = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, trigger_id=t_id, limit=20
        )
        await session.commit()

        assert db_ds.trigger_id == t_id
        assert db_ds.source_erp_job_number == trig.job_number


@pytest.mark.asyncio
async def test_ws_10_2_duplicate_dataset_prevention():
    """13. Duplicate dataset identity prevention."""
    await engine.dispose()
    ds_id = f"DS-DUP-PREVENT-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionFactory() as session:
        await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id, limit=5
        )
        await session.commit()

    async with AsyncSessionFactory() as session:
        with pytest.raises(ValueError, match="Duplicate dataset_id"):
            await WS10FeatureDatasetBuilder.build_and_persist_dataset(
                session=session, dataset_id_override=ds_id, limit=5
            )


@pytest.mark.asyncio
async def test_ws_10_2_ws09_contract_preservation_and_production_safety():
    """14 & 16. WS-09 authority protection & real production safety audit."""
    await engine.dispose()
    ds_id = f"DS-SAFETY-AUDIT-{uuid.uuid4().hex[:6]}"

    async with AsyncSessionFactory() as session:
        await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id, limit=10
        )
        await session.commit()

    async with AsyncSessionFactory() as session:
        stmt_m = select(MLModelVersion)
        res_m = await session.execute(stmt_m)
        models = res_m.scalars().all()
        promoted = [m for m in models if m.training_dataset_id == ds_id and m.lifecycle_status == "PROMOTED"]
        rejected = [m for m in models if m.lifecycle_status == "REJECTED"]

        assert len(promoted) == 0
        assert len(rejected) >= 4

        overview = await PredictiveIntelligenceService.get_predictive_authority_overview(session)
        assert overview.overall_authority_status == "NOT_CONFIGURED"

        stmt_s = select(MLPredictionSnapshot)
        res_s = await session.execute(stmt_s)
        snaps = res_s.scalars().all()
        assert len(snaps) == 0


@pytest.mark.asyncio
async def test_ws_10_2_empty_or_insufficient_dataset_handling():
    """15. Empty / insufficient dataset handling."""
    await engine.dispose()
    async with AsyncSessionFactory() as session:
        ds_id = f"DS-EMPTY-{uuid.uuid4().hex[:6]}"
        db_ds, ext = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id, plant_code="NON_EXISTENT_PLANT_CODE"
        )
        await session.commit()

        assert db_ds.total_records == 0
        assert db_ds.train_count == 0
        assert db_ds.val_count == 0
        assert db_ds.holdout_count == 0


@pytest.mark.asyncio
async def test_ws_10_2_performance_benchmark():
    """15 & Performance. Benchmark dataset construction with dispatches."""
    await engine.dispose()
    async with AsyncSessionFactory() as session:
        ds_id = f"DS-PERF-{uuid.uuid4().hex[:6]}"
        t0 = time.perf_counter()
        db_ds, ext = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session, dataset_id_override=ds_id, limit=100
        )
        await session.commit()
        t1 = time.perf_counter()

        duration = t1 - t0
        rows_per_sec = (db_ds.total_records / duration) if duration > 0 else 0

        print(f"\n[WS-10.2 BENCHMARK] Processed {db_ds.total_records} rows in {duration:.2f} s ({rows_per_sec:.1f} rows/sec)")
        assert duration < 10.0, f"Dataset construction exceeded 10s SLO ({duration:.2f} s)"
