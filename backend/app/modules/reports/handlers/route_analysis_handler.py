import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecordNotFoundError
from app.modules.erp.models import Customer, Plant, Site
from app.modules.operational_dashboard.models.route_analysis import RouteAnalysisSnapshot
from app.modules.reports.schemas.report_schemas import ReportStatus
from app.modules.reports.schemas.route_analysis_canonical import (
    CandidateComparisonDTO,
    ReportMetadataDTO,
    RouteAnalysisReportCanonical,
)


class RouteAnalysisReportHandler:
    """
    Handler for building canonical Route Analysis Report representations
    strictly from persisted, immutable RouteAnalysisSnapshot records.

    Snapshot-Complete Invariant:
    The persisted snapshot's evidence, decision code, mathematical percentiles,
    time deltas, and snapshot-time entity attributes are the primary source of truth.
    Any fallback entity lookup occurs ONLY for optional legacy enrichment if missing
    from the snapshot, and is forbidden from mutating snapshot-time decision values.
    """

    @classmethod
    async def build_canonical_report_from_snapshot(
        cls,
        session: AsyncSession,
        snapshot: RouteAnalysisSnapshot,
        execution_id: Optional[str] = None,
        requested_by: str = "SYSTEM",
    ) -> RouteAnalysisReportCanonical:
        matrix = snapshot.candidate_comparison_matrix or []
        hist_payload = snapshot.historical_evidence_payload or {}
        google_payload = snapshot.google_evidence_payload or {}

        # 1. Primary Source: Extract snapshot-time names/codes from comparison matrix & payloads
        snapshot_plant_names: Dict[str, tuple[str, str]] = {}
        for row in matrix:
            if not isinstance(row, dict):
                continue
            # Check row-level candidate plant
            p_id = str(row.get("plant_id") or row.get("candidate_plant_id") or "")
            p_code = row.get("plant_code") or row.get("candidate_plant_code") or ""
            p_name = row.get("plant_name") or row.get("candidate_plant_name") or ""
            if p_id and (p_code or p_name):
                snapshot_plant_names[p_id] = (p_code, p_name)

            # Check row-level current plant
            curr_id = str(row.get("current_plant_id") or "")
            curr_c = row.get("current_plant_code") or ""
            curr_n = row.get("current_plant_name") or ""
            if curr_id and (curr_c or curr_n) and curr_id not in snapshot_plant_names:
                snapshot_plant_names[curr_id] = (curr_c, curr_n)

        # Check plant_metrics from historical payload
        plant_metrics = hist_payload.get("plant_metrics", {})
        if isinstance(plant_metrics, dict):
            for p_id, p_dict in plant_metrics.items():
                if isinstance(p_dict, dict):
                    p_code = p_dict.get("plant_code", "")
                    p_name = p_dict.get("plant_name", "")
                    if p_id not in snapshot_plant_names and (p_code or p_name):
                        snapshot_plant_names[str(p_id)] = (p_code, p_name)

        # 2. Secondary/Fallback: Only query DB if snapshot did not preserve names/codes
        curr_p_id_str = str(snapshot.current_source_plant_id) if snapshot.current_source_plant_id else ""
        rec_p_id_str = str(snapshot.recommended_plant_id) if snapshot.recommended_plant_id else ""

        curr_code, curr_name = snapshot_plant_names.get(curr_p_id_str, ("", ""))
        rec_code, rec_name = snapshot_plant_names.get(rec_p_id_str, ("", ""))

        customer_code = str(hist_payload.get("customer_code", ""))
        customer_name = str(hist_payload.get("customer_name", ""))
        site_code = str(hist_payload.get("site_code", ""))
        site_name = str(hist_payload.get("site_name", ""))

        # Optional DB fallback only if fields are empty
        if not curr_name and snapshot.current_source_plant_id:
            p_res = await session.execute(select(Plant).where(Plant.id == snapshot.current_source_plant_id))
            p_obj = p_res.scalars().first()
            if p_obj:
                curr_code, curr_name = p_obj.code or "", p_obj.name or ""

        if not rec_name and snapshot.recommended_plant_id:
            p_res = await session.execute(select(Plant).where(Plant.id == snapshot.recommended_plant_id))
            p_obj = p_res.scalars().first()
            if p_obj:
                rec_code, rec_name = p_obj.code or "", p_obj.name or ""

        if not customer_name and snapshot.customer_id:
            c_res = await session.execute(select(Customer).where(Customer.id == snapshot.customer_id))
            c_obj = c_res.scalars().first()
            if c_obj:
                customer_code, customer_name = c_obj.code or "", c_obj.name or ""

        if not site_name and snapshot.site_id:
            s_res = await session.execute(select(Site).where(Site.id == snapshot.site_id))
            s_obj = s_res.scalars().first()
            if s_obj:
                site_code, site_name = s_obj.code or "", s_obj.name or ""

        # Map canonical case category with full alias reconciliation
        raw_cat = None
        if hist_payload and hist_payload.get("case_category"):
            raw_cat = hist_payload.get("case_category")
        elif matrix:
            for c in matrix:
                if isinstance(c, dict) and c.get("case_category"):
                    raw_cat = c.get("case_category")
                    break
        if not raw_cat and snapshot.failure_reason_code:
            raw_cat = snapshot.failure_reason_code
        if not raw_cat:
            if snapshot.recommendation_status == "LOCATION_DATA_MISSING":
                raw_cat = "C11_COORDINATES_MISSING"
            elif snapshot.recommendation_status == "NO_CLEAR_DIFFERENCE":
                raw_cat = "C5_NOMINAL_DIFFERENCE_BELOW_SWITCH"
            elif snapshot.recommendation_status == "RECOMMEND_CURRENT_SOURCE":
                raw_cat = "C1_BOTH_AGREE_CURRENT"
            elif snapshot.recommendation_status == "RECOMMEND_ALTERNATIVE":
                raw_cat = "C2_BOTH_AGREE_ALTERNATIVE"
            elif snapshot.recommendation_status == "LIVE_ROUTE_ONLY":
                raw_cat = "C8_LIVE_ROUTE_ONLY_HIST_INSUFFICIENT"
            elif snapshot.recommendation_status == "HISTORICAL_COMPARISON_ONLY":
                raw_cat = "C7_HISTORICAL_ONLY_GOOGLE_STALE_FAILED"
            else:
                raw_cat = "C9_NO_EVIDENCE_AVAILABLE"

        cat_map = {
            "C1_BOTH_AGREE_CURRENT": "C1_BOTH_AGREE_CURRENT",
            "C2_BOTH_AGREE_ALT": "C2_BOTH_AGREE_ALTERNATIVE",
            "C2_BOTH_AGREE_ALTERNATIVE": "C2_BOTH_AGREE_ALTERNATIVE",
            "C3_TRAFFIC_OVERRIDE_ALT": "C3_TRAFFIC_OVERRIDE_ALTERNATIVE",
            "C3_TRAFFIC_OVERRIDE_ALTERNATIVE": "C3_TRAFFIC_OVERRIDE_ALTERNATIVE",
            "C4_TRAFFIC_OVERRIDE_CURRENT": "C4_TRAFFIC_OVERRIDE_CURRENT",
            "C5_NOMINAL_DIFFERENCE_BELOW_SWITCH": "C5_NOMINAL_DIFFERENCE_BELOW_SWITCH",
            "C5_MARGINAL_ALT_DIFFERENCE": "C5_NOMINAL_DIFFERENCE_BELOW_SWITCH",
            "C6_IDENTICAL_ROUTE_ESTIMATE": "C6_IDENTICAL_ROUTE_ESTIMATE",
            "C7_HISTORICAL_ONLY_GOOGLE_STALE_FAILED": "C7_HISTORICAL_ONLY_GOOGLE_STALE_FAILED",
            "C7_HISTORICAL_ONLY": "C7_HISTORICAL_ONLY_GOOGLE_STALE_FAILED",
            "C8_LIVE_ROUTE_ONLY_HIST_INSUFFICIENT": "C8_LIVE_ROUTE_ONLY_HIST_INSUFFICIENT",
            "C8_LIVE_ROUTE_ONLY": "C8_LIVE_ROUTE_ONLY_HIST_INSUFFICIENT",
            "C9_NO_EVIDENCE_AVAILABLE": "C9_NO_EVIDENCE_AVAILABLE",
            "C9_NO_EVIDENCE": "C9_NO_EVIDENCE_AVAILABLE",
            "C10_CANDIDATE_ROUTE_FAILED": "C10_CANDIDATE_ROUTE_FAILED",
            "C11_COORDINATES_MISSING": "C11_COORDINATES_MISSING",
            "LOCATION_DATA_MISSING": "C11_COORDINATES_MISSING",
        }
        decision_case = cat_map.get(raw_cat, raw_cat) if raw_cat else "C9_NO_EVIDENCE_AVAILABLE"

        # 3. Assemble candidate comparison DTOs strictly from snapshot matrix
        target_rec_id = str(snapshot.recommended_plant_id) if snapshot.recommended_plant_id else None
        target_curr_id = str(snapshot.current_source_plant_id) if snapshot.current_source_plant_id else None

        comparisons: List[CandidateComparisonDTO] = []
        for row in matrix:
            if not isinstance(row, dict):
                continue
            p_id_str = str(row.get("plant_id") or row.get("candidate_plant_id") or "")
            p_code = row.get("plant_code") or row.get("candidate_plant_code") or snapshot_plant_names.get(p_id_str, ("", ""))[0]
            p_name = row.get("plant_name") or row.get("candidate_plant_name") or snapshot_plant_names.get(p_id_str, ("", ""))[1]

            is_rec = bool(row.get("is_recommended") or (target_rec_id and p_id_str == target_rec_id))
            is_curr = bool(row.get("is_current_source") or (target_curr_id and p_id_str == target_curr_id))

            g_dist = row.get("google_candidate_distance_km") if row.get("google_candidate_distance_km") is not None else row.get("google_distance_km")
            g_dur = row.get("google_candidate_duration_minutes") if row.get("google_candidate_duration_minutes") is not None else row.get("google_duration_in_traffic_mins")
            g_static = row.get("google_candidate_static_minutes") if row.get("google_candidate_static_minutes") is not None else row.get("google_static_duration_mins")
            g_delay = row.get("google_candidate_traffic_delay_minutes") if row.get("google_candidate_traffic_delay_minutes") is not None else row.get("google_traffic_delay_mins")

            hist_p50 = row.get("historical_candidate_p50_minutes") if row.get("historical_candidate_p50_minutes") is not None else row.get("historical_t1_p50_mins")
            hist_p25 = row.get("historical_t1_p25_mins")
            hist_p75 = row.get("historical_t1_p75_mins")
            hist_iqr = row.get("historical_t1_iqr_mins")
            hist_samples = int(row.get("historical_candidate_sample_count") if row.get("historical_candidate_sample_count") is not None else (row.get("historical_sample_count") or 0))
            hist_conf = str(row.get("historical_candidate_confidence") or row.get("historical_confidence") or "NONE")
            hist_win = str(row.get("historical_winner_status") or "NOT_EVALUATED")

            comparisons.append(
                CandidateComparisonDTO(
                    plant_id=p_id_str,
                    plant_code=p_code,
                    plant_name=p_name,
                    is_current_source=is_curr,
                    is_recommended=is_rec,
                    is_viable=bool(row.get("is_viable", True)),
                    crow_fly_distance_km=float(row.get("crow_fly_distance_km", 0.0)),
                    google_distance_km=g_dist,
                    google_duration_in_traffic_mins=g_dur,
                    google_static_duration_mins=g_static,
                    google_traffic_delay_mins=g_delay,
                    historical_t1_p50_mins=hist_p50,
                    historical_t1_p25_mins=hist_p25,
                    historical_t1_p75_mins=hist_p75,
                    historical_t1_iqr_mins=hist_iqr,
                    historical_sample_count=hist_samples,
                    historical_confidence=hist_conf,
                    historical_winner_status=hist_win,
                )
            )

        exec_id = execution_id or f"ROUT-REP-{snapshot.analysis_id.hex[:12]}"

        metadata = ReportMetadataDTO(
            execution_id=exec_id,
            report_id="route_analysis",
            report_name="Route Analysis Decision Support Report",
            generated_at=datetime.now(timezone.utc).isoformat(),
            requested_by=requested_by,
        )

        return RouteAnalysisReportCanonical(
            metadata=metadata,
            requested_scope={"analysis_id": str(snapshot.analysis_id)},
            effective_scope={
                "customer_id": str(snapshot.customer_id) if snapshot.customer_id else None,
                "site_id": str(snapshot.site_id) if snapshot.site_id else None,
                "current_plant_id": str(snapshot.current_source_plant_id) if snapshot.current_source_plant_id else None,
            },
            scope_fingerprint=f"route-analysis-{snapshot.analysis_id}",
            status=ReportStatus.COMPLETED,
            record_count=1,
            analysis_id=str(snapshot.analysis_id),
            customer_id=str(snapshot.customer_id) if snapshot.customer_id else None,
            customer_code=customer_code,
            customer_name=customer_name,
            site_id=str(snapshot.site_id) if snapshot.site_id else None,
            site_code=site_code,
            site_name=site_name,
            current_source_plant_id=str(snapshot.current_source_plant_id) if snapshot.current_source_plant_id else None,
            current_source_plant_code=curr_code,
            current_source_plant_name=curr_name,
            recommended_plant_id=str(snapshot.recommended_plant_id) if snapshot.recommended_plant_id else None,
            recommended_plant_code=rec_code if snapshot.recommended_plant_id else None,
            recommended_plant_name=rec_name if snapshot.recommended_plant_id else None,
            recommendation_status=snapshot.recommendation_status,
            decision_case=decision_case,
            decision_template_title=snapshot.recommendation_status.replace("_", " ").title(),
            decision_reason_summary=snapshot.decision_reason_summary,
            is_traffic_override=bool(hist_payload.get("is_traffic_override", False)),
            minutes_saved=hist_payload.get("minutes_saved"),
            failure_reason_code=snapshot.failure_reason_code,
            analysis_mode=snapshot.analysis_mode,
            planned_departure_time=snapshot.planned_departure_time.isoformat() if snapshot.planned_departure_time else None,
            engine_version=snapshot.engine_version,
            policy_version=snapshot.policy_version,
            analysis_context=snapshot.analysis_context,
            operator_notes=snapshot.operator_notes,
            erp_import_batch_id=str(snapshot.erp_import_batch_id) if snapshot.erp_import_batch_id else None,
            created_at=snapshot.queried_at.isoformat(),
            created_by=None,
            google_queried_at=snapshot.google_queried_at.isoformat() if snapshot.google_queried_at else None,
            google_data_freshness_seconds=snapshot.data_freshness_seconds,
            is_google_cached=snapshot.is_cached_result,
            is_google_fresh=not snapshot.is_cached_result,
            is_google_stale_cache=snapshot.is_cached_result,
            google_evidence_payload=google_payload,
            is_historical_sufficient=bool(hist_payload.get("is_overall_sufficient", False)),
            historical_evidence_payload=hist_payload,
            comparisons=comparisons,
        )

    @classmethod
    async def build_canonical_report(
        cls,
        session: AsyncSession,
        execution_id: str,
        requested_scope: Dict[str, Any],
        effective_scope: Dict[str, Any],
        requested_by: str = "SYSTEM",
        status: ReportStatus = ReportStatus.COMPLETED,
    ) -> RouteAnalysisReportCanonical:
        analysis_id_str = requested_scope.get("analysis_id") or effective_scope.get("analysis_id")
        if not analysis_id_str:
            stmt = select(RouteAnalysisSnapshot).order_by(RouteAnalysisSnapshot.queried_at.desc()).limit(1)
            res = await session.execute(stmt)
            snapshot = res.scalars().first()
            if not snapshot:
                raise RecordNotFoundError("No route analysis snapshots found in database.")
        else:
            try:
                a_uuid = uuid.UUID(analysis_id_str)
            except ValueError as exc:
                raise ValueError(f"Invalid analysis_id UUID format: {analysis_id_str}") from exc

            stmt = select(RouteAnalysisSnapshot).where(RouteAnalysisSnapshot.analysis_id == a_uuid)
            res = await session.execute(stmt)
            snapshot = res.scalars().first()
            if not snapshot:
                raise RecordNotFoundError(f"Route analysis snapshot '{analysis_id_str}' not found.")

        return await cls.build_canonical_report_from_snapshot(
            session=session,
            snapshot=snapshot,
            execution_id=execution_id,
            requested_by=requested_by,
        )
