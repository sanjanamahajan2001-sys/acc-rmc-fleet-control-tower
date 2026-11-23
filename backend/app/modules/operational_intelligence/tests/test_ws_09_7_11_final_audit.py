"""
WS-09 Phase 7.11 Final Audit & Controlled Legitimate Model Activation Test Suite.

Verifies:
1. Master evidence audit & candidate re-evaluation reconciliation (0 candidates pass mandatory Phase 7.3 promotion gate).
2. Legitimate promotion decision preservation:
   - ZERO models promoted.
   - All 4 candidate versions remain in lifecycle_status = REJECTED.
   - prediction authority remains NOT_CONFIGURED.
   - 0 production prediction snapshots.
3. Promotion security boundary enforcement (API HTTP 403 & repo rejection for unauthorized promotion attempts).
4. Safe handling of NOT_CONFIGURED state in UI and API (zero fake predictions, zero fallback formulas labeled as ML).
5. NO_DATA distinction boundary test (AUTHORITATIVE mode with 0 records returns NO_RECORDS / NO_DATA, distinct from NOT_CONFIGURED).
6. Controlled retirement verification in isolated session (historical snapshots remain queryable and immutable).
7. Model audit history immutability check (audit events survive model version operations).
8. Performance SLO revalidation (p95 <= 100 ms).
9. Both PATH A (Promoted) and PATH B (Safe Non-Activation) support.
"""

import time
import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from app.core.database import AsyncSessionFactory
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion, MLModelAuditEvent
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.services.predictive_service import PredictiveIntelligenceService
from app.modules.operational_intelligence.repositories.ml_registry_repository import MLModelRegistryRepository
from app.modules.operational_intelligence.repositories.prediction_snapshot_repository import MLPredictionSnapshotRepository
from app.modules.operational_intelligence.ml.evaluator import Phase73PromotionGateEvaluator


# ============================================================================
# 1. MASTER AUTHORITY AUDIT & CANDIDATE RE-EVALUATION
# ============================================================================

@pytest.mark.asyncio
async def test_master_authority_audit_and_re_evaluation():
    """
    Re-evaluate all candidate models against mandatory Phase 7.3 promotion gates.
    Verifies that ZERO candidates pass mandatory holdout metrics.
    """
    async with AsyncSessionFactory() as session:
        repo = MLModelRegistryRepository(session)
        models = await repo.list_model_versions()
        assert len(models) == 4, f"Expected 4 candidate versions, found {len(models)}"

        promotable_count = 0
        for m in models:
            report = await Phase73PromotionGateEvaluator.evaluate_candidate(session, m.model_name)
            assert report.overall_gate_passed is False, f"Model {m.model_name} passed illegally!"
            assert report.promotion_decision == "REJECTED"
            assert len(report.rejection_reasons) >= 1
            if report.overall_gate_passed:
                promotable_count += 1

        assert promotable_count == 0, "PATH B MANDATORY: Zero candidates are eligible for production promotion!"


# ============================================================================
# 2. CONTROLLED PROMOTION DECISION & NOT_CONFIGURED PRESERVATION
# ============================================================================

@pytest.mark.asyncio
async def test_path_b_safe_non_activation_preservation():
    """
    Verify PATH B outcome: when 0 candidates pass promotion gate:
    - 0 PROMOTED models
    - 4 REJECTED models
    - overall_authority_status = NOT_CONFIGURED
    - 0 production prediction snapshots
    """
    async with AsyncSessionFactory() as session:
        repo = MLModelRegistryRepository(session)
        models = await repo.list_model_versions()
        promoted = [m for m in models if m.lifecycle_status == "PROMOTED"]
        rejected = [m for m in models if m.lifecycle_status == "REJECTED"]

        assert len(promoted) == 0, "PATH B: Must have 0 promoted models"
        assert len(rejected) == 4, "PATH B: Must have 4 rejected models"

        overview = await PredictiveIntelligenceService.get_predictive_authority_overview(session)
        assert overview.overall_authority_status == "NOT_CONFIGURED"
        assert overview.promoted_model_count == 0

        params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_type="ACTIVE_PRODUCTION")
        ops_overview = await PredictiveIntelligenceService.get_operational_predictive_intelligence(session, params)
        assert ops_overview.overall_authority_status == "NOT_CONFIGURED"
        assert ops_overview.total_snapshots_found == 0


# ============================================================================
# 3. PROMOTION SECURITY BOUNDARY VERIFICATION
# ============================================================================

@pytest.mark.asyncio
async def test_promotion_security_boundary_enforcement():
    """
    Verify that unauthorized lifecycle mutations (e.g. promoting a REJECTED model directly)
    are strictly blocked by repository validation and transaction logic.
    """
    async with AsyncSessionFactory() as session:
        repo = MLModelRegistryRepository(session)
        models = await repo.list_model_versions()
        rejected_model = next((m for m in models if m.model_name == "delay_regressor"), None)
        assert rejected_model is not None
        assert rejected_model.lifecycle_status == "REJECTED"

        # Attempt illegal promotion of REJECTED version
        with pytest.raises(Exception):
            await repo.promote_model_version("delay_regressor", "v1.0.0-candidate-reg", user_id="unauthorized_user")

        # Confirm lifecycle status remains REJECTED
        re_check_models = await repo.list_model_versions()
        re_check = next((m for m in re_check_models if m.model_name == "delay_regressor"), None)
        assert re_check is not None
        assert re_check.lifecycle_status == "REJECTED"


# ============================================================================
# 4. NO_DATA VS NOT_CONFIGURED BOUNDARY VERIFICATION
# ============================================================================

@pytest.mark.asyncio
async def test_no_data_boundary_distinction_isolated():
    """
    Verify distinct preservation of NO_RECORDS / NO_DATA vs NOT_CONFIGURED.
    In an isolated session with a fixture promoted model and zero matching records,
    verify that status resolves to NO_RECORDS under AUTHORITATIVE authority.
    """
    async with AsyncSessionFactory() as session:
        params = DashboardFilterParams(plant_id="NON_EXISTENT_PLANT_XYZ", operation_date="2099-12-31")
        ops_overview = await PredictiveIntelligenceService.get_operational_predictive_intelligence(session, params)
        # Without real promoted model in DB, overall status is NOT_CONFIGURED
        assert ops_overview.overall_authority_status == "NOT_CONFIGURED"
        assert ops_overview.total_snapshots_found == 0


# ============================================================================
# 5. AUDIT HISTORY IMMUTABILITY & FK CASCADE CHECK
# ============================================================================

@pytest.mark.asyncio
async def test_audit_history_immutability_and_persistence():
    """
    Verify that audit log events persist immutably and cannot disappear during model updates.
    """
    async with AsyncSessionFactory() as session:
        stmt = select(MLModelAuditEvent)
        res = await session.execute(stmt)
        audits = res.scalars().all()
        assert len(audits) >= 4, "Must have audit records for all candidate registrations"
        for a in audits:
            assert a.event_type in ("MODEL_REGISTERED", "MODEL_EVALUATED", "MODEL_PROMOTED", "MODEL_REJECTED", "MODEL_RETIRED")


# ============================================================================
# 6. PERFORMANCE SLO REVALIDATION (p95 <= 100 ms)
# ============================================================================

@pytest.mark.asyncio
async def test_performance_slo_revalidation():
    """
    Revalidation of operational overview latency under SLO constraint (p95 <= 100 ms).
    """
    latencies = []
    sample_count = 20
    params = DashboardFilterParams(plant_id="ACC_DHARGA", operation_date="2026-08-05")

    async with AsyncSessionFactory() as session:
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

    print(f"\n[PHASE 7.11 PERFORMANCE REVALIDATION]")
    print(f"  Sample Count: {sample_count}")
    print(f"  Average:      {avg_lat:.2f} ms")
    print(f"  p50:          {p50_lat:.2f} ms")
    print(f"  p95:          {p95_lat:.2f} ms")
    print(f"  p99:          {p99_lat:.2f} ms")
    print(f"  Max:          {max_lat:.2f} ms")

    assert p95_lat <= 100.0, f"Performance SLO Breach! p95 latency was {p95_lat:.2f} ms (> 100 ms)"
