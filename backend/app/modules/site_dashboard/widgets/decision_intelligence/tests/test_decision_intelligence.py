import pytest
from app.core.database import AsyncSessionFactory
from app.modules.site_dashboard.widgets.decision_intelligence.service import DecisionIntelligenceService
from app.modules.site_dashboard.widgets.decision_intelligence.recommendation_engine import RecommendationEngine


@pytest.mark.asyncio
async def test_decision_intelligence_service_execution():
    async with AsyncSessionFactory() as session:
        response = await DecisionIntelligenceService.get_decision_intelligence(session, {"dataset_type": "ALL"})
        
        assert response is not None
        assert response.summary is not None
        assert response.summary.active_recommendations >= 0
        assert isinstance(response.recommendations, list)
        assert isinstance(response.insights, list)


def test_edge_case_zero_dispatches():
    raw_metrics = {
        "total_dispatches": 0,
        "sum_holding": 0.0,
        "sum_retention": 0.0,
        "holding_breaches": 0,
        "retention_breaches": 0,
        "active_vehicles": [],
    }
    summary, recs, insights = RecommendationEngine.generate_recommendations(raw_metrics, {"plant_id": "ACC_VASCO"})
    assert summary.active_recommendations == 0
    assert summary.high_priority_issues == 0
    assert summary.estimated_delay_reduction_mins == 0.0
    assert summary.estimated_sla_recovery_pct == 0.0
    assert summary.fleet_efficiency_opportunity_pct == 0.0
    assert len(recs) == 0
    assert len(insights) == 1
    assert "Optimal" in insights[0].title or "Compliance" in insights[0].category


def test_edge_case_single_dispatch_no_breach():
    raw_metrics = {
        "total_dispatches": 1,
        "sum_holding": 2.0,
        "sum_retention": 0.5,
        "holding_breaches": 0,
        "retention_breaches": 0,
        "active_vehicles": ["GA01T1234"],
    }
    summary, recs, insights = RecommendationEngine.generate_recommendations(raw_metrics, {"plant_id": "ACC_VASCO"})
    assert summary.active_recommendations == 0
    assert summary.high_priority_issues == 0
    assert len(recs) == 0


def test_edge_case_single_dispatch_with_holding_breach():
    raw_metrics = {
        "total_dispatches": 1,
        "sum_holding": 25.0,
        "sum_retention": 5.0,
        "holding_breaches": 1,
        "retention_breaches": 0,
        "active_vehicles": ["GA01T1234"],
    }
    summary, recs, insights = RecommendationEngine.generate_recommendations(raw_metrics, {"plant_id": "ACC_VASCO"})
    assert summary.active_recommendations > 0
    assert summary.high_priority_issues == 1
    assert recs[0].priority == "CRITICAL"
    assert recs[0].confidence_pct <= 99.0


def test_edge_case_large_dataset_bounds():
    raw_metrics = {
        "total_dispatches": 10000,
        "sum_holding": 500000.0,
        "sum_retention": 80000.0,
        "holding_breaches": 4500,
        "retention_breaches": 1200,
        "active_vehicles": ["GA01T1234", "GA02T5678"],
    }
    summary, recs, insights = RecommendationEngine.generate_recommendations(raw_metrics, {"plant_id": "ALL"})
    assert 0.0 <= summary.estimated_sla_recovery_pct <= 100.0
    assert 0.0 <= summary.fleet_efficiency_opportunity_pct <= 100.0
    assert summary.high_priority_issues == 5700
