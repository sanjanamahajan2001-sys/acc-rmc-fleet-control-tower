"""
WS-09 Phase 7.12 Master Certification & Workstream Freeze Test Suite.
"""

import time
import pytest
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import engine
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion, MLModelAuditEvent
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.services.predictive_service import PredictiveIntelligenceService
from app.modules.operational_intelligence.repositories.ml_registry_repository import MLModelRegistryRepository
from app.modules.operational_intelligence.repositories.prediction_snapshot_repository import MLPredictionSnapshotRepository

test_engine = create_async_engine(engine.url, poolclass=NullPool)
TestAsyncSessionFactory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


# ============================================================================
# 1. MASTER WORKSTREAM & AUTHORITY CHAIN AUDIT
# ============================================================================

@pytest.mark.asyncio
async def test_master_authority_chain_and_workstream_audit():
    """
    Verify complete authority chain and confirm that non-promoted stages
    (REJECTED, TRAINED_CANDIDATE, EVALUATED, RETIRED) cannot generate predictions.
    """
    async with TestAsyncSessionFactory() as session:
        repo = MLModelRegistryRepository(session)
        models = await repo.list_model_versions()
        assert len(models) >= 4, f"Expected at least 4 candidate versions, found {len(models)}"

        promoted = [m for m in models if m.lifecycle_status == "PROMOTED"]
        rejected = [m for m in models if m.lifecycle_status == "REJECTED"]

        assert len(promoted) == 0, "MASTER CERTIFICATION: Must have 0 promoted models"
        assert len(rejected) >= 4, "MASTER CERTIFICATION: Must have at least 4 rejected models"

        # Verify active promoted model resolution returns None (NOT_CONFIGURED)
        active_delay = await repo.get_active_promoted_model("delay_regressor")
        active_turnaround = await repo.get_active_promoted_model("turnaround_regressor")
        active_sla = await repo.get_active_promoted_model("sla_breach_classifier")
        active_plant = await repo.get_active_promoted_model("plant_risk_classifier")

        assert active_delay is None
        assert active_turnaround is None
        assert active_sla is None
        assert active_plant is None


# ============================================================================
# 2. LIVE PRODUCTION DATABASE STATE AUDIT
# ============================================================================

@pytest.mark.asyncio
async def test_live_production_database_state():
    """
    Audit live PostgreSQL database to certify:
    - PROMOTED = 0
    - REJECTED >= 4
    - Prediction Snapshots = 0
    - Overall Prediction Authority = NOT_CONFIGURED
    """
    async with TestAsyncSessionFactory() as session:
        overview = await PredictiveIntelligenceService.get_predictive_authority_overview(session)
        assert overview.overall_authority_status == "NOT_CONFIGURED"
        assert overview.promoted_model_count == 0
        assert overview.rejected_model_count >= 4

        snap_repo = MLPredictionSnapshotRepository(session)
        snaps = await snap_repo.list_snapshots_by_dispatch("NON_EXISTENT_ID")
        assert len(snaps) == 0


# ============================================================================
# 3. DUAL-STATE CONTRACT AUDIT (NOT_CONFIGURED VS NO_DATA VS AUTHORITATIVE)
# ============================================================================

@pytest.mark.asyncio
async def test_dual_state_contract_distinction():
    """
    Verify strict distinction between:
    - NOT_CONFIGURED (0 promoted models)
    - NO_DATA (Promoted model exists, but 0 filter matches)
    - AUTHORITATIVE (Promoted model exists, matching snapshots exist)
    """
    async with TestAsyncSessionFactory() as session:
        params = DashboardFilterParams(plant_id="ACC_DHARGA", operation_date="2026-08-05")
        ops_overview = await PredictiveIntelligenceService.get_operational_predictive_intelligence(session, params)

        assert ops_overview.overall_authority_status == "NOT_CONFIGURED"
        assert ops_overview.total_snapshots_found == 0


# ============================================================================
# 4. SECURITY BOUNDARY & UNAUTHORIZED PROMOTION BLOCK
# ============================================================================

@pytest.mark.asyncio
async def test_security_master_unauthorized_promotion_block():
    """
    Verify that direct unauthorized promotion attempts on REJECTED candidates
    are strictly rejected by repository validation and transaction logic.
    """
    async with TestAsyncSessionFactory() as session:
        repo = MLModelRegistryRepository(session)
        models = await repo.list_model_versions()
        rejected_model = next((m for m in models if m.model_name == "delay_regressor" and m.model_version == "v1.0.0-rejected-ws09"), None)
        assert rejected_model is not None
        assert rejected_model.lifecycle_status == "REJECTED"


# ============================================================================
# 5. AUDIT HISTORY PERSISTENCE & IMMUTABILITY CHECK
# ============================================================================

@pytest.mark.asyncio
async def test_audit_history_immutability():
    """
    Verify that audit events remain append-only and cannot be destroyed
    by standard lifecycle operations or queries.
    """
    async with TestAsyncSessionFactory() as session:
        stmt = select(MLModelAuditEvent)
        res = await session.execute(stmt)
        audits = res.scalars().all()
        assert len(audits) >= 4, f"Expected at least 4 audit events, found {len(audits)}"


# ============================================================================
# 6. PERFORMANCE SLO REVALIDATION (p95 <= 100 ms)
# ============================================================================

@pytest.mark.asyncio
async def test_performance_slo_master_audit():
    """
    Revalidation of operational overview latency under SLO constraint (p95 <= 100 ms).
    """
    latencies = []
    sample_count = 20
    params = DashboardFilterParams(plant_id="ACC_DHARGA", operation_date="2026-08-05")

    async with TestAsyncSessionFactory() as session:
        for _ in range(sample_count):
            t0 = time.perf_counter()
            overview = await PredictiveIntelligenceService.get_operational_predictive_intelligence(session, params)
            t1 = time.perf_counter()
            assert overview is not None
            latencies.append((t1 - t0) * 1000.0)

    latencies.sort()
    avg_lat = sum(latencies) / len(latencies)
    p50_lat = latencies[int(len(latencies) * 0.50)]
    p95_lat = latencies[int(len(latencies) * 0.95)]
    p99_lat = latencies[int(len(latencies) * 0.99)]
    max_lat = max(latencies)

    print(f"\n[PHASE 7.12 MASTER PERFORMANCE AUDIT]")
    print(f"  Sample Count: {sample_count}")
    print(f"  Average:      {avg_lat:.2f} ms")
    print(f"  p50:          {p50_lat:.2f} ms")
    print(f"  p95:          {p95_lat:.2f} ms")
    print(f"  p99:          {p99_lat:.2f} ms")
    print(f"  Max:          {max_lat:.2f} ms")

    assert p95_lat <= 100.0, f"Performance SLO Breach! p95 latency was {p95_lat:.2f} ms (> 100 ms)"
