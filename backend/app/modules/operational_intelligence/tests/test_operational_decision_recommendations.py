"""
WS-09 Phase 3 Production Remediation & Freeze Hardening Test Suite
Tests Actionable Decision Recommendations backend calculations, field authority integrity, filter matrix propagation,
stale context transition, and direct PostgreSQL input reconciliation.
"""

import pytest
from sqlalchemy import select, func, text
from app.core.database import AsyncSessionFactory, engine
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_intelligence.services.decision_recommendation_service import OperationalDecisionRecommendationService
from app.modules.site_dashboard.widgets.decision_intelligence.repository import DecisionIntelligenceRepository
from app.modules.site_dashboard.widgets.decision_intelligence.recommendation_engine import RecommendationEngine
from app.modules.erp.models import Dispatch, Plant, Customer


@pytest.mark.asyncio
async def test_decision_recommendation_service_basic():
    """
    Test OperationalDecisionRecommendationService basic execution under default filters.
    Verifies that the service returns an OperationalDecisionRecommendationResponseDTO.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        params = DashboardFilterParams(
            plant_id="ALL",
            customer_id="ALL",
            dataset_type="ALL",
        )
        result = await OperationalDecisionRecommendationService.get_decision_recommendations(db_session, params)

        assert result is not None
        assert result.summary is not None
        assert result.calculation_status in ["SUCCESS", "NO_RECORDS"]

        if result.calculation_status == "SUCCESS":
            assert result.summary.active_recommendations == len(result.recommendations)
            assert len(result.insights) > 0

            # Verify recommendation ID preservation
            for rec in result.recommendations:
                assert rec.recommendation_id in ["REC-CRIT-01", "REC-HIGH-01", "REC-MED-01", "REC-LOW-01"]
                assert rec.priority in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
                assert rec.confidence_pct >= 80.0 and rec.confidence_pct <= 99.0
                assert rec.status == "Pending"


@pytest.mark.asyncio
async def test_decision_recommendation_filter_matrix_suite():
    """
    Test filter propagation across Plant, Customer, Date, and Dataset parameters.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        # 1. Test Plant Filter ACC_KUNDAIM
        params_kundaim = DashboardFilterParams(plant_id="ACC_KUNDAIM", customer_id="ALL", dataset_type="ALL")
        res_kundaim = await OperationalDecisionRecommendationService.get_decision_recommendations(db_session, params_kundaim)
        assert res_kundaim is not None
        assert "Plant: ACC_KUNDAIM" in res_kundaim.calculation_notes

        # 2. Test Plant Filter ACC_VASCO
        params_vasco = DashboardFilterParams(plant_id="ACC_VASCO", customer_id="ALL", dataset_type="ALL")
        res_vasco = await OperationalDecisionRecommendationService.get_decision_recommendations(db_session, params_vasco)
        assert res_vasco is not None
        assert "Plant: ACC_VASCO" in res_vasco.calculation_notes

        # 3. Test Customer Filter CUST_TRUE_BUILD
        params_cust = DashboardFilterParams(plant_id="ALL", customer_id="CUST_TRUE_BUILD", dataset_type="ALL")
        res_cust = await OperationalDecisionRecommendationService.get_decision_recommendations(db_session, params_cust)
        assert res_cust is not None
        assert "Customer: CUST_TRUE_BUILD" in res_cust.calculation_notes

        # 4. Test Combined Filter (ACC_VASCO + CUST_TRUE_BUILD + REAL_ONLY)
        params_comb = DashboardFilterParams(
            plant_id="ACC_VASCO",
            customer_id="CUST_TRUE_BUILD",
            dataset_type="REAL_ONLY",
            operation_date="2026-08-05",
        )
        res_comb = await OperationalDecisionRecommendationService.get_decision_recommendations(db_session, params_comb)
        assert res_comb is not None
        assert res_comb.calculation_status in ["SUCCESS", "NO_RECORDS"]


@pytest.mark.asyncio
async def test_recommendation_engine_direct_reconciliation():
    """
    MANDATORY RECONCILIATION TEST:
    Verifies that Section 03 API recommendation IDs, counts, and priority ordering match canonical
    RecommendationEngine output 100% identically for identical filter context.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        params = DashboardFilterParams(plant_id="ACC_VASCO", customer_id="ALL", dataset_id="DS-20260805-001")
        dto = await OperationalDecisionRecommendationService.get_decision_recommendations(db_session, params)

        # Direct call to repository & RecommendationEngine
        filters = {"plant_id": "ACC_VASCO", "customer_id": "ALL", "dataset_id": "DS-20260805-001"}
        raw_metrics = await DecisionIntelligenceRepository.get_operational_metrics(db_session, filters)
        eng_sum, eng_recs, eng_ins = RecommendationEngine.generate_recommendations(raw_metrics, filters)

        assert dto.summary.active_recommendations == eng_sum.active_recommendations
        assert dto.summary.high_priority_issues == eng_sum.high_priority_issues
        assert dto.summary.estimated_delay_reduction_mins == eng_sum.estimated_delay_reduction_mins
        assert dto.summary.estimated_sla_recovery_pct == eng_sum.estimated_sla_recovery_pct
        assert dto.summary.fleet_efficiency_opportunity_pct == eng_sum.fleet_efficiency_opportunity_pct

        assert len(dto.recommendations) == len(eng_recs)
        for dto_rec, eng_rec in zip(dto.recommendations, eng_recs):
            assert dto_rec.recommendation_id == eng_rec.recommendation_id
            assert dto_rec.priority == eng_rec.priority
            assert dto_rec.confidence_pct == eng_rec.confidence_pct
            assert dto_rec.expected_impact == eng_rec.expected_impact
            assert dto_rec.status == eng_rec.status


@pytest.mark.asyncio
async def test_direct_postgresql_input_reconciliation():
    """
    DIRECT POSTGRESQL INPUT RECONCILIATION TEST:
    Reconciles raw dispatches SLA holding breaches (> 20.0 mins) and retention breaches (> 10.0 mins)
    against DecisionIntelligenceRepository and high_priority_issues.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        # Direct SQL query on dispatches joining Plant
        q = select(
            func.coalesce(func.count().filter(Dispatch.t2a_holding_mins > 20.0), 0).label("holding_breaches"),
            func.coalesce(func.count().filter(Dispatch.t2c_retention_mins > 10.0), 0).label("retention_breaches"),
        ).join(Plant, Dispatch.plant_id == Plant.id, isouter=True).where(Plant.code == "ACC_VASCO")

        res = (await db_session.execute(q)).fetchone()
        expected_holding = res.holding_breaches if res else 0
        expected_retention = res.retention_breaches if res else 0
        expected_high_priority = expected_holding + expected_retention

        params = DashboardFilterParams(plant_id="ACC_VASCO", customer_id="ALL", dataset_type="ALL")
        dto = await OperationalDecisionRecommendationService.get_decision_recommendations(db_session, params)

        assert dto.summary.high_priority_issues == expected_high_priority


@pytest.mark.asyncio
async def test_stale_filter_transition_integrity():
    """
    STALE FILTER TRANSITION INTEGRITY TEST:
    Verifies that changing context from ACC_VASCO to ACC_KUNDAIM updates calculation notes and lineage.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        res1 = await OperationalDecisionRecommendationService.get_decision_recommendations(
            db_session, DashboardFilterParams(plant_id="ACC_VASCO")
        )
        res2 = await OperationalDecisionRecommendationService.get_decision_recommendations(
            db_session, DashboardFilterParams(plant_id="ACC_KUNDAIM")
        )

        assert "Plant: ACC_VASCO" in res1.calculation_notes
        assert "Plant: ACC_KUNDAIM" in res2.calculation_notes
        assert res1.calculation_notes != res2.calculation_notes
