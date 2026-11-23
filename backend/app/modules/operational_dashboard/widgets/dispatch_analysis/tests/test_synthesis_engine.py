"""
WS-ROUT-3: 2D Synthesis Recommendation Engine Test Suite
FROZEN BLUEPRINT v1.2.1 COMPLIANT
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta

from app.modules.operational_dashboard.widgets.dispatch_analysis.dtos import (
    RouteAnalysisMode,
    HistoricalConfidenceLevel,
    HistoricalWinnerOutcome,
    PlantSiteHistoricalMetricDTO,
    HistoricalComparisonPairDTO,
    HistoricalTransitEvidenceSummaryDTO,
    GoogleCandidateMatrixItemDTO,
    GoogleDetailedRouteDTO,
    GoogleRouteEvidenceSummaryDTO,
    SynthesisDecisionOutcome,
    SynthesisCaseCategory,
    SynthesisCandidateComparisonDTO,
    RouteAnalysisSynthesisResultDTO,
)
from app.modules.operational_dashboard.widgets.dispatch_analysis.services.synthesis_engine import (
    RouteAnalysisSynthesisEngine,
    DeterministicExplanationGenerator,
)


def make_sample_hist_metric(plant_id="p1", plant_code="PLANT_A", p50=25.0, count=20, iqr=8.0):
    return PlantSiteHistoricalMetricDTO(
        plant_id=plant_id,
        plant_code=plant_code,
        plant_name=f"Name {plant_code}",
        site_id="s1",
        site_code="SITE_X",
        site_name="Site X Name",
        sample_count=count,
        p25_minutes=p50 - (iqr / 2.0),
        p50_minutes=p50,
        p75_minutes=p50 + (iqr / 2.0),
        iqr_minutes=iqr,
        confidence_level=HistoricalConfidenceLevel.HIGH if (count >= 15 and iqr <= 20.0) else (
            HistoricalConfidenceLevel.MODERATE if count >= 5 else (
                HistoricalConfidenceLevel.LOW if count > 0 else HistoricalConfidenceLevel.NONE
            )
        ),
        is_sufficient_sample=(count >= 5),
    )


def make_sample_hist_summary(curr_p50=25.0, alt_p50=35.0, curr_count=20, alt_count=20):
    m_curr = make_sample_hist_metric(plant_id="p_curr", plant_code="PLANT_A", p50=curr_p50, count=curr_count)
    m_alt = make_sample_hist_metric(plant_id="p_alt", plant_code="PLANT_B", p50=alt_p50, count=alt_count)
    delta = curr_p50 - alt_p50
    if abs(delta) < 2.0:
        winner = HistoricalWinnerOutcome.NO_MEANINGFUL_HISTORICAL_DIFFERENCE
        winner_id, winner_code = None, None
    elif delta < 0:
        winner = HistoricalWinnerOutcome.CURRENT_PLANT_FASTER
        winner_id, winner_code = "p_curr", "PLANT_A"
    else:
        winner = HistoricalWinnerOutcome.CANDIDATE_PLANT_FASTER
        winner_id, winner_code = "p_alt", "PLANT_B"

    if curr_count < 5 or alt_count < 5:
        winner = HistoricalWinnerOutcome.INSUFFICIENT_EVIDENCE
        winner_id, winner_code = None, None

    comp = HistoricalComparisonPairDTO(
        current_plant_id="p_curr",
        current_plant_code="PLANT_A",
        candidate_plant_id="p_alt",
        candidate_plant_code="PLANT_B",
        site_id="s1",
        site_code="SITE_X",
        current_p50_minutes=curr_p50,
        candidate_p50_minutes=alt_p50,
        delta_hist_minutes=delta,
        historical_winner_status=winner,
        winner_plant_id=winner_id,
        winner_plant_code=winner_code,
        tie_threshold_minutes=2.0,
        explanation="Historical explanation",
    )

    return HistoricalTransitEvidenceSummaryDTO(
        site_id="s1",
        site_code="SITE_X",
        site_name="Site X Name",
        current_source_plant_id="p_curr",
        current_source_plant_code="PLANT_A",
        analysis_timestamp="2026-09-08T12:00:00+00:00",
        historical_window_days=90,
        window_start_date="2026-06-10T12:00:00+00:00",
        window_end_date="2026-09-08T12:00:00+00:00",
        plant_metrics={"p_curr": m_curr, "p_alt": m_alt},
        comparisons=[comp],
        overall_historical_winner=winner,
        overall_winner_plant_id=winner_id,
        overall_winner_plant_code=winner_code,
        is_overall_sufficient=(curr_count >= 5 and alt_count >= 5),
    )


def make_sample_google_summary(
    curr_dur=30.0,
    alt_dur=45.0,
    is_fresh=True,
    is_stale=False,
    cache_age=10.0,
    curr_delay=2.0,
    alt_delay=3.0,
    alt_status="OK",
    mode=RouteAnalysisMode.NOW,
):
    item_curr = GoogleCandidateMatrixItemDTO(
        plant_id="p_curr",
        plant_code="PLANT_A",
        site_id="s1",
        site_code="SITE_X",
        origin_index=0,
        destination_index=0,
        status="OK",
        duration_minutes=curr_dur,
        duration_seconds=int(curr_dur * 60),
        static_duration_minutes=curr_dur - curr_delay,
        static_duration_seconds=int((curr_dur - curr_delay) * 60),
        traffic_delay_minutes=curr_delay,
        distance_km=20.0,
    )
    item_alt = GoogleCandidateMatrixItemDTO(
        plant_id="p_alt",
        plant_code="PLANT_B",
        site_id="s1",
        site_code="SITE_X",
        origin_index=1,
        destination_index=0,
        status=alt_status,
        duration_minutes=alt_dur if alt_status == "OK" else None,
        duration_seconds=int(alt_dur * 60) if alt_status == "OK" else None,
        static_duration_minutes=alt_dur - alt_delay if alt_status == "OK" else None,
        static_duration_seconds=int((alt_dur - alt_delay) * 60) if alt_status == "OK" else None,
        traffic_delay_minutes=alt_delay if alt_status == "OK" else None,
        distance_km=25.0 if alt_status == "OK" else None,
    )

    return GoogleRouteEvidenceSummaryDTO(
        provider_name="GOOGLE_ROUTES_V2",
        status="SUCCESS" if is_fresh and not is_stale else ("STALE_FALLBACK" if is_stale else "PROVIDER_FAILURE"),
        mode=mode,
        response_timestamp="2026-09-08T12:00:00+00:00",
        is_fresh=is_fresh,
        is_stale_cache=is_stale,
        cache_age_seconds=cache_age,
        matrix_items={"p_curr": item_curr, "p_alt": item_alt},
    )


# =============================================================================
# TESTS FOR ALL 10 FROZEN SYNTHESIS STATES & EDGE CASES
# =============================================================================


def test_syn_c1_both_agree_curr():
    """Case C1: Historical prefers Current, Google prefers Current -> RECOMMEND_CURRENT_SOURCE."""
    hist = make_sample_hist_summary(curr_p50=20.0, alt_p50=30.0)
    google = make_sample_google_summary(curr_dur=25.0, alt_dur=38.0)

    candidates = [{"plant_id": "p_alt", "plant_code": "PLANT_B", "plant_name": "Plant B"}]
    res = RouteAnalysisSynthesisEngine.synthesize_multi_candidate_decision(
        analysis_id=str(uuid.uuid4()),
        site_id="s1",
        site_code="SITE_X",
        site_name="Site X",
        current_plant_id="p_curr",
        current_plant_code="PLANT_A",
        current_plant_name="Plant A",
        candidate_plants=candidates,
        historical_summary=hist,
        google_summary=google,
        detailed_route=None,
    )

    assert res.recommendation_status == SynthesisDecisionOutcome.RECOMMEND_CURRENT_SOURCE
    assert res.primary_case_category == SynthesisCaseCategory.C1_BOTH_AGREE_CURRENT
    assert res.recommended_plant_id == "p_curr"
    assert res.is_traffic_override is False
    assert "Plant PLANT_A is currently recommended" in res.decision_reason_summary


def test_syn_c2_both_agree_alt():
    """Case C2: Historical prefers Alt, Google prefers Alt by >= 10m -> RECOMMEND_ALTERNATIVE."""
    hist = make_sample_hist_summary(curr_p50=35.0, alt_p50=20.0)
    google = make_sample_google_summary(curr_dur=45.0, alt_dur=25.0)  # delta = +20m >= 10m

    candidates = [{"plant_id": "p_alt", "plant_code": "PLANT_B", "plant_name": "Plant B"}]
    res = RouteAnalysisSynthesisEngine.synthesize_multi_candidate_decision(
        analysis_id=str(uuid.uuid4()),
        site_id="s1",
        site_code="SITE_X",
        site_name="Site X",
        current_plant_id="p_curr",
        current_plant_code="PLANT_A",
        current_plant_name="Plant A",
        candidate_plants=candidates,
        historical_summary=hist,
        google_summary=google,
        detailed_route=None,
    )

    assert res.recommendation_status == SynthesisDecisionOutcome.RECOMMEND_ALTERNATIVE
    assert res.primary_case_category == SynthesisCaseCategory.C2_BOTH_AGREE_ALTERNATIVE
    assert res.recommended_plant_id == "p_alt"
    assert res.minutes_saved == 20.0
    assert res.is_traffic_override is False


def test_syn_c3_traffic_override_alt():
    """Case C3: Historical prefers Current, but Google Alt saves >= 10m -> RECOMMEND_ALTERNATIVE (Traffic Override)."""
    hist = make_sample_hist_summary(curr_p50=20.0, alt_p50=30.0)  # Hist favors Curr
    google = make_sample_google_summary(curr_dur=55.0, alt_dur=30.0, curr_delay=25.0)  # Google Alt saves 25m >= 10m

    candidates = [{"plant_id": "p_alt", "plant_code": "PLANT_B", "plant_name": "Plant B"}]
    res = RouteAnalysisSynthesisEngine.synthesize_multi_candidate_decision(
        analysis_id=str(uuid.uuid4()),
        site_id="s1",
        site_code="SITE_X",
        site_name="Site X",
        current_plant_id="p_curr",
        current_plant_code="PLANT_A",
        current_plant_name="Plant A",
        candidate_plants=candidates,
        historical_summary=hist,
        google_summary=google,
        detailed_route=None,
    )

    assert res.recommendation_status == SynthesisDecisionOutcome.RECOMMEND_ALTERNATIVE
    assert res.primary_case_category == SynthesisCaseCategory.C3_TRAFFIC_OVERRIDE_ALTERNATIVE
    assert res.recommended_plant_id == "p_alt"
    assert res.is_traffic_override is True
    assert "severe congestion on Plant PLANT_A route" in res.decision_reason_summary


def test_syn_c4_traffic_override_curr():
    """Case C4: Historical prefers Alt, but Google Current is faster -> RECOMMEND_CURRENT_SOURCE (Traffic Override)."""
    hist = make_sample_hist_summary(curr_p50=35.0, alt_p50=22.0)  # Hist favors Alt
    google = make_sample_google_summary(curr_dur=25.0, alt_dur=40.0)  # Google Curr is faster (delta = -15m)

    candidates = [{"plant_id": "p_alt", "plant_code": "PLANT_B", "plant_name": "Plant B"}]
    res = RouteAnalysisSynthesisEngine.synthesize_multi_candidate_decision(
        analysis_id=str(uuid.uuid4()),
        site_id="s1",
        site_code="SITE_X",
        site_name="Site X",
        current_plant_id="p_curr",
        current_plant_code="PLANT_A",
        current_plant_name="Plant A",
        candidate_plants=candidates,
        historical_summary=hist,
        google_summary=google,
        detailed_route=None,
    )

    assert res.recommendation_status == SynthesisDecisionOutcome.RECOMMEND_CURRENT_SOURCE
    assert res.primary_case_category == SynthesisCaseCategory.C4_TRAFFIC_OVERRIDE_CURRENT
    assert res.recommended_plant_id == "p_curr"
    assert res.is_traffic_override is True


def test_syn_c5_nominal_difference_below_switch():
    """Case C5: Google Alt is faster by < 10m (e.g. 6 mins) -> NO_CLEAR_DIFFERENCE."""
    hist = make_sample_hist_summary(curr_p50=25.0, alt_p50=25.0)
    google = make_sample_google_summary(curr_dur=30.0, alt_dur=24.0)  # delta = +6.0m < 10.0m

    candidates = [{"plant_id": "p_alt", "plant_code": "PLANT_B", "plant_name": "Plant B"}]
    res = RouteAnalysisSynthesisEngine.synthesize_multi_candidate_decision(
        analysis_id=str(uuid.uuid4()),
        site_id="s1",
        site_code="SITE_X",
        site_name="Site X",
        current_plant_id="p_curr",
        current_plant_code="PLANT_A",
        current_plant_name="Plant A",
        candidate_plants=candidates,
        historical_summary=hist,
        google_summary=google,
        detailed_route=None,
    )

    assert res.recommendation_status == SynthesisDecisionOutcome.NO_CLEAR_DIFFERENCE
    assert res.primary_case_category == SynthesisCaseCategory.C5_NOMINAL_DIFFERENCE_BELOW_SWITCH
    assert res.recommended_plant_id == "p_curr"
    assert "below the 10 min operational switching threshold" in res.decision_reason_summary


def test_syn_c6_identical_route_estimate():
    """Case C6: Google durations are identical (delta_route == 0) -> NO_CLEAR_DIFFERENCE."""
    hist = make_sample_hist_summary(curr_p50=25.0, alt_p50=25.0)
    google = make_sample_google_summary(curr_dur=30.0, alt_dur=30.0)  # delta = 0.0

    candidates = [{"plant_id": "p_alt", "plant_code": "PLANT_B", "plant_name": "Plant B"}]
    res = RouteAnalysisSynthesisEngine.synthesize_multi_candidate_decision(
        analysis_id=str(uuid.uuid4()),
        site_id="s1",
        site_code="SITE_X",
        site_name="Site X",
        current_plant_id="p_curr",
        current_plant_code="PLANT_A",
        current_plant_name="Plant A",
        candidate_plants=candidates,
        historical_summary=hist,
        google_summary=google,
        detailed_route=None,
    )

    assert res.recommendation_status == SynthesisDecisionOutcome.NO_CLEAR_DIFFERENCE
    assert res.primary_case_category == SynthesisCaseCategory.C6_IDENTICAL_ROUTE_ESTIMATE
    assert "identical route travel estimates" in res.decision_reason_summary


def test_syn_c7_historical_only_google_stale_or_failed():
    """
    Case C7 / STALE-CACHE INVARIANT:
    When Google is stale (>300s) or failed, MUST return HISTORICAL_COMPARISON_ONLY.
    MUST NEVER return RECOMMEND_ALTERNATIVE or RECOMMEND_CURRENT_SOURCE.
    """
    hist = make_sample_hist_summary(curr_p50=25.0, alt_p50=35.0, curr_count=20, alt_count=20)
    # Stale cache: age = 400s
    google_stale = make_sample_google_summary(curr_dur=60.0, alt_dur=20.0, is_fresh=False, is_stale=True, cache_age=400.0)

    candidates = [{"plant_id": "p_alt", "plant_code": "PLANT_B", "plant_name": "Plant B"}]
    res = RouteAnalysisSynthesisEngine.synthesize_multi_candidate_decision(
        analysis_id=str(uuid.uuid4()),
        site_id="s1",
        site_code="SITE_X",
        site_name="Site X",
        current_plant_id="p_curr",
        current_plant_code="PLANT_A",
        current_plant_name="Plant A",
        candidate_plants=candidates,
        historical_summary=hist,
        google_summary=google_stale,
        detailed_route=None,
    )

    assert res.recommendation_status == SynthesisDecisionOutcome.HISTORICAL_COMPARISON_ONLY
    assert res.primary_case_category == SynthesisCaseCategory.C7_HISTORICAL_ONLY_GOOGLE_STALE_FAILED
    assert res.is_google_fresh is False
    assert res.is_google_stale_cache is True
    assert "Live route conditions unavailable (or expired)" in res.decision_reason_summary


def test_syn_c8_live_route_only_hist_insufficient():
    """Case C8: Historical N < 5, but Google Alt saves >= 10m -> LIVE_ROUTE_ONLY."""
    hist = make_sample_hist_summary(curr_p50=25.0, alt_p50=35.0, curr_count=2, alt_count=2)  # N < 5
    google = make_sample_google_summary(curr_dur=50.0, alt_dur=25.0)  # saves 25m

    candidates = [{"plant_id": "p_alt", "plant_code": "PLANT_B", "plant_name": "Plant B"}]
    res = RouteAnalysisSynthesisEngine.synthesize_multi_candidate_decision(
        analysis_id=str(uuid.uuid4()),
        site_id="s1",
        site_code="SITE_X",
        site_name="Site X",
        current_plant_id="p_curr",
        current_plant_code="PLANT_A",
        current_plant_name="Plant A",
        candidate_plants=candidates,
        historical_summary=hist,
        google_summary=google,
        detailed_route=None,
    )

    assert res.recommendation_status == SynthesisDecisionOutcome.LIVE_ROUTE_ONLY
    assert res.primary_case_category == SynthesisCaseCategory.C8_LIVE_ROUTE_ONLY_HIST_INSUFFICIENT
    assert res.recommended_plant_id == "p_alt"
    assert "Historical operational data is insufficient" in res.decision_reason_summary


def test_syn_c9_no_evidence_available():
    """Case C9: Both Google is unavailable/stale and Historical N < 5 -> NO_RECOMMENDATION."""
    hist = make_sample_hist_summary(curr_p50=25.0, alt_p50=35.0, curr_count=1, alt_count=1)
    google_failed = make_sample_google_summary(is_fresh=False, is_stale=False)

    candidates = [{"plant_id": "p_alt", "plant_code": "PLANT_B", "plant_name": "Plant B"}]
    res = RouteAnalysisSynthesisEngine.synthesize_multi_candidate_decision(
        analysis_id=str(uuid.uuid4()),
        site_id="s1",
        site_code="SITE_X",
        site_name="Site X",
        current_plant_id="p_curr",
        current_plant_code="PLANT_A",
        current_plant_name="Plant A",
        candidate_plants=candidates,
        historical_summary=hist,
        google_summary=google_failed,
        detailed_route=None,
    )

    assert res.recommendation_status == SynthesisDecisionOutcome.NO_RECOMMENDATION
    assert res.primary_case_category == SynthesisCaseCategory.C9_NO_EVIDENCE_AVAILABLE
    assert res.recommended_plant_id is None
    assert "Route analysis unavailable" in res.decision_reason_summary


def test_syn_c10_candidate_route_failed():
    """Case C10: Google route calculation failed for candidate plant -> CANDIDATE_ROUTE_UNAVAILABLE."""
    hist = make_sample_hist_summary()
    google_cand_failed = make_sample_google_summary(alt_status="NOT_FOUND")

    candidates = [{"plant_id": "p_alt", "plant_code": "PLANT_B", "plant_name": "Plant B"}]
    res = RouteAnalysisSynthesisEngine.synthesize_multi_candidate_decision(
        analysis_id=str(uuid.uuid4()),
        site_id="s1",
        site_code="SITE_X",
        site_name="Site X",
        current_plant_id="p_curr",
        current_plant_code="PLANT_A",
        current_plant_name="Plant A",
        candidate_plants=candidates,
        historical_summary=hist,
        google_summary=google_cand_failed,
        detailed_route=None,
    )

    assert res.recommendation_status == SynthesisDecisionOutcome.CANDIDATE_ROUTE_UNAVAILABLE
    assert res.primary_case_category == SynthesisCaseCategory.C10_CANDIDATE_ROUTE_FAILED
    assert "Route calculation failed for Plant PLANT_B" in res.decision_reason_summary


def test_historical_tie_within_2m():
    """Verifies historical difference < 2.0m is classified as NO_MEANINGFUL_HISTORICAL_DIFFERENCE."""
    hist = make_sample_hist_summary(curr_p50=25.0, alt_p50=26.2)  # delta = -1.2m < 2.0m
    assert hist.comparisons[0].historical_winner_status == HistoricalWinnerOutcome.NO_MEANINGFUL_HISTORICAL_DIFFERENCE


def test_exact_10m_switch_boundary():
    """Verifies boundary: delta_route == 10.0m triggers RECOMMEND_ALTERNATIVE, 9.99m does not."""
    hist = make_sample_hist_summary(curr_p50=25.0, alt_p50=25.0)
    
    # 1. Exact 10.0m savings -> RECOMMEND_ALTERNATIVE
    google_10 = make_sample_google_summary(curr_dur=40.0, alt_dur=30.0)
    res_10 = RouteAnalysisSynthesisEngine.synthesize_multi_candidate_decision(
        analysis_id=str(uuid.uuid4()),
        site_id="s1", site_code="SITE_X", site_name="Site X",
        current_plant_id="p_curr", current_plant_code="PLANT_A", current_plant_name="Plant A",
        candidate_plants=[{"plant_id": "p_alt", "plant_code": "PLANT_B", "plant_name": "Plant B"}],
        historical_summary=hist, google_summary=google_10, detailed_route=None,
    )
    assert res_10.recommendation_status == SynthesisDecisionOutcome.RECOMMEND_ALTERNATIVE

    # 2. 9.9m savings -> NO_CLEAR_DIFFERENCE
    google_9_9 = make_sample_google_summary(curr_dur=39.9, alt_dur=30.0)
    res_9_9 = RouteAnalysisSynthesisEngine.synthesize_multi_candidate_decision(
        analysis_id=str(uuid.uuid4()),
        site_id="s1", site_code="SITE_X", site_name="Site X",
        current_plant_id="p_curr", current_plant_code="PLANT_A", current_plant_name="Plant A",
        candidate_plants=[{"plant_id": "p_alt", "plant_code": "PLANT_B", "plant_name": "Plant B"}],
        historical_summary=hist, google_summary=google_9_9, detailed_route=None,
    )
    assert res_9_9.recommendation_status == SynthesisDecisionOutcome.NO_CLEAR_DIFFERENCE


def test_governance_and_version_propagation():
    """Verifies engine version and policy version are propagated into synthesis results."""
    hist = make_sample_hist_summary()
    google = make_sample_google_summary()

    res = RouteAnalysisSynthesisEngine.synthesize_multi_candidate_decision(
        analysis_id="analysis-12345",
        site_id="s1",
        site_code="SITE_X",
        site_name="Site X",
        current_plant_id="p_curr",
        current_plant_code="PLANT_A",
        current_plant_name="Plant A",
        candidate_plants=[{"plant_id": "p_alt", "plant_code": "PLANT_B", "plant_name": "Plant B"}],
        historical_summary=hist,
        google_summary=google,
        detailed_route=None,
    )

    assert res.engine_version == "v1.2.1"
    assert res.policy_version == "ROUTE_POLICY_v1.2.1"
    assert res.theta_switch_minutes == 10.0
    assert res.theta_hist_minutes == 2.0
    assert res.analysis_id == "analysis-12345"


def test_planned_departure_mode_explanation_language():
    """Verifies PLANNED_DEPARTURE mode explanation uses planned traffic wording."""
    hist = make_sample_hist_summary(curr_p50=20.0, alt_p50=30.0)
    google = make_sample_google_summary(curr_dur=25.0, alt_dur=40.0, mode=RouteAnalysisMode.PLANNED_DEPARTURE)

    res = RouteAnalysisSynthesisEngine.synthesize_multi_candidate_decision(
        analysis_id="analysis-planned-1",
        site_id="s1",
        site_code="SITE_X",
        site_name="Site X",
        current_plant_id="p_curr",
        current_plant_code="PLANT_A",
        current_plant_name="Plant A",
        candidate_plants=[{"plant_id": "p_alt", "plant_code": "PLANT_B", "plant_name": "Plant B"}],
        historical_summary=hist,
        google_summary=google,
        detailed_route=None,
        mode=RouteAnalysisMode.PLANNED_DEPARTURE,
        requested_departure_time=datetime(2026, 9, 10, 8, 30, 0, tzinfo=timezone.utc),
    )

    assert res.analysis_mode == RouteAnalysisMode.PLANNED_DEPARTURE
    assert "planned departure traffic" in res.decision_reason_summary
    assert res.requested_departure_time == "2026-09-10T08:30:00+00:00"
