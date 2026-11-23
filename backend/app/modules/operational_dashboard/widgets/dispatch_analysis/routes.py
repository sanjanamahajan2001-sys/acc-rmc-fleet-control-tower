from datetime import datetime, timezone
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.dependencies.common import get_db_session
from app.core.config import settings
from app.core.exceptions import RecordNotFoundError, DomainValidationError
from app.dependencies.auth import get_optional_user_claims, require_authenticated_user
from app.schemas.auth import TokenPayload
from app.modules.erp.models import Site, Plant, Customer, Dispatch
from app.modules.operational_dashboard.models.route_analysis import RouteAnalysisSnapshot
from sqlalchemy import desc, func, distinct, distinct
from app.modules.operational_dashboard.widgets.dispatch_analysis.services.cadence_engine import (
    DispatchCadenceEngine,
)
from app.modules.operational_dashboard.widgets.dispatch_analysis.services.route_analysis_service import (
    RouteAnalysisOrchestrationService,
)
from app.modules.operational_dashboard.widgets.dispatch_analysis.services.google_usage_service import (
    GoogleApiUsageService,
)
from app.modules.operational_dashboard.widgets.dispatch_analysis.dtos import (
    TMIncidentAccessExecutionRequestDTO,
    TMIncidentAccessResponseDTO,
    TMIncidentAccessResultDTO,
    OperationalPlantsListResponseDTO,
    OperationalPlantInfoDTO,
    SynthesisCandidateComparisonDTO,
    DispatchCadenceKPIResponseDTO,
    DispatchCadenceTableResponseDTO,
    DispatchDelayAnalyticsResponseDTO,
    OperationalInsightsResponseDTO,
    CustomerVehicleReportResponseDTO,
    RouteAnalysisExecutionRequestDTO,
    RouteAnalysisSynthesisResultDTO,
    RouteAnalysisSnapshotResponseDTO,
    RouteAnalysisHistoryResponseDTO,
    RouteAnalysisSnapshotItemDTO,
    RouteAnalysisBatchContextDTO,
    RouteAnalysisBatchGenerateRequestDTO,
    RouteAnalysisBatchGenerateResponseDTO,
    GoogleApiUsageResponseDTO,
)
from app.modules.reports.handlers.route_analysis_handler import RouteAnalysisReportHandler
from app.modules.reports.renderers.route_analysis_renderer import (
    RouteAnalysisXLSXRenderer,
    RouteAnalysisPDFRenderer,
)

dispatch_analysis_router = APIRouter(prefix="/dispatch-analysis", tags=["Dispatch Analysis"])
router = dispatch_analysis_router


# =============================================================================
# SITES LISTING HELPER ENDPOINT FOR ROUTE ANALYSIS SELECTION
# =============================================================================


@dispatch_analysis_router.get("/sites")
async def get_dispatch_analysis_sites(
    plant_id: Optional[str] = Query(None, description="Optional plant ID or code filter"),
    session: AsyncSession = Depends(get_db_session),
    claims: Optional[TokenPayload] = Depends(get_optional_user_claims),
):
    """
    Returns available destination delivery sites for Route Analysis evaluation.
    """
    stmt = select(Site).order_by(Site.name.asc())
    if plant_id and plant_id != "ALL":
        try:
            p_uuid = uuid.UUID(plant_id)
            stmt = stmt.where(Site.plant_id == p_uuid)
        except ValueError:
            # plant_id may be code
            p_stmt = select(Plant.id).where(Plant.code == plant_id)
            p_id = (await session.execute(p_stmt)).scalar()
            if p_id:
                stmt = stmt.where(Site.plant_id == p_id)

    sites_db = (await session.execute(stmt)).scalars().all()
    return {
        "success": True,
        "data": [
            {
                "id": str(s.id),
                "code": s.code,
                "name": s.name,
                "plant_id": str(s.plant_id) if s.plant_id else None,
                "latitude": s.latitude,
                "longitude": s.longitude,
            }
            for s in sites_db
        ],
    }


# =============================================================================
# DISPATCH CADENCE & DELAY ANALYTICS ENDPOINTS
# =============================================================================


@dispatch_analysis_router.get("/kpis", response_model=DispatchCadenceKPIResponseDTO)
async def get_dispatch_analysis_kpis(
    plant_id: Optional[str] = Query(None, description="Optional plant code filter"),
    customer_id: Optional[str] = Query(None, description="Optional customer code filter"),
    dataset_type: Optional[str] = Query("REAL_ONLY", description="Dataset type: REAL_ONLY, SYNTHETIC_ONLY, ALL"),
    session: AsyncSession = Depends(get_db_session),
    claims: Optional[TokenPayload] = Depends(get_optional_user_claims),
):
    filters = {
        "plant_id": plant_id,
        "customer_id": customer_id,
        "dataset_type": dataset_type or "REAL_ONLY",
    }
    return await DispatchCadenceEngine.get_kpis(session, filters)


@dispatch_analysis_router.get("/cadence", response_model=DispatchCadenceTableResponseDTO)
async def get_dispatch_cadence_table(
    plant_id: Optional[str] = Query(None, description="Optional plant code filter"),
    customer_id: Optional[str] = Query(None, description="Optional customer code filter"),
    dataset_type: Optional[str] = Query("REAL_ONLY", description="Dataset type: REAL_ONLY, SYNTHETIC_ONLY, ALL"),
    session: AsyncSession = Depends(get_db_session),
    claims: Optional[TokenPayload] = Depends(get_optional_user_claims),
):
    filters = {
        "plant_id": plant_id,
        "customer_id": customer_id,
        "dataset_type": dataset_type or "REAL_ONLY",
    }
    return await DispatchCadenceEngine.get_cadence_table(session, filters)


@dispatch_analysis_router.get("/delay-analytics", response_model=DispatchDelayAnalyticsResponseDTO)
async def get_dispatch_delay_analytics(
    plant_id: Optional[str] = Query(None, description="Optional plant code filter"),
    customer_id: Optional[str] = Query(None, description="Optional customer code filter"),
    dataset_type: Optional[str] = Query("REAL_ONLY", description="Dataset type: REAL_ONLY, SYNTHETIC_ONLY, ALL"),
    session: AsyncSession = Depends(get_db_session),
    claims: Optional[TokenPayload] = Depends(get_optional_user_claims),
):
    filters = {
        "plant_id": plant_id,
        "customer_id": customer_id,
        "dataset_type": dataset_type or "REAL_ONLY",
    }
    return await DispatchCadenceEngine.get_delay_analytics(session, filters)


@dispatch_analysis_router.get("/insights", response_model=OperationalInsightsResponseDTO)
@dispatch_analysis_router.get("/operational-insights", response_model=OperationalInsightsResponseDTO)
async def get_operational_insights(
    plant_id: Optional[str] = Query(None, description="Optional plant code filter"),
    customer_id: Optional[str] = Query(None, description="Optional customer code filter"),
    dataset_type: Optional[str] = Query("REAL_ONLY", description="Dataset type: REAL_ONLY, SYNTHETIC_ONLY, ALL"),
    session: AsyncSession = Depends(get_db_session),
    claims: Optional[TokenPayload] = Depends(get_optional_user_claims),
):
    filters = {
        "plant_id": plant_id,
        "customer_id": customer_id,
        "dataset_type": dataset_type or "REAL_ONLY",
    }
    return await DispatchCadenceEngine.get_operational_insights(session, filters)


@dispatch_analysis_router.get("/customer-report", response_model=CustomerVehicleReportResponseDTO)
async def get_customer_vehicle_report(
    plant_id: Optional[str] = Query(None, description="Optional plant code filter"),
    customer_id: Optional[str] = Query(None, description="Optional customer code filter"),
    dataset_type: Optional[str] = Query("REAL_ONLY", description="Dataset type: REAL_ONLY, SYNTHETIC_ONLY, ALL"),
    session: AsyncSession = Depends(get_db_session),
    claims: Optional[TokenPayload] = Depends(get_optional_user_claims),
):
    filters = {
        "plant_id": plant_id,
        "customer_id": customer_id,
        "dataset_type": dataset_type or "REAL_ONLY",
    }
    return await DispatchCadenceEngine.get_customer_report(session, filters)


# =============================================================================
# WS-ROUT-4: ROUTE ANALYSIS DECISION SUPPORT & SNAPSHOT REST ENDPOINTS
# =============================================================================


@dispatch_analysis_router.post(
    "/route-analysis",
    response_model=RouteAnalysisSnapshotResponseDTO,
    summary="Execute Route Analysis and Persist Immutable Snapshot",
)
async def execute_route_analysis(
    request_dto: RouteAnalysisExecutionRequestDTO,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenPayload = Depends(require_authenticated_user),
):
    """
    Executes a deterministic 2D Route Analysis synthesis combining:
    - WS-ROUT-1: Historical ERP operational T1 transit evidence
    - WS-ROUT-2: Google Routes API v2 current/planned traffic estimates
    - WS-ROUT-3: 2D synthesis recommendation matrix & template generator
    - WS-ROUT-4: Transactional persistence of immutable audit snapshot

    Every execution generates a new immutable snapshot record.
    """
    user_uuid = uuid.UUID(claims.sub) if claims and claims.sub else None
    result = await RouteAnalysisOrchestrationService.execute_analysis(
        session=session,
        request_dto=request_dto,
        user_id=user_uuid,
    )
    return RouteAnalysisSnapshotResponseDTO(success=True, data=result)


@dispatch_analysis_router.get(
    "/route-analysis/batch-context",
    summary="Get Active ERP Batch Lineage and Route Analysis Generation Context",
)
async def get_route_analysis_batch_context(
    session: AsyncSession = Depends(get_db_session),
    claims: Optional[TokenPayload] = Depends(get_optional_user_claims),
):
    """
    Returns active ERP batch lineage metrics:
    - total_erp_dispatches: total dispatch rows in active batch
    - unique_route_corridors: distinct physical origin_plant -> destination_site pairs
    - eligible_corridors: backward compatible alias for unique_route_corridors
    - analyzed_snapshots: total dispatch-level snapshots generated for this batch
    - reconciled outcome metrics
    """
    # 1. Identify active ERP import batch (most populated batch)
    latest_batch_stmt = (
        select(
            Dispatch.import_batch_id,
            func.count(Dispatch.id).label("total_dispatches"),
            func.max(Dispatch.created_at).label("import_date"),
        )
        .where(Dispatch.import_batch_id != None)
        .group_by(Dispatch.import_batch_id)
        .order_by(func.count(Dispatch.id).desc())
        .limit(1)
    )
    batch_res = (await session.execute(latest_batch_stmt)).first()

    if not batch_res:
        return {
            "success": True,
            "data": RouteAnalysisBatchContextDTO(
                batch_id=None,
                import_timestamp=None,
                total_erp_dispatches=0,
                unique_route_corridors=0,
                eligible_corridors=0,
                analyzed_snapshots=0,
                generation_status="NOT_GENERATED",
                generated_timestamp=None,
            ),
        }

    batch_id, total_disps, max_date = batch_res

    # Pre-fetch master data to determine physical corridor (plant_id, destination_site_id)
    custs_res = await session.execute(select(Customer))
    custs_map = {c.id: c for c in custs_res.scalars().all()}
    sites_res = await session.execute(select(Site))
    sites = sites_res.scalars().all()

    # Load all distinct (plant_id, customer_id) in batch to compute physical corridors
    disp_pairs_stmt = (
        select(Dispatch.plant_id, Dispatch.customer_id)
        .where(Dispatch.import_batch_id == batch_id)
        .distinct()
    )
    disp_pairs = (await session.execute(disp_pairs_stmt)).all()

    unique_corridors_set = set()
    for pid, cid in disp_pairs:
        c_obj = custs_map.get(cid)
        c_name = c_obj.name.lower() if c_obj and c_obj.name else ""
        if not c_name or "default_customer" in c_name:
            continue
        p_sites = [s for s in sites if s.plant_id == pid]
        matching_sites = [s for s in p_sites if c_name in s.name.lower() or s.name.lower() in c_name]
        if not matching_sites:
            matching_sites = [s for s in sites if c_name in s.name.lower() or s.name.lower() in c_name]
        site_chosen = matching_sites[0] if matching_sites else None
        if site_chosen and site_chosen.latitude is not None and site_chosen.longitude is not None:
            unique_corridors_set.add((str(pid), str(site_chosen.id)))

    unique_corridors_count = len(unique_corridors_set)

    # Query snapshots specifically stamped with this batch_id
    snap_stmt = (
        select(
            func.count(RouteAnalysisSnapshot.analysis_id).label("total_snaps"),
            func.max(RouteAnalysisSnapshot.queried_at).label("max_queried_at"),
            func.count(RouteAnalysisSnapshot.analysis_id).filter(RouteAnalysisSnapshot.recommendation_status == "RECOMMEND_ALTERNATIVE").label("alt_rec"),
            func.count(RouteAnalysisSnapshot.analysis_id).filter(RouteAnalysisSnapshot.recommendation_status == "RECOMMEND_CURRENT_SOURCE").label("retain_app"),
            func.count(RouteAnalysisSnapshot.analysis_id).filter(RouteAnalysisSnapshot.recommendation_status == "NO_CLEAR_DIFFERENCE").label("no_diff"),
            func.count(RouteAnalysisSnapshot.analysis_id).filter(RouteAnalysisSnapshot.recommendation_status == "HISTORICAL_COMPARISON_ONLY").label("hist_only"),
            func.count(RouteAnalysisSnapshot.analysis_id).filter(RouteAnalysisSnapshot.recommendation_status == "LIVE_ROUTE_ONLY").label("live_only"),
            func.count(RouteAnalysisSnapshot.analysis_id).filter(
                (RouteAnalysisSnapshot.recommendation_status == "LOCATION_DATA_MISSING") | (RouteAnalysisSnapshot.failure_reason_code == "LOCATION_DATA_MISSING")
            ).label("loc_missing"),
        )
        .where(RouteAnalysisSnapshot.erp_import_batch_id == batch_id)
    )
    snap_res = (await session.execute(snap_stmt)).first()
    snap_count = snap_res.total_snaps if snap_res else 0
    snap_max_date = snap_res.max_queried_at if snap_res else None

    gen_status = "GENERATED" if snap_count > 0 else "NOT_GENERATED"

    return {
        "success": True,
        "data": RouteAnalysisBatchContextDTO(
            batch_id=str(batch_id) if batch_id else None,
            import_timestamp=max_date.isoformat() if max_date else None,
            total_erp_dispatches=total_disps,
            unique_route_corridors=unique_corridors_count,
            eligible_corridors=unique_corridors_count,
            analyzed_snapshots=snap_count,
            alt_recommended_count=snap_res.alt_rec if snap_res else 0,
            retain_approved_count=snap_res.retain_app if snap_res else 0,
            no_difference_count=snap_res.no_diff if snap_res else 0,
            historical_only_count=snap_res.hist_only if snap_res else 0,
            live_only_count=snap_res.live_only if snap_res else 0,
            location_missing_count=snap_res.loc_missing if snap_res else 0,
            generation_status=gen_status,
            generated_timestamp=snap_max_date.isoformat() if snap_max_date else None,
        ),
    }


@dispatch_analysis_router.post(
    "/route-analysis/generate-batch",
    response_model=RouteAnalysisBatchGenerateResponseDTO,
    summary="Execute Batch Route Analysis Generation for Complete ERP Population",
)
async def generate_route_analysis_batch(
    payload: Optional[RouteAnalysisBatchGenerateRequestDTO] = None,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenPayload = Depends(require_authenticated_user),
):
    """
    Analyzes the complete dispatch population from the authoritative ERP batch,
    generating individual dispatch-level RouteAnalysisSnapshot records while
    deduplicating 2D physical corridor route evidence computation.
    """
    user_uuid = uuid.UUID(claims.sub) if claims and claims.sub else None
    req_payload = payload or RouteAnalysisBatchGenerateRequestDTO()

    # 1. Identify active ERP import batch
    latest_batch_stmt = (
        select(Dispatch.import_batch_id, func.count(Dispatch.id))
        .where(Dispatch.import_batch_id != None)
        .group_by(Dispatch.import_batch_id)
        .order_by(func.count(Dispatch.id).desc())
        .limit(1)
    )
    batch_res = (await session.execute(latest_batch_stmt)).first()
    if not batch_res:
        return RouteAnalysisBatchGenerateResponseDTO(
            success=False,
            batch_id=None,
            generated_count=0,
            message="No active ERP import batch found.",
        )
    active_batch_id = batch_res[0]

    # 2. Load all dispatches in active batch
    dispatches = (
        await session.execute(
            select(Dispatch).where(Dispatch.import_batch_id == active_batch_id)
        )
    ).scalars().all()

    # Master data maps
    plants_map = {p.id: p for p in (await session.execute(select(Plant))).scalars().all()}
    custs_map = {c.id: c for c in (await session.execute(select(Customer))).scalars().all()}
    sites = (await session.execute(select(Site))).scalars().all()

    # Corridor evidence cache: (plant_id, site_id) -> evidence dict
    corridor_evidence_cache = {}

    snapshots_to_create = []

    for d in dispatches:
        pid = d.plant_id
        cid = d.customer_id
        p_obj = plants_map.get(pid)
        c_obj = custs_map.get(cid)
        c_name = c_obj.name.lower() if c_obj and c_obj.name else ""

        # Destination Site resolution: Plant-scoped site first, then global customer site lookup
        site_chosen = None
        if c_name and "default_customer" not in c_name:
            p_sites = [s for s in sites if s.plant_id == pid]
            matching_sites = [s for s in p_sites if c_name in s.name.lower() or s.name.lower() in c_name]
            if not matching_sites:
                matching_sites = [s for s in sites if c_name in s.name.lower() or s.name.lower() in c_name]
            site_chosen = matching_sites[0] if matching_sites else None

        now_utc = datetime.now(timezone.utc)

        if site_chosen and site_chosen.latitude is not None and site_chosen.longitude is not None:
            corridor_key = (str(pid), str(site_chosen.id))
            if corridor_key not in corridor_evidence_cache:
                exec_req = RouteAnalysisExecutionRequestDTO(
                    site_id=str(site_chosen.id),
                    customer_id=str(cid) if cid else None,
                    current_source_plant_id=str(pid) if pid else None,
                    analysis_mode=req_payload.analysis_mode or "NOW",
                    planned_departure_time=req_payload.planned_departure_time,
                    force_refresh=req_payload.force_refresh,
                    analysis_context="ROUTINE",
                )
                try:
                    res = await RouteAnalysisOrchestrationService.execute_analysis(
                        session=session,
                        request_dto=exec_req,
                        user_id=user_uuid,
                        persist_snapshot=False,
                    )

                    if res:
                        corridor_evidence_cache[corridor_key] = {
                            "recommendation_status": res.recommendation_status.value if hasattr(res.recommendation_status, "value") else str(res.recommendation_status),
                            "recommended_plant_id": uuid.UUID(res.recommended_plant_id) if res.recommended_plant_id else None,
                            "failure_reason_code": res.failure_reason_code,
                            "decision_reason_summary": res.decision_reason_summary,
                            "historical_evidence_payload": res.historical_evidence.model_dump() if res.historical_evidence else {},
                            "google_evidence_payload": res.google_evidence.model_dump() if res.google_evidence else {},
                            "candidate_comparison_matrix": [c.model_dump() for c in res.comparisons] if res.comparisons else [],
                            "google_queried_at": datetime.fromisoformat(res.google_evidence.response_timestamp) if res.google_evidence and res.google_evidence.response_timestamp else None,
                            "data_freshness_seconds": int(res.google_cache_age_seconds or 0),
                            "is_cached_result": res.is_google_stale_cache or (res.google_cache_age_seconds > 0) if res.google_evidence else False,
                            "engine_version": res.engine_version,
                            "policy_version": res.policy_version,
                        }
                except Exception:
                    pass

            evidence = corridor_evidence_cache.get(corridor_key)
            if evidence:
                snap = RouteAnalysisSnapshot(
                    analysis_id=uuid.uuid4(),
                    customer_id=cid,
                    site_id=site_chosen.id,
                    current_source_plant_id=pid,
                    analysis_mode=req_payload.analysis_mode or "NOW",
                    recommendation_status=evidence["recommendation_status"],
                    recommended_plant_id=evidence["recommended_plant_id"],
                    failure_reason_code=evidence["failure_reason_code"],
                    decision_reason_summary=evidence["decision_reason_summary"],
                    historical_evidence_payload=evidence["historical_evidence_payload"],
                    google_evidence_payload=evidence["google_evidence_payload"],
                    candidate_comparison_matrix=evidence["candidate_comparison_matrix"],
                    engine_version=evidence["engine_version"],
                    policy_version=evidence["policy_version"],
                    analysis_context="ERP_BATCH",
                    operator_notes=f"Auto-generated for dispatch {d.dispatch_number or d.id}",
                    erp_import_batch_id=active_batch_id,
                    data_freshness_seconds=evidence["data_freshness_seconds"],
                    is_cached_result=True,
                    google_queried_at=evidence["google_queried_at"],
                    queried_at=now_utc,
                    source_lineage={
                        "dispatch_id": str(d.id),
                        "dispatch_number": d.dispatch_number,
                        "trip_number": getattr(d, "trip_number", None),
                        "order_id": str(getattr(d, "order_id", None)) if getattr(d, "order_id", None) else None,
                        "batch_id": str(active_batch_id),
                    },
                )
                snapshots_to_create.append(snap)
            else:
                # Failed candidate route
                snap = RouteAnalysisSnapshot(
                    analysis_id=uuid.uuid4(),
                    customer_id=cid,
                    site_id=site_chosen.id if site_chosen else None,
                    current_source_plant_id=pid,
                    analysis_mode=req_payload.analysis_mode or "NOW",
                    recommendation_status="NO_CLEAR_DIFFERENCE",
                    failure_reason_code="C10_CANDIDATE_ROUTE_FAILED",
                    decision_reason_summary="Route evaluation could not be completed for this candidate site.",
                    historical_evidence_payload={"case_category": "C10_CANDIDATE_ROUTE_FAILED"},
                    google_evidence_payload={},
                    candidate_comparison_matrix=[],
                    engine_version="1.0.0",
                    policy_version="1.0.0",
                    analysis_context="ERP_BATCH",
                    operator_notes=f"Auto-generated for dispatch {d.dispatch_number or d.id}",
                    erp_import_batch_id=active_batch_id,
                    data_freshness_seconds=0,
                    is_cached_result=False,
                    queried_at=now_utc,
                    source_lineage={
                        "dispatch_id": str(d.id),
                        "dispatch_number": d.dispatch_number,
                        "trip_number": getattr(d, "trip_number", None),
                        "order_id": str(getattr(d, "order_id", None)) if getattr(d, "order_id", None) else None,
                        "batch_id": str(active_batch_id),
                    },
                )
                snapshots_to_create.append(snap)
        else:
            # Geocoded destination site missing
            snap = RouteAnalysisSnapshot(
                analysis_id=uuid.uuid4(),
                customer_id=cid,
                site_id=None,
                current_source_plant_id=pid,
                analysis_mode=req_payload.analysis_mode or "NOW",
                recommendation_status="LOCATION_DATA_MISSING",
                failure_reason_code="LOCATION_DATA_MISSING",
                decision_reason_summary="No geocoded destination site matches this customer dispatch. Geocoding required for route analysis.",
                historical_evidence_payload={"case_category": "C11_COORDINATES_MISSING"},
                google_evidence_payload={},
                candidate_comparison_matrix=[],
                engine_version="1.0.0",
                policy_version="1.0.0",
                analysis_context="ERP_BATCH",
                operator_notes=f"Auto-generated for dispatch {d.dispatch_number or d.id} (Location missing)",
                erp_import_batch_id=active_batch_id,
                data_freshness_seconds=0,
                is_cached_result=False,
                queried_at=now_utc,
                source_lineage={
                    "dispatch_id": str(d.id),
                    "dispatch_number": d.dispatch_number,
                    "trip_number": getattr(d, "trip_number", None),
                    "order_id": str(getattr(d, "order_id", None)) if getattr(d, "order_id", None) else None,
                    "batch_id": str(active_batch_id),
                },
            )
            snapshots_to_create.append(snap)

    # Chunked bulk insertion to handle full ERP dataset reliably
    chunk_size = 500
    for i in range(0, len(snapshots_to_create), chunk_size):
        chunk = snapshots_to_create[i : i + chunk_size]
        session.add_all(chunk)
        await session.commit()

    return RouteAnalysisBatchGenerateResponseDTO(
        success=True,
        batch_id=str(active_batch_id),
        generated_count=len(snapshots_to_create),
        message=f"Successfully generated {len(snapshots_to_create)} dispatch-level route analysis snapshots for active ERP batch.",
    )


@dispatch_analysis_router.get(
    "/route-analysis/snapshot/{analysis_id}",
    response_model=RouteAnalysisSnapshotResponseDTO,
    summary="Retrieve Route Analysis Snapshot by ID",
)
async def get_route_analysis_snapshot(
    analysis_id: str,
    session: AsyncSession = Depends(get_db_session),
    claims: Optional[TokenPayload] = Depends(get_optional_user_claims),
):
    """
    Retrieves a single immutable Route Analysis execution snapshot with full 2D synthesis lineage.
    """
    try:
        snap_uuid = uuid.UUID(analysis_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid snapshot UUID: {analysis_id}",
        )

    stmt = select(RouteAnalysisSnapshot).where(RouteAnalysisSnapshot.analysis_id == snap_uuid)
    snapshot = (await session.execute(stmt)).scalars().first()

    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route analysis snapshot {analysis_id} not found.",
        )

    # Resolve master data
    site = None
    if snapshot.site_id:
        s_res = await session.execute(select(Site).where(Site.id == snapshot.site_id))
        site = s_res.scalars().first()

    curr_plant = None
    if snapshot.current_source_plant_id:
        p_res = await session.execute(select(Plant).where(Plant.id == snapshot.current_source_plant_id))
        curr_plant = p_res.scalars().first()

    rec_plant = None
    if snapshot.recommended_plant_id:
        rp_res = await session.execute(select(Plant).where(Plant.id == snapshot.recommended_plant_id))
        rec_plant = rp_res.scalars().first()

    cust = None
    if snapshot.customer_id:
        c_res = await session.execute(select(Customer).where(Customer.id == snapshot.customer_id))
        cust = c_res.scalars().first()

    # Reconstruct comparisons
    comparisons = []
    if snapshot.candidate_comparison_matrix:
        for c in snapshot.candidate_comparison_matrix:
            if isinstance(c, dict):
                comparisons.append(c)

    # Calculate minutes saved
    min_saved = None
    if snapshot.candidate_comparison_matrix and rec_plant:
        for c in snapshot.candidate_comparison_matrix:
            if isinstance(c, dict) and str(c.get("candidate_plant_id")) == str(rec_plant.id):
                diff = c.get("time_differential_minutes")
                if diff is not None and diff > 0:
                    min_saved = float(diff)

    hist_payload = snapshot.historical_evidence_payload or {}
    google_payload = snapshot.google_evidence_payload or {}
    lineage = snapshot.source_lineage or {}

    raw_cat = None
    if hist_payload and hist_payload.get("case_category"):
        raw_cat = hist_payload.get("case_category")
    elif snapshot.candidate_comparison_matrix:
        for c in snapshot.candidate_comparison_matrix:
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
    norm_case_cat = cat_map.get(raw_cat, raw_cat) if raw_cat else "C9_NO_EVIDENCE_AVAILABLE"


    # Extract detailed route from google payload if present
    detailed_route_val = google_payload.get("detailed_route")
    if not detailed_route_val and google_payload.get("detailed_routes"):
        detailed_dict = google_payload.get("detailed_routes")
        if snapshot.recommended_plant_id and str(snapshot.recommended_plant_id) in detailed_dict:
            detailed_route_val = detailed_dict[str(snapshot.recommended_plant_id)]
        elif snapshot.current_source_plant_id and str(snapshot.current_source_plant_id) in detailed_dict:
            detailed_route_val = detailed_dict[str(snapshot.current_source_plant_id)]
        elif detailed_dict:
            detailed_route_val = next(iter(detailed_dict.values()))

    result_dto = RouteAnalysisSynthesisResultDTO(
        analysis_id=str(snapshot.analysis_id),
        dispatch_id=lineage.get("dispatch_id"),
        dispatch_number=lineage.get("dispatch_number"),
        trip_number=lineage.get("trip_number"),
        site_id=str(snapshot.site_id) if snapshot.site_id else "",
        site_code=site.code if site else "N/A",
        site_name=site.name if site else "N/A",
        site_latitude=site.latitude if site else None,
        site_longitude=site.longitude if site else None,
        current_source_plant_id=str(snapshot.current_source_plant_id) if snapshot.current_source_plant_id else "",
        current_source_plant_code=curr_plant.code if curr_plant else "N/A",
        current_source_plant_name=curr_plant.name if curr_plant else "N/A",
        current_source_plant_latitude=curr_plant.latitude if curr_plant else None,
        current_source_plant_longitude=curr_plant.longitude if curr_plant else None,
        recommended_plant_id=str(snapshot.recommended_plant_id) if snapshot.recommended_plant_id else None,
        recommended_plant_code=rec_plant.code if rec_plant else None,
        recommended_plant_name=rec_plant.name if rec_plant else None,
        recommendation_status=snapshot.recommendation_status,
        primary_case_category=norm_case_cat or "C9_NO_EVIDENCE_AVAILABLE",
        decision_reason_summary=snapshot.decision_reason_summary or "Route analysis evaluated.",
        minutes_saved=min_saved,
        analysis_mode=snapshot.analysis_mode or "NOW",
        requested_departure_time=snapshot.planned_departure_time.isoformat() if snapshot.planned_departure_time else None,
        analysis_timestamp=snapshot.queried_at.isoformat() if snapshot.queried_at else datetime.now(timezone.utc).isoformat(),
        engine_version=snapshot.engine_version or "v1.2.1",
        policy_version=snapshot.policy_version or "ROUTE_POLICY_v1.2.1",
        is_google_fresh=bool(snapshot.google_evidence_payload.get("is_fresh", True)) if snapshot.google_evidence_payload else False,
        is_historical_sufficient=bool(snapshot.historical_evidence_payload.get("is_sufficient", True)) if snapshot.historical_evidence_payload else False,
        comparisons=comparisons,
        historical_evidence=hist_payload,
        google_evidence=google_payload,
        detailed_route=detailed_route_val,
        failure_reason_code=snapshot.failure_reason_code,
    )

    return RouteAnalysisSnapshotResponseDTO(
        success=True,
        data=result_dto,
    )


@dispatch_analysis_router.get(
    "/route-analysis/history",
    response_model=RouteAnalysisHistoryResponseDTO,
    summary="List Historical Route Analysis Snapshots with Server Pagination & Dispatch Lineage",
)
async def get_route_analysis_history(
    batch_id: Optional[str] = Query(None, description="Filter by ERP import batch UUID (defaults to active ERP batch)"),
    customer_id: Optional[str] = Query(None, description="Filter by customer UUID or code"),
    site_id: Optional[str] = Query(None, description="Filter by site UUID or code"),
    plant_id: Optional[str] = Query(None, description="Filter by plant code or UUID"),
    recommendation_status: Optional[str] = Query(None, description="Filter by decision outcome"),
    evaluation_mode: Optional[str] = Query(None, description="Prioritize evaluations matching the active mode ('NOW' or 'PLANNED')"),
    all_batches: bool = Query(False, description="Set True to include all historical batches"),
    page: int = Query(1, ge=1, description="1-indexed page number"),
    page_size: int = Query(50, ge=1, le=500, description="Number of items per page"),
    session: AsyncSession = Depends(get_db_session),
    claims: Optional[TokenPayload] = Depends(get_optional_user_claims),
):
    """
    Retrieves authorized historical Route Analysis execution snapshots with enriched master data and dispatch lineage.
    Defaults to scoping history to the active ERP import batch unless all_batches=True is requested.
    """
    from sqlalchemy import case

    if evaluation_mode and evaluation_mode.upper() in ("PLANNED", "PLANNED_DEPARTURE"):
        mode_priority = case(
            (RouteAnalysisSnapshot.analysis_mode.in_(["PLANNED", "PLANNED_DEPARTURE"]), 0),
            else_=1,
        )
        base_stmt = select(RouteAnalysisSnapshot).order_by(mode_priority, desc(RouteAnalysisSnapshot.queried_at))
    elif evaluation_mode and evaluation_mode.upper() == "NOW":
        mode_priority = case(
            (RouteAnalysisSnapshot.analysis_mode == "NOW", 0),
            else_=1,
        )
        base_stmt = select(RouteAnalysisSnapshot).order_by(mode_priority, desc(RouteAnalysisSnapshot.queried_at))
    else:
        base_stmt = select(RouteAnalysisSnapshot).order_by(desc(RouteAnalysisSnapshot.queried_at))

    count_stmt = select(func.count(RouteAnalysisSnapshot.analysis_id))

    # Determine batch scoping
    if batch_id and batch_id != "ALL":
        try:
            b_uuid = uuid.UUID(batch_id)
            base_stmt = base_stmt.where(RouteAnalysisSnapshot.erp_import_batch_id == b_uuid)
            count_stmt = count_stmt.where(RouteAnalysisSnapshot.erp_import_batch_id == b_uuid)
        except ValueError:
            pass
    elif not all_batches and not (site_id or customer_id):
        # Default overview table to active ERP batch when no specific site/customer is requested
        latest_batch_stmt = (
            select(Dispatch.import_batch_id)
            .where(Dispatch.import_batch_id != None)
            .group_by(Dispatch.import_batch_id)
            .order_by(func.count(Dispatch.id).desc())
            .limit(1)
        )
        active_batch_res = (await session.execute(latest_batch_stmt)).scalar()
        if active_batch_res:
            base_stmt = base_stmt.where(RouteAnalysisSnapshot.erp_import_batch_id == active_batch_res)
            count_stmt = count_stmt.where(RouteAnalysisSnapshot.erp_import_batch_id == active_batch_res)

    if customer_id and customer_id != "ALL":
        try:
            c_uuid = uuid.UUID(customer_id)
            base_stmt = base_stmt.where(RouteAnalysisSnapshot.customer_id == c_uuid)
            count_stmt = count_stmt.where(RouteAnalysisSnapshot.customer_id == c_uuid)
        except ValueError:
            pass

    if site_id and site_id != "ALL":
        try:
            s_uuid = uuid.UUID(site_id)
            base_stmt = base_stmt.where(RouteAnalysisSnapshot.site_id == s_uuid)
            count_stmt = count_stmt.where(RouteAnalysisSnapshot.site_id == s_uuid)
        except ValueError:
            pass

    if recommendation_status and recommendation_status != "ALL":
        base_stmt = base_stmt.where(RouteAnalysisSnapshot.recommendation_status == recommendation_status)
        count_stmt = count_stmt.where(RouteAnalysisSnapshot.recommendation_status == recommendation_status)

    total_count = (await session.execute(count_stmt)).scalar() or 0
    offset = (page - 1) * page_size
    snapshots = list((await session.execute(base_stmt.offset(offset).limit(page_size))).scalars().all())

    # Batch enrich Site, Plant, and Customer entities
    site_ids = [s.site_id for s in snapshots if s.site_id]
    plant_ids = list(set([s.current_source_plant_id for s in snapshots if s.current_source_plant_id] + [s.recommended_plant_id for s in snapshots if s.recommended_plant_id]))
    customer_ids = [s.customer_id for s in snapshots if s.customer_id]

    sites_map = {}
    if site_ids:
        s_res = await session.execute(select(Site).where(Site.id.in_(site_ids)))
        sites_map = {s.id: s for s in s_res.scalars().all()}

    plants_map = {}
    if plant_ids:
        p_res = await session.execute(select(Plant).where(Plant.id.in_(plant_ids)))
        plants_map = {p.id: p for p in p_res.scalars().all()}

    customers_map = {}
    if customer_ids:
        c_res = await session.execute(select(Customer).where(Customer.id.in_(customer_ids)))
        customers_map = {c.id: c for c in c_res.scalars().all()}

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


    items = []
    for s in snapshots:
        site = sites_map.get(s.site_id)
        curr_plant = plants_map.get(s.current_source_plant_id)
        rec_plant = plants_map.get(s.recommended_plant_id)
        cust = customers_map.get(s.customer_id)
        lineage = s.source_lineage or {}

        # Calculate minutes saved
        min_saved = None
        if s.candidate_comparison_matrix and rec_plant:
            for c in s.candidate_comparison_matrix:
                if isinstance(c, dict) and str(c.get("candidate_plant_id")) == str(rec_plant.id):
                    diff = c.get("time_differential_minutes")
                    if diff is not None and diff > 0:
                        min_saved = float(diff)

        # Map canonical case category
        raw_cat = None
        if s.historical_evidence_payload and s.historical_evidence_payload.get("case_category"):
            raw_cat = s.historical_evidence_payload.get("case_category")
        elif s.candidate_comparison_matrix:
            for c in s.candidate_comparison_matrix:
                if isinstance(c, dict) and c.get("case_category"):
                    raw_cat = c.get("case_category")
                    break
        if not raw_cat and s.failure_reason_code:
            raw_cat = s.failure_reason_code
        if not raw_cat:
            if s.recommendation_status == "LOCATION_DATA_MISSING":
                raw_cat = "C11_COORDINATES_MISSING"
            elif s.recommendation_status == "NO_CLEAR_DIFFERENCE":
                raw_cat = "C5_NOMINAL_DIFFERENCE_BELOW_SWITCH"
            elif s.recommendation_status == "RECOMMEND_CURRENT_SOURCE":
                raw_cat = "C1_BOTH_AGREE_CURRENT"
            elif s.recommendation_status == "RECOMMEND_ALTERNATIVE":
                raw_cat = "C2_BOTH_AGREE_ALTERNATIVE"
            elif s.recommendation_status == "LIVE_ROUTE_ONLY":
                raw_cat = "C8_LIVE_ROUTE_ONLY_HIST_INSUFFICIENT"
            elif s.recommendation_status == "HISTORICAL_COMPARISON_ONLY":
                raw_cat = "C7_HISTORICAL_ONLY_GOOGLE_STALE_FAILED"
            else:
                raw_cat = "C9_NO_EVIDENCE_AVAILABLE"

        norm_case_cat = cat_map.get(raw_cat, raw_cat) if raw_cat else "C9_NO_EVIDENCE_AVAILABLE"


        items.append(
            RouteAnalysisSnapshotItemDTO(
                analysis_id=str(s.analysis_id),
                dispatch_id=lineage.get("dispatch_id"),
                dispatch_number=lineage.get("dispatch_number"),
                trip_number=lineage.get("trip_number"),
                customer_id=str(s.customer_id) if s.customer_id else None,
                customer_code=cust.code if cust else None,
                customer_name=cust.name if cust else None,
                site_id=str(s.site_id) if s.site_id else None,
                site_code=site.code if site else None,
                site_name=site.name if site else None,
                current_source_plant_id=str(s.current_source_plant_id) if s.current_source_plant_id else None,
                current_source_plant_code=curr_plant.code if curr_plant else None,
                current_source_plant_name=curr_plant.name if curr_plant else None,
                recommended_plant_id=str(s.recommended_plant_id) if s.recommended_plant_id else None,
                recommended_plant_code=rec_plant.code if rec_plant else None,
                recommended_plant_name=rec_plant.name if rec_plant else None,
                recommendation_status=s.recommendation_status,
                primary_case_category=norm_case_cat,
                failure_reason_code=s.failure_reason_code,
                analysis_mode=s.analysis_mode,
                planned_departure_time=s.planned_departure_time.isoformat() if s.planned_departure_time else None,
                engine_version=s.engine_version,
                policy_version=s.policy_version,
                decision_reason_summary=s.decision_reason_summary,
                minutes_saved=min_saved,
                analysis_context=s.analysis_context,
                operator_notes=s.operator_notes,
                erp_import_batch_id=str(s.erp_import_batch_id) if s.erp_import_batch_id else None,
                data_freshness_seconds=s.data_freshness_seconds,
                is_cached_result=s.is_cached_result,
                queried_at=s.queried_at.isoformat(),
            )
        )

    total_pages = max(1, (total_count + page_size - 1) // page_size)
    return RouteAnalysisHistoryResponseDTO(
        success=True,
        data=items,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# =============================================================================
# WS-ROUT-5: ROUTE ANALYSIS SNAPSHOT EXPORTS (XLSX & PDF)
# =============================================================================


@dispatch_analysis_router.get(
    "/route-analysis/snapshot/{analysis_id}/export/xlsx",
    summary="Export Route Analysis Snapshot as XLSX",
)
async def export_route_analysis_snapshot_xlsx(
    analysis_id: str,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenPayload = Depends(require_authenticated_user),
):
    """
    Renders an authoritative, spreadsheet-formatted XLSX representation of an immutable
    RouteAnalysisSnapshot. Never triggers new routing calls or mathematical recalculation.
    """
    try:
        a_uuid = uuid.UUID(analysis_id)
    except ValueError as exc:
        raise DomainValidationError("Invalid analysis_id UUID format") from exc

    snapshot = await RouteAnalysisOrchestrationService.get_snapshot_by_id(session, a_uuid)
    if not snapshot:
        raise RecordNotFoundError(f"Route analysis snapshot '{analysis_id}' not found")

    user_name = claims.username if claims and hasattr(claims, "username") else (claims.sub if claims else "SYSTEM")
    canonical_report = await RouteAnalysisReportHandler.build_canonical_report_from_snapshot(
        session=session,
        snapshot=snapshot,
        requested_by=user_name,
    )

    xlsx_bytes = RouteAnalysisXLSXRenderer.render(canonical_report)
    filename = f"route_analysis_{analysis_id[:8]}.xlsx"

    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "X-Content-Type-Options": "nosniff",
        },
    )


@dispatch_analysis_router.get(
    "/route-analysis/snapshot/{analysis_id}/export/pdf",
    summary="Export Route Analysis Snapshot as PDF",
)
async def export_route_analysis_snapshot_pdf(
    analysis_id: str,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenPayload = Depends(require_authenticated_user),
):
    """
    Renders an executive, evidence-backed PDF representation of an immutable
    RouteAnalysisSnapshot. Preserves 100% numerical and decision parity with the database.
    """
    try:
        a_uuid = uuid.UUID(analysis_id)
    except ValueError as exc:
        raise DomainValidationError("Invalid analysis_id UUID format") from exc

    snapshot = await RouteAnalysisOrchestrationService.get_snapshot_by_id(session, a_uuid)
    if not snapshot:
        raise RecordNotFoundError(f"Route analysis snapshot '{analysis_id}' not found")

    user_name = claims.username if claims and hasattr(claims, "username") else (claims.sub if claims else "SYSTEM")
    canonical_report = await RouteAnalysisReportHandler.build_canonical_report_from_snapshot(
        session=session,
        snapshot=snapshot,
        requested_by=user_name,
    )

    pdf_bytes = RouteAnalysisPDFRenderer.render(canonical_report)
    filename = f"route_analysis_{analysis_id[:8]}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "X-Content-Type-Options": "nosniff",
        },
    )


@dispatch_analysis_router.get(
    "/route-analysis/maps-config",
    summary="Get Google Maps JS Client Configuration",
)
async def get_maps_config(
    claims: Optional[TokenPayload] = Depends(get_optional_user_claims),
):
    """
    Returns public Google Maps JavaScript API client configuration for interactive map rendering.
    Only returns the browser Maps JS key, never exposing the backend Routes API server key.
    """
    maps_js_key = settings.GOOGLE_MAPS_JS_API_KEY or ""
    return {
        "success": True,
        "maps_api_key": maps_js_key,
        "is_configured": bool(maps_js_key),
    }



@dispatch_analysis_router.get(
    "/route-analysis/tm-incident-access/plants",
    response_model=OperationalPlantsListResponseDTO,
    summary="Get Operational Goa Plants for Incident Access Evaluation",
)
async def get_operational_plants_for_incident_access(
    session: AsyncSession = Depends(get_db_session),
    claims: Optional[TokenPayload] = Depends(get_optional_user_claims),
):
    """
    Returns the authoritative operational Goa plants with coordinates for incident access routing.
    """
    plants = await RouteAnalysisOrchestrationService.resolve_operational_plants(session)
    plant_dtos = [
        OperationalPlantInfoDTO(
            plant_id=str(getattr(p, "id", "") or (p.get("plant_id") if isinstance(p, dict) else "")),
            plant_code=str(getattr(p, "code", "") or (p.get("plant_code") if isinstance(p, dict) else "")),
            plant_name=str(getattr(p, "name", "") or (p.get("plant_name") if isinstance(p, dict) else "")),
            latitude=float(getattr(p, "latitude", 0.0) or (p.get("latitude") if isinstance(p, dict) else 0.0)),
            longitude=float(getattr(p, "longitude", 0.0) or (p.get("longitude") if isinstance(p, dict) else 0.0)),
            is_active=bool(getattr(p, "is_active", True) if not isinstance(p, dict) else p.get("is_active", True)),
            location_type="PLANT",
        )
        for p in plants
    ]
    return OperationalPlantsListResponseDTO(
        success=True,
        total_plants=len(plant_dtos),
        plants=plant_dtos,
    )


@dispatch_analysis_router.post(
    "/route-analysis/tm-incident-access",
    response_model=TMIncidentAccessResponseDTO,
    summary="Evaluate Current-Traffic Plant Access for TM Incident / Stuck Location",
)
async def evaluate_tm_incident_access(
    request: TMIncidentAccessExecutionRequestDTO,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenPayload = Depends(require_authenticated_user),
):
    """
    Evaluates current-traffic road access from all 4 authoritative Goa operational plants
    to an operator-reported TM incident location. Ranks candidate plants strictly by shortest
    Google Routes current road ETA. Persists an immutable snapshot with context TM_INCIDENT_ACCESS.
    """
    user_name = claims.username if claims and hasattr(claims, "username") and claims.username else (claims.sub if claims else "OPERATOR")
    
    result = await RouteAnalysisOrchestrationService.execute_tm_incident_access_analysis(
        session=session,
        request_dto=request,
        operator_username=user_name,
    )
    
    return TMIncidentAccessResponseDTO(
        success=True,
        data=result,
    )


@dispatch_analysis_router.get(
    "/route-analysis/tm-incident-access/{analysis_id}",
    response_model=TMIncidentAccessResponseDTO,
    summary="Get Persisted TM Incident Access Analysis Snapshot",
)
async def get_tm_incident_access_snapshot(
    analysis_id: str,
    session: AsyncSession = Depends(get_db_session),
    claims: TokenPayload = Depends(require_authenticated_user),
):
    """
    Retrieves a persisted TM Incident Access analysis snapshot by UUID.
    """
    try:
        a_uuid = uuid.UUID(analysis_id)
    except ValueError as exc:
        raise DomainValidationError("Invalid analysis_id UUID format") from exc

    snapshot = await RouteAnalysisOrchestrationService.get_snapshot_by_id(session, a_uuid)
    if not snapshot or snapshot.analysis_context != "TM_INCIDENT_ACCESS":
        raise RecordNotFoundError(f"TM incident access snapshot '{analysis_id}' not found")

    raw_payload = snapshot.raw_synthesis_payload or {}
    data_dict = raw_payload.get("data", raw_payload)
    result_dto = TMIncidentAccessResultDTO(**data_dict)

    return TMIncidentAccessResponseDTO(
        success=True,
        data=result_dto,
    )


@dispatch_analysis_router.get(
    "/route-analysis/api-usage",
    response_model=GoogleApiUsageResponseDTO,
    summary="Get Google Maps and Routes API Usage and Allowance Telemetry",
)
async def get_google_api_usage_summary(
    session: AsyncSession = Depends(get_db_session),
    claims: Optional[TokenPayload] = Depends(get_optional_user_claims),
):
    """
    Returns monthly Google Maps & Routes API billable consumption, remaining free-tier allowance,
    cache-hit cost savings, and financial estimates.
    """
    summary = await GoogleApiUsageService.get_monthly_usage_summary(session)
    return GoogleApiUsageResponseDTO(
        success=True,
        data=summary,
    )

