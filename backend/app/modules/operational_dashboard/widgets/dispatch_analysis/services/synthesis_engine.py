"""
WS-ROUT-3: 2D Synthesis Recommendation Engine & Deterministic Explanation Generator
Authoritative implementation compliant with Route Analysis Decision Support Engine v1.2.1 (FROZEN).
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.logging import get_logger
from app.modules.operational_dashboard.widgets.dispatch_analysis.dtos import (
    RouteAnalysisMode,
    HistoricalConfidenceLevel,
    HistoricalWinnerOutcome,
    HistoricalTransitEvidenceSummaryDTO,
    GoogleRouteEvidenceSummaryDTO,
    GoogleCandidateMatrixItemDTO,
    GoogleDetailedRouteDTO,
    SynthesisDecisionOutcome,
    SynthesisCaseCategory,
    SynthesisCandidateComparisonDTO,
    RouteAnalysisSynthesisResultDTO,
)
from app.modules.operational_dashboard.widgets.dispatch_analysis.services.google_routes_client import (
    GoogleRoutesProvider,
    IRouteProvider,
)

logger = get_logger("app.synthesis_engine")


class DeterministicExplanationGenerator:
    """
    Template-based deterministic explanation generator.
    Strict contract: Zero LLM / Zero generative hallucinations.
    Every number and assertion originates directly from authoritative evidence DTOs.
    """

    @classmethod
    def generate_explanation(
        cls,
        case_category: SynthesisCaseCategory,
        curr_plant_code: str,
        alt_plant_code: str,
        delta_route_min: Optional[float],
        delta_hist_min: Optional[float],
        curr_traffic_delay_min: Optional[float],
        alt_traffic_delay_min: Optional[float],
        curr_p50_min: Optional[float],
        alt_p50_min: Optional[float],
        curr_sample_count: int,
        alt_sample_count: int,
        theta_switch: float = 10.0,
        mode: RouteAnalysisMode = RouteAnalysisMode.NOW,
        failure_reason: Optional[str] = None,
    ) -> str:
        temporal_str = "current traffic" if mode == RouteAnalysisMode.NOW else "planned departure traffic"

        if case_category == SynthesisCaseCategory.C1_BOTH_AGREE_CURRENT:
            diff_str = f"{abs(delta_route_min):.1f}" if delta_route_min is not None else "0.0"
            hist_str = f"{abs(delta_hist_min):.1f}" if delta_hist_min is not None else "comparable"
            return (
                f"Plant {curr_plant_code} is currently recommended: faster in {temporal_str} by {diff_str} mins "
                f"and historically faster/comparable by {hist_str} mins ({curr_sample_count} historical trips)."
            )

        if case_category == SynthesisCaseCategory.C2_BOTH_AGREE_ALTERNATIVE:
            saved_str = f"{delta_route_min:.1f}" if delta_route_min is not None else f"{theta_switch:.1f}"
            hist_str = f"{delta_hist_min:.1f}" if delta_hist_min is not None else "comparable"
            return (
                f"Plant {alt_plant_code} is currently recommended: current route saves {saved_str} mins "
                f"(>= {theta_switch:.0f}m policy threshold) and historical median transit is faster/comparable by {hist_str} mins ({alt_sample_count} trips)."
            )

        if case_category == SynthesisCaseCategory.C3_TRAFFIC_OVERRIDE_ALTERNATIVE:
            saved_str = f"{delta_route_min:.1f}" if delta_route_min is not None else f"{theta_switch:.1f}"
            delay_str = f"+{curr_traffic_delay_min:.1f}" if curr_traffic_delay_min is not None else "+0.0"
            hist_p50_str = f"{curr_p50_min:.1f}" if curr_p50_min is not None else "N/A"
            return (
                f"Plant {alt_plant_code} is currently recommended due to severe congestion on Plant {curr_plant_code} route "
                f"({delay_str} mins traffic delay), saving {saved_str} mins overall, despite Plant {curr_plant_code} having a faster historical baseline ({hist_p50_str} mins median)."
            )

        if case_category == SynthesisCaseCategory.C4_TRAFFIC_OVERRIDE_CURRENT:
            diff_str = f"{abs(delta_route_min):.1f}" if delta_route_min is not None else "0.0"
            hist_str = f"{abs(delta_hist_min):.1f}" if delta_hist_min is not None else "0.0"
            return (
                f"Plant {curr_plant_code} is currently recommended: currently faster by {diff_str} mins due to traffic on Plant {alt_plant_code} corridor, "
                f"despite Plant {alt_plant_code} historically averaging {hist_str} mins faster."
            )

        if case_category == SynthesisCaseCategory.C5_NOMINAL_DIFFERENCE_BELOW_SWITCH:
            diff_str = f"{delta_route_min:.1f}" if delta_route_min is not None else "0.0"
            return (
                f"No operational plant change recommended: Plant {alt_plant_code} is nominally faster by only {diff_str} mins, "
                f"which is below the {theta_switch:.0f} min operational switching threshold. Retain Plant {curr_plant_code}."
            )

        if case_category == SynthesisCaseCategory.C6_IDENTICAL_ROUTE_ESTIMATE:
            return f"Plant {curr_plant_code} and Plant {alt_plant_code} have identical route travel estimates. Retain current plant."

        if case_category == SynthesisCaseCategory.C7_HISTORICAL_ONLY_GOOGLE_STALE_FAILED:
            p_curr_p50 = f"{curr_p50_min:.1f}" if curr_p50_min is not None else "N/A"
            p_alt_p50 = f"{alt_p50_min:.1f}" if alt_p50_min is not None else "N/A"
            return (
                f"Live route conditions unavailable (or expired). Historical operational transit: Plant {curr_plant_code} p50 = {p_curr_p50}m ({curr_sample_count} trips) "
                f"vs Plant {alt_plant_code} p50 = {p_alt_p50}m ({alt_sample_count} trips). No live route recommendation can be made."
            )

        if case_category == SynthesisCaseCategory.C8_LIVE_ROUTE_ONLY_HIST_INSUFFICIENT:
            saved_str = f"{abs(delta_route_min):.1f}" if delta_route_min is not None else "0.0"
            rec_code = curr_plant_code if (delta_route_min is not None and delta_route_min < 0) else alt_plant_code
            return (
                f"Plant {rec_code} recommended based strictly on Google route estimates (faster by {saved_str} mins). "
                f"Historical operational data is insufficient (< 5 completed trips)."
            )


        if case_category == SynthesisCaseCategory.C9_NO_EVIDENCE_AVAILABLE:
            return "Route analysis unavailable: Google route query failed/expired and historical ERP trip data is insufficient for this destination site."

        if case_category == SynthesisCaseCategory.C10_CANDIDATE_ROUTE_FAILED:
            reason = failure_reason or "Route not found or unroutable"
            return f"Route calculation failed for Plant {alt_plant_code} ({reason}). Comparison limited to available candidates."

        if case_category == SynthesisCaseCategory.C11_COORDINATES_MISSING:
            return "Location data missing: Authoritative GPS coordinates missing for plant or destination site in master entity tables."

        return "Route analysis completed. Retain current source plant."


class RouteAnalysisSynthesisEngine:
    """
    Authoritative 2D Synthesis Recommendation Engine.
    Combines:
    - WS-ROUT-1: Historical ERP operational T1 transit evidence
    - WS-ROUT-2: Google Routes API v2 traffic/route evidence
    """

    ENGINE_VERSION: str = "v1.2.1"
    POLICY_VERSION: str = "ROUTE_POLICY_v1.2.1"
    THETA_SWITCH_MINUTES: float = 10.0
    THETA_HIST_MINUTES: float = 2.0
    MIN_HISTORICAL_SAMPLE_COUNT: int = 5

    @classmethod
    def synthesize_pair(
        cls,
        curr_plant_id: str,
        curr_plant_code: str,
        curr_plant_name: str,
        cand_plant_id: str,
        cand_plant_code: str,
        cand_plant_name: str,
        site_id: str,
        site_code: str,
        site_name: str,
        hist_curr_metric: Optional[Any],
        hist_cand_metric: Optional[Any],
        hist_comparison: Optional[Any],
        google_curr_item: Optional[GoogleCandidateMatrixItemDTO],
        google_cand_item: Optional[GoogleCandidateMatrixItemDTO],
        is_google_fresh: bool,
        is_google_stale: bool,
        mode: RouteAnalysisMode = RouteAnalysisMode.NOW,
    ) -> SynthesisCandidateComparisonDTO:
        """
        Evaluates a single Candidate Plant vs Current Source Plant pair across the 2D decision matrix.
        """
        # 1. Extract Historical Metrics
        curr_p50 = hist_curr_metric.p50_minutes if hist_curr_metric else None
        cand_p50 = hist_cand_metric.p50_minutes if hist_cand_metric else None
        curr_n = hist_curr_metric.sample_count if hist_curr_metric else 0
        cand_n = hist_cand_metric.sample_count if hist_cand_metric else 0
        curr_conf = hist_curr_metric.confidence_level if hist_curr_metric else HistoricalConfidenceLevel.NONE
        cand_conf = hist_cand_metric.confidence_level if hist_cand_metric else HistoricalConfidenceLevel.NONE

        delta_hist: Optional[float] = None
        if curr_p50 is not None and cand_p50 is not None:
            delta_hist = round(curr_p50 - cand_p50, 2)

        hist_winner = hist_comparison.historical_winner_status if hist_comparison else HistoricalWinnerOutcome.INSUFFICIENT_EVIDENCE
        is_hist_sufficient = (curr_n >= cls.MIN_HISTORICAL_SAMPLE_COUNT and cand_n >= cls.MIN_HISTORICAL_SAMPLE_COUNT)

        # 2. Extract Google Metrics
        g_curr_dur = google_curr_item.duration_minutes if google_curr_item else None
        g_cand_dur = google_cand_item.duration_minutes if google_cand_item else None
        g_curr_stat = google_curr_item.static_duration_minutes if google_curr_item else None
        g_cand_stat = google_cand_item.static_duration_minutes if google_cand_item else None
        g_curr_delay = google_curr_item.traffic_delay_minutes if google_curr_item else None
        g_cand_delay = google_cand_item.traffic_delay_minutes if google_cand_item else None
        g_curr_dist = google_curr_item.distance_km if google_curr_item else None
        g_cand_dist = google_cand_item.distance_km if google_cand_item else None
        g_status = google_cand_item.status if google_cand_item else "ERROR"

        delta_route: Optional[float] = None
        if g_curr_dur is not None and g_cand_dur is not None:
            delta_route = round(g_curr_dur - g_cand_dur, 2)

        # 3. Decision Matrix Synthesis
        case_cat: SynthesisCaseCategory
        outcome: SynthesisDecisionOutcome
        rec_pid: Optional[str] = None
        rec_pcode: Optional[str] = None
        mins_saved: Optional[float] = None

        # Check candidate route availability
        if google_cand_item is None or google_cand_item.status not in ("OK", "0", ""):
            case_cat = SynthesisCaseCategory.C10_CANDIDATE_ROUTE_FAILED
            outcome = SynthesisDecisionOutcome.CANDIDATE_ROUTE_UNAVAILABLE
            rec_pid = curr_plant_id
            rec_pcode = curr_plant_code

        # STALE CACHE / GOOGLE FAILED INVARIANT
        elif not is_google_fresh or is_google_stale or google_curr_item is None:
            if is_hist_sufficient:
                case_cat = SynthesisCaseCategory.C7_HISTORICAL_ONLY_GOOGLE_STALE_FAILED
                outcome = SynthesisDecisionOutcome.HISTORICAL_COMPARISON_ONLY
                # Informational winner if applicable
                if hist_winner == HistoricalWinnerOutcome.CANDIDATE_PLANT_FASTER:
                    rec_pid = cand_plant_id
                    rec_pcode = cand_plant_code
                else:
                    rec_pid = curr_plant_id
                    rec_pcode = curr_plant_code
            else:
                case_cat = SynthesisCaseCategory.C9_NO_EVIDENCE_AVAILABLE
                outcome = SynthesisDecisionOutcome.NO_RECOMMENDATION
                rec_pid = None
                rec_pcode = None

        # FRESH GOOGLE ROUTE CONDITIONS
        else:
            assert delta_route is not None

            # Case C6: Identical estimates
            if delta_route == 0.0:
                case_cat = SynthesisCaseCategory.C6_IDENTICAL_ROUTE_ESTIMATE
                outcome = SynthesisDecisionOutcome.NO_CLEAR_DIFFERENCE
                rec_pid = curr_plant_id
                rec_pcode = curr_plant_code
                mins_saved = 0.0

            # Current plant is faster in live traffic (delta_route < 0)
            elif delta_route < 0.0:
                mins_saved = abs(delta_route)
                if not is_hist_sufficient:
                    case_cat = SynthesisCaseCategory.C8_LIVE_ROUTE_ONLY_HIST_INSUFFICIENT
                    outcome = SynthesisDecisionOutcome.LIVE_ROUTE_ONLY
                    rec_pid = curr_plant_id
                    rec_pcode = curr_plant_code
                elif hist_winner in (HistoricalWinnerOutcome.CURRENT_PLANT_FASTER, HistoricalWinnerOutcome.NO_MEANINGFUL_HISTORICAL_DIFFERENCE):
                    case_cat = SynthesisCaseCategory.C1_BOTH_AGREE_CURRENT
                    outcome = SynthesisDecisionOutcome.RECOMMEND_CURRENT_SOURCE
                    rec_pid = curr_plant_id
                    rec_pcode = curr_plant_code
                else:
                    # hist_winner == CANDIDATE_PLANT_FASTER (Traffic Override favoring Current)
                    case_cat = SynthesisCaseCategory.C4_TRAFFIC_OVERRIDE_CURRENT
                    outcome = SynthesisDecisionOutcome.RECOMMEND_CURRENT_SOURCE
                    rec_pid = curr_plant_id
                    rec_pcode = curr_plant_code

            # Alternative plant is faster in live traffic (delta_route > 0)
            else:
                # Sub-case: delta_route < theta_switch (nominal difference)
                if delta_route < cls.THETA_SWITCH_MINUTES:
                    case_cat = SynthesisCaseCategory.C5_NOMINAL_DIFFERENCE_BELOW_SWITCH
                    outcome = SynthesisDecisionOutcome.NO_CLEAR_DIFFERENCE
                    rec_pid = curr_plant_id
                    rec_pcode = curr_plant_code
                    mins_saved = delta_route

                # Sub-case: delta_route >= theta_switch (significant savings >= 10m)
                else:
                    mins_saved = delta_route
                    if not is_hist_sufficient:
                        case_cat = SynthesisCaseCategory.C8_LIVE_ROUTE_ONLY_HIST_INSUFFICIENT
                        outcome = SynthesisDecisionOutcome.LIVE_ROUTE_ONLY
                        rec_pid = cand_plant_id
                        rec_pcode = cand_plant_code
                    elif hist_winner in (HistoricalWinnerOutcome.CANDIDATE_PLANT_FASTER, HistoricalWinnerOutcome.NO_MEANINGFUL_HISTORICAL_DIFFERENCE):
                        case_cat = SynthesisCaseCategory.C2_BOTH_AGREE_ALTERNATIVE
                        outcome = SynthesisDecisionOutcome.RECOMMEND_ALTERNATIVE
                        rec_pid = cand_plant_id
                        rec_pcode = cand_plant_code
                    else:
                        # hist_winner == CURRENT_PLANT_FASTER (Traffic Override favoring Alternative)
                        case_cat = SynthesisCaseCategory.C3_TRAFFIC_OVERRIDE_ALTERNATIVE
                        outcome = SynthesisDecisionOutcome.RECOMMEND_ALTERNATIVE
                        rec_pid = cand_plant_id
                        rec_pcode = cand_plant_code

        # 4. Generate Deterministic Explanation
        explanation = DeterministicExplanationGenerator.generate_explanation(
            case_category=case_cat,
            curr_plant_code=curr_plant_code,
            alt_plant_code=cand_plant_code,
            delta_route_min=delta_route,
            delta_hist_min=delta_hist,
            curr_traffic_delay_min=g_curr_delay,
            alt_traffic_delay_min=g_cand_delay,
            curr_p50_min=curr_p50,
            alt_p50_min=cand_p50,
            curr_sample_count=curr_n,
            alt_sample_count=cand_n,
            theta_switch=cls.THETA_SWITCH_MINUTES,
            mode=mode,
            failure_reason=google_cand_item.error_message if google_cand_item else None,
        )

        return SynthesisCandidateComparisonDTO(
            candidate_plant_id=cand_plant_id,
            candidate_plant_code=cand_plant_code,
            candidate_plant_name=cand_plant_name,
            current_plant_id=curr_plant_id,
            current_plant_code=curr_plant_code,
            current_plant_name=curr_plant_name,
            site_id=site_id,
            site_code=site_code,
            site_name=site_name,
            google_current_duration_minutes=g_curr_dur,
            google_candidate_duration_minutes=g_cand_dur,
            delta_route_minutes=delta_route,
            google_current_static_minutes=g_curr_stat,
            google_candidate_static_minutes=g_cand_stat,
            google_current_traffic_delay_minutes=g_curr_delay,
            google_candidate_traffic_delay_minutes=g_cand_delay,
            google_current_distance_km=g_curr_dist,
            google_candidate_distance_km=g_cand_dist,
            google_status=g_status,
            historical_current_p50_minutes=curr_p50,
            historical_candidate_p50_minutes=cand_p50,
            delta_hist_minutes=delta_hist,
            historical_current_sample_count=curr_n,
            historical_candidate_sample_count=cand_n,
            historical_current_confidence=curr_conf,
            historical_candidate_confidence=cand_conf,
            historical_winner_status=hist_winner,
            case_category=case_cat,
            outcome=outcome,
            recommended_plant_id=rec_pid,
            recommended_plant_code=rec_pcode,
            minutes_saved=mins_saved,
            explanation=explanation,
        )

    @classmethod
    def synthesize_multi_candidate_decision(
        cls,
        analysis_id: str,
        site_id: str,
        site_code: str,
        site_name: str,
        current_plant_id: str,
        current_plant_code: str,
        current_plant_name: str,
        candidate_plants: List[Dict[str, Any]],
        historical_summary: Optional[HistoricalTransitEvidenceSummaryDTO],
        google_summary: Optional[GoogleRouteEvidenceSummaryDTO],
        detailed_route: Optional[GoogleDetailedRouteDTO],
        mode: RouteAnalysisMode = RouteAnalysisMode.NOW,
        requested_departure_time: Optional[datetime] = None,
        analysis_timestamp: Optional[datetime] = None,
    ) -> RouteAnalysisSynthesisResultDTO:
        """
        Orchestrates multi-candidate synthesis across all candidate corridors.
        """
        now_dt = analysis_timestamp or datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        dept_time_str = requested_departure_time.isoformat() if requested_departure_time else None

        is_google_fresh = google_summary.is_fresh if google_summary else False
        is_google_stale = google_summary.is_stale_cache if google_summary else False
        cache_age = google_summary.cache_age_seconds if google_summary else 0.0

        hist_metrics = historical_summary.plant_metrics if historical_summary else {}
        hist_comparisons = {
            c.candidate_plant_id: c for c in (historical_summary.comparisons if historical_summary else [])
        }
        hist_curr_metric = hist_metrics.get(str(current_plant_id))

        g_matrix = google_summary.matrix_items if google_summary else {}
        g_curr_item = g_matrix.get(str(current_plant_id))

        comparisons: List[SynthesisCandidateComparisonDTO] = []

        # Iterate over all candidate alternative plants
        for cand in candidate_plants:
            cand_id = str(cand["plant_id"])
            if cand_id == str(current_plant_id):
                continue

            cand_code = str(cand.get("plant_code") or cand_id)
            cand_name = str(cand.get("plant_name") or cand_code)

            hist_cand_metric = hist_metrics.get(cand_id)
            hist_comp = hist_comparisons.get(cand_id)
            g_cand_item = g_matrix.get(cand_id)

            pair_comp = cls.synthesize_pair(
                curr_plant_id=str(current_plant_id),
                curr_plant_code=current_plant_code,
                curr_plant_name=current_plant_name,
                cand_plant_id=cand_id,
                cand_plant_code=cand_code,
                cand_plant_name=cand_name,
                site_id=str(site_id),
                site_code=site_code,
                site_name=site_name,
                hist_curr_metric=hist_curr_metric,
                hist_cand_metric=hist_cand_metric,
                hist_comparison=hist_comp,
                google_curr_item=g_curr_item,
                google_cand_item=g_cand_item,
                is_google_fresh=is_google_fresh,
                is_google_stale=is_google_stale,
                mode=mode,
            )
            comparisons.append(pair_comp)

        # Determine Global Winning Outcome across all comparisons
        overall_outcome = SynthesisDecisionOutcome.RECOMMEND_CURRENT_SOURCE
        overall_case = SynthesisCaseCategory.C1_BOTH_AGREE_CURRENT
        overall_rec_id = str(current_plant_id)
        overall_rec_code = current_plant_code
        overall_rec_name = current_plant_name
        overall_mins_saved: Optional[float] = None
        is_override = False
        summary_text = ""

        # If no candidates provided
        if not comparisons:
            if not is_google_fresh or is_google_stale:
                overall_outcome = SynthesisDecisionOutcome.HISTORICAL_COMPARISON_ONLY if historical_summary and historical_summary.is_overall_sufficient else SynthesisDecisionOutcome.NO_RECOMMENDATION
                overall_case = SynthesisCaseCategory.C7_HISTORICAL_ONLY_GOOGLE_STALE_FAILED if overall_outcome == SynthesisDecisionOutcome.HISTORICAL_COMPARISON_ONLY else SynthesisCaseCategory.C9_NO_EVIDENCE_AVAILABLE
                overall_rec_id = None
                overall_rec_code = None
                overall_rec_name = None
            summary_text = "Single plant scope evaluated. Retain current plant."
        else:
            # Look for highest saving recommended alternative
            best_alt: Optional[SynthesisCandidateComparisonDTO] = None
            max_savings = -1.0

            for comp in comparisons:
                if comp.outcome == SynthesisDecisionOutcome.RECOMMEND_ALTERNATIVE or (
                    comp.outcome == SynthesisDecisionOutcome.LIVE_ROUTE_ONLY and comp.recommended_plant_id == comp.candidate_plant_id
                ):
                    savings = comp.minutes_saved or 0.0
                    if savings > max_savings:
                        max_savings = savings
                        best_alt = comp

            if best_alt:
                overall_outcome = best_alt.outcome
                overall_case = best_alt.case_category
                overall_rec_id = best_alt.candidate_plant_id
                overall_rec_code = best_alt.candidate_plant_code
                overall_rec_name = best_alt.candidate_plant_name
                overall_mins_saved = best_alt.minutes_saved
                is_override = (best_alt.case_category == SynthesisCaseCategory.C3_TRAFFIC_OVERRIDE_ALTERNATIVE)
                summary_text = best_alt.explanation
            else:
                # If no alternative qualifies for switch, pick the primary comparison result
                first_comp = comparisons[0]
                overall_outcome = first_comp.outcome
                overall_case = first_comp.case_category
                overall_rec_id = first_comp.recommended_plant_id
                overall_rec_code = first_comp.recommended_plant_code
                overall_rec_name = current_plant_name if overall_rec_id == str(current_plant_id) else None
                overall_mins_saved = first_comp.minutes_saved
                is_override = (first_comp.case_category == SynthesisCaseCategory.C4_TRAFFIC_OVERRIDE_CURRENT)
                summary_text = first_comp.explanation

        return RouteAnalysisSynthesisResultDTO(
            analysis_id=analysis_id,
            site_id=str(site_id),
            site_code=site_code,
            site_name=site_name,
            current_source_plant_id=str(current_plant_id),
            current_source_plant_code=current_plant_code,
            current_source_plant_name=current_plant_name,
            recommended_plant_id=overall_rec_id,
            recommended_plant_code=overall_rec_code,
            recommended_plant_name=overall_rec_name,
            recommendation_status=overall_outcome,
            primary_case_category=overall_case,
            is_traffic_override=is_override,
            decision_reason_summary=summary_text,
            minutes_saved=overall_mins_saved,
            engine_version=cls.ENGINE_VERSION,
            policy_version=cls.POLICY_VERSION,
            analysis_mode=mode,
            requested_departure_time=dept_time_str,
            analysis_timestamp=now_iso,
            theta_switch_minutes=cls.THETA_SWITCH_MINUTES,
            theta_hist_minutes=cls.THETA_HIST_MINUTES,
            min_historical_sample_count=cls.MIN_HISTORICAL_SAMPLE_COUNT,
            is_google_fresh=is_google_fresh,
            is_google_stale_cache=is_google_stale,
            google_cache_age_seconds=cache_age,
            is_historical_sufficient=historical_summary.is_overall_sufficient if historical_summary else False,
            comparisons=comparisons,
            historical_evidence=historical_summary,
            google_evidence=google_summary,
            detailed_route=detailed_route,
            failure_reason_code=google_summary.failure_reason if google_summary else None,
        )
