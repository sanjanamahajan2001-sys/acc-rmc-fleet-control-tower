"""
WS-ROUT-4: Route Analysis Orchestration Service
Coordinates:
- Master entity & coordinate validation (Plant, Site, Customer)
- Governed candidate plant resolution
- WS-ROUT-1: Historical ERP T1 transit statistics
- WS-ROUT-2: Google Routes API v2 traffic evidence
- WS-ROUT-3: 2D Synthesis Recommendation Engine
- WS-ROUT-4: Immutable snapshot persistence in route_analysis_snapshots
"""

import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    RecordNotFoundError,
    DomainValidationError,
)
from app.core.logging import get_logger
from app.modules.erp.models import Customer, Dispatch, Plant, Site
from app.modules.operational_dashboard.models.route_analysis import RouteAnalysisSnapshot
from app.modules.operational_dashboard.widgets.dispatch_analysis.dtos import (
    RouteAnalysisMode,
    RouteAnalysisExecutionRequestDTO,
    RouteAnalysisSnapshotResponseDTO,
    RouteAnalysisHistoryResponseDTO,
    RouteAnalysisSynthesisResultDTO,
    SynthesisDecisionOutcome,
    SynthesisCaseCategory,
    HistoricalTransitEvidenceSummaryDTO,
    GoogleRouteEvidenceSummaryDTO,
    GoogleDetailedRouteDTO,
    TMIncidentAccessExecutionRequestDTO,
    TMIncidentAccessResultDTO,
    TMIncidentDecisionState,
    PlantIncidentAccessItemDTO,
    OperationalPlantInfoDTO,
)
from app.modules.operational_dashboard.widgets.dispatch_analysis.services.google_routes_client import (
    GoogleRoutesProvider,
    IRouteProvider,
)
from app.modules.operational_dashboard.widgets.dispatch_analysis.services.synthesis_engine import (
    DeterministicExplanationGenerator,
    RouteAnalysisSynthesisEngine,
)
from app.modules.operational_dashboard.widgets.dispatch_analysis.services import (
    HistoricalRouteEvidenceService,
)

logger = get_logger("app.route_analysis_service")


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in kilometers between two GPS coordinates (unrounded high-precision)."""
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class RouteAnalysisOrchestrationService:
    """
    Authoritative Orchestration Service for Route Analysis.
    Strict Invariants:
    1. Decision support only (zero automatic rerouting / dispatch).
    2. Zero live truck GPS / availability simulation.
    3. Zero fake / mock operational data in production.
    4. Immutable snapshot audit persistence.
    """

    MAX_CANDIDATE_RADIUS_KM: float = 60.0
    MAX_CANDIDATE_PLANTS_LIMIT: int = 4

    @classmethod
    async def execute_analysis(
        cls,
        session: AsyncSession,
        request_dto: RouteAnalysisExecutionRequestDTO,
        user_id: Optional[uuid.UUID] = None,
        google_provider: Optional[IRouteProvider] = None,
        persist_snapshot: bool = True,
    ) -> RouteAnalysisSynthesisResultDTO:
        """
        Executes end-to-end route analysis and transactionally persists an immutable snapshot when persist_snapshot=True.
        """
        analysis_id = str(uuid.uuid4())
        analysis_dt = datetime.now(timezone.utc)
        engine_version = "v1.2.1"
        policy_version = "ROUTE_POLICY_v1.2.1"

        # 1. Resolve Customer & Site Entities
        customer_obj: Optional[Customer] = None
        if request_dto.customer_id:
            try:
                cust_uuid = uuid.UUID(request_dto.customer_id)
                stmt = select(Customer).where(Customer.id == cust_uuid, Customer.is_deleted == False)
                customer_obj = (await session.execute(stmt)).scalars().first()
            except ValueError:
                stmt = select(Customer).where(Customer.code == request_dto.customer_id, Customer.is_deleted == False)
                customer_obj = (await session.execute(stmt)).scalars().first()

        site_obj: Optional[Site] = None
        try:
            site_uuid = uuid.UUID(request_dto.site_id)
            stmt = select(Site).where(Site.id == site_uuid, Site.is_deleted == False)
            site_obj = (await session.execute(stmt)).scalars().first()
        except ValueError:
            stmt = select(Site).where(Site.code == request_dto.site_id, Site.is_deleted == False)
            site_obj = (await session.execute(stmt)).scalars().first()

        if not site_obj:
            raise RecordNotFoundError(f"Destination site '{request_dto.site_id}' not found in master database")

        # 2. Resolve Current Source Plant
        current_plant_obj: Optional[Plant] = None
        if request_dto.current_source_plant_id:
            try:
                p_uuid = uuid.UUID(request_dto.current_source_plant_id)
                stmt = select(Plant).where(Plant.id == p_uuid, Plant.is_deleted == False)
                current_plant_obj = (await session.execute(stmt)).scalars().first()
            except ValueError:
                stmt = select(Plant).where(Plant.code == request_dto.current_source_plant_id, Plant.is_deleted == False)
                current_plant_obj = (await session.execute(stmt)).scalars().first()

        if not current_plant_obj:
            # Fall back to site's assigned primary plant_id
            stmt = select(Plant).where(Plant.id == site_obj.plant_id, Plant.is_deleted == False)
            current_plant_obj = (await session.execute(stmt)).scalars().first()

        if not current_plant_obj:
            raise RecordNotFoundError(f"No valid source plant assigned or resolvable for site '{site_obj.code}'")

        # 3. Resolve Governed Candidate Plants
        all_plants_stmt = select(Plant).where(Plant.is_deleted == False)
        all_plants = (await session.execute(all_plants_stmt)).scalars().all()

        candidate_plants: List[Dict[str, Any]] = []
        for plant in all_plants:
            if plant.id == current_plant_obj.id:
                continue
            # Filter out synthetic test fixture plants (e.g. PLANT_A_*)
            if plant.code and plant.code.startswith('PLANT_'):
                continue
            if (
                site_obj.latitude is not None
                and site_obj.longitude is not None
                and plant.latitude is not None
                and plant.longitude is not None
            ):
                dist = haversine_km(site_obj.latitude, site_obj.longitude, plant.latitude, plant.longitude)
                if dist <= cls.MAX_CANDIDATE_RADIUS_KM:
                    candidate_plants.append({
                        "plant_id": str(plant.id),
                        "plant_code": plant.code,
                        "plant_name": plant.name,
                        "latitude": plant.latitude,
                        "longitude": plant.longitude,
                        "distance_km": dist,
                    })
            else:
                candidate_plants.append({
                    "plant_id": str(plant.id),
                    "plant_code": plant.code,
                    "plant_name": plant.name,
                    "latitude": plant.latitude,
                    "longitude": plant.longitude,
                    "distance_km": None,
                })

        candidate_plants.sort(key=lambda x: x["distance_km"] if x["distance_km"] is not None else 9999.0)
        candidate_plants = candidate_plants[: cls.MAX_CANDIDATE_PLANTS_LIMIT]

        # 4. Check Master Coordinate Validity Gate
        has_valid_site_coords = (
            site_obj.latitude is not None
            and site_obj.longitude is not None
            and -90.0 <= site_obj.latitude <= 90.0
            and -180.0 <= site_obj.longitude <= 180.0
        )
        has_valid_curr_plant_coords = (
            current_plant_obj.latitude is not None
            and current_plant_obj.longitude is not None
            and -90.0 <= current_plant_obj.latitude <= 90.0
            and -180.0 <= current_plant_obj.longitude <= 180.0
        )

        provider = google_provider or GoogleRoutesProvider()

        if not has_valid_site_coords or not has_valid_curr_plant_coords:
            # LOCATION_DATA_MISSING Outcome
            expl = DeterministicExplanationGenerator.generate_explanation(
                case_category=SynthesisCaseCategory.C11_COORDINATES_MISSING,
                curr_plant_code=current_plant_obj.code,
                alt_plant_code="",
                delta_route_min=None,
                delta_hist_min=None,
                curr_traffic_delay_min=None,
                alt_traffic_delay_min=None,
                curr_p50_min=None,
                alt_p50_min=None,
                curr_sample_count=0,
                alt_sample_count=0,
            )

            result_dto = RouteAnalysisSynthesisResultDTO(
                analysis_id=analysis_id,
                site_id=str(site_obj.id),
                site_code=site_obj.code,
                site_name=site_obj.name,
                current_source_plant_id=str(current_plant_obj.id),
                current_source_plant_code=current_plant_obj.code,
                current_source_plant_name=current_plant_obj.name,
                recommended_plant_id=None,
                recommended_plant_code=None,
                recommended_plant_name=None,
                recommendation_status=SynthesisDecisionOutcome.LOCATION_DATA_MISSING,
                primary_case_category=SynthesisCaseCategory.C11_COORDINATES_MISSING,
                is_traffic_override=False,
                decision_reason_summary=expl,
                minutes_saved=None,
                engine_version=engine_version,
                policy_version=policy_version,
                analysis_mode=request_dto.analysis_mode,
                requested_departure_time=request_dto.planned_departure_time.isoformat() if request_dto.planned_departure_time else None,
                analysis_timestamp=analysis_dt.isoformat(),
                is_google_fresh=False,
                is_google_stale_cache=False,
                google_cache_age_seconds=0.0,
                is_historical_sufficient=False,
                comparisons=[],
                historical_evidence=None,
                google_evidence=None,
                detailed_route=None,
                failure_reason_code="LOCATION_DATA_MISSING",
            )

            if persist_snapshot:
                await cls._persist_snapshot(
                    session=session,
                    result=result_dto,
                    customer_id=customer_obj.id if customer_obj else None,
                    plant_id=current_plant_obj.id,
                    user_id=user_id,
                    operator_notes=request_dto.operator_notes,
                    analysis_context=request_dto.analysis_context,
                )
            return result_dto

        # 5. Fetch WS-ROUT-1 Historical Evidence
        cand_pids = [uuid.UUID(c["plant_id"]) for c in candidate_plants]
        hist_summary = await HistoricalRouteEvidenceService.get_historical_transit_evidence(
            session=session,
            site_id=site_obj.id,
            current_source_plant_id=current_plant_obj.id,
            candidate_plant_ids=cand_pids,
            analysis_timestamp=analysis_dt,
        )

        # 6. Fetch WS-ROUT-2 Google Routes Evidence
        plant_origins = [
            {
                "plant_id": str(current_plant_obj.id),
                "plant_code": current_plant_obj.code,
                "latitude": current_plant_obj.latitude,
                "longitude": current_plant_obj.longitude,
            }
        ]
        for c in candidate_plants:
            if c.get("latitude") is not None and c.get("longitude") is not None:
                plant_origins.append({
                    "plant_id": c["plant_id"],
                    "plant_code": c["plant_code"],
                    "latitude": c["latitude"],
                    "longitude": c["longitude"],
                })

        google_summary = await provider.get_route_evidence(
            origins=plant_origins,
            destination={
                "site_id": str(site_obj.id),
                "site_code": site_obj.code,
                "latitude": site_obj.latitude,
                "longitude": site_obj.longitude,
            },
            mode=request_dto.analysis_mode,
            departure_time=request_dto.planned_departure_time,
            fetch_detailed_for_plant_ids=[str(current_plant_obj.id)] + [c["plant_id"] for c in candidate_plants],
            force_refresh=request_dto.force_refresh,
        )

        # 7. Execute WS-ROUT-3 Synthesis
        synthesis_result = RouteAnalysisSynthesisEngine.synthesize_multi_candidate_decision(
            analysis_id=analysis_id,
            site_id=str(site_obj.id),
            site_code=site_obj.code,
            site_name=site_obj.name,
            current_plant_id=str(current_plant_obj.id),
            current_plant_code=current_plant_obj.code,
            current_plant_name=current_plant_obj.name,
            candidate_plants=candidate_plants,
            historical_summary=hist_summary,
            google_summary=google_summary,
            detailed_route=None,
            mode=request_dto.analysis_mode,
            requested_departure_time=request_dto.planned_departure_time,
            analysis_timestamp=analysis_dt,
        )

        # Attach detailed route if available in provider summary
        if synthesis_result.recommended_plant_id and synthesis_result.recommended_plant_id in google_summary.detailed_routes:
            synthesis_result.detailed_route = google_summary.detailed_routes[synthesis_result.recommended_plant_id]

        # 8. Persist Immutable Snapshot
        if persist_snapshot:
            await cls._persist_snapshot(
                session=session,
                result=synthesis_result,
                customer_id=customer_obj.id if customer_obj else None,
                plant_id=current_plant_obj.id,
                user_id=user_id,
                operator_notes=request_dto.operator_notes,
                analysis_context=request_dto.analysis_context,
            )

        return synthesis_result

    @classmethod
    async def _persist_snapshot(
        cls,
        session: AsyncSession,
        result: RouteAnalysisSynthesisResultDTO,
        customer_id: Optional[uuid.UUID] = None,
        plant_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        operator_notes: Optional[str] = None,
        analysis_context: Optional[str] = None,
    ) -> RouteAnalysisSnapshot:
        """
        Persists immutable snapshot to PostgreSQL route_analysis_snapshots table.
        """
        analysis_uuid = uuid.UUID(result.analysis_id)
        site_uuid = uuid.UUID(result.site_id) if result.site_id else None
        curr_plant_uuid = uuid.UUID(result.current_source_plant_id) if result.current_source_plant_id else None
        rec_plant_uuid = uuid.UUID(result.recommended_plant_id) if result.recommended_plant_id else None

        hist_payload = result.historical_evidence.model_dump() if result.historical_evidence else {}
        google_payload = result.google_evidence.model_dump() if result.google_evidence else {}
        matrix_payload = [c.model_dump() for c in result.comparisons]

        # Latest ERP batch lineage if discoverable by plant_id
        erp_batch_id: Optional[uuid.UUID] = None
        if plant_id:
            latest_dispatch_stmt = (
                select(Dispatch.import_batch_id)
                .where(Dispatch.plant_id == plant_id)
                .order_by(desc(Dispatch.dispatch_date))
                .limit(1)
            )
            erp_batch_id = (await session.execute(latest_dispatch_stmt)).scalar()

        snapshot = RouteAnalysisSnapshot(
            analysis_id=analysis_uuid,
            customer_id=customer_id,
            site_id=site_uuid,
            current_source_plant_id=curr_plant_uuid,
            recommended_plant_id=rec_plant_uuid,
            recommendation_status=result.recommendation_status.value,
            failure_reason_code=result.failure_reason_code,
            analysis_mode=result.analysis_mode.value,
            planned_departure_time=datetime.fromisoformat(result.requested_departure_time) if result.requested_departure_time else None,
            engine_version=result.engine_version,
            policy_version=result.policy_version,
            decision_reason_summary=result.decision_reason_summary,
            analysis_context=analysis_context or "ROUTINE",
            operator_notes=operator_notes,
            erp_import_batch_id=erp_batch_id,
            historical_evidence_payload=hist_payload,
            google_evidence_payload=google_payload,
            candidate_comparison_matrix=matrix_payload,
            google_queried_at=datetime.fromisoformat(result.google_evidence.response_timestamp) if result.google_evidence else None,
            data_freshness_seconds=int(result.google_cache_age_seconds),
            is_cached_result=result.google_evidence.is_stale_cache or (result.google_cache_age_seconds > 0) if result.google_evidence else False,
            created_by=user_id,
        )

        session.add(snapshot)
        await session.commit()
        await session.refresh(snapshot)
        return snapshot

    @classmethod
    async def get_snapshot_by_id(
        cls,
        session: AsyncSession,
        analysis_id: uuid.UUID,
    ) -> Optional[RouteAnalysisSnapshot]:
        """Retrieves an immutable snapshot record by analysis ID."""
        stmt = select(RouteAnalysisSnapshot).where(RouteAnalysisSnapshot.analysis_id == analysis_id)
        return (await session.execute(stmt)).scalars().first()

    @classmethod
    async def resolve_operational_plants(
        cls,
        session: AsyncSession,
    ) -> List[Plant]:
        """
        Resolves canonical active Goa operational plants strictly from authoritative master data:
        ACC_VASCO, ACC_KUNDAIM, ACC_DHARGA, ACC_NESSAI.
        Excludes synthetic/test fixture plants.
        """
        stmt = (
            select(Plant)
            .where(
                Plant.is_deleted == False,
                Plant.code.in_(["ACC_VASCO", "ACC_KUNDAIM", "ACC_DHARGA", "ACC_NESSAI"]),
            )
            .order_by(Plant.code)
        )
        plants = list((await session.execute(stmt)).scalars().all())
        return plants

    @classmethod
    async def execute_tm_incident_access_analysis(
        cls,
        session: AsyncSession,
        request_dto: TMIncidentAccessExecutionRequestDTO,
        operator_username: str,
        user_id: Optional[uuid.UUID] = None,
        google_provider: Optional[IRouteProvider] = None,
    ) -> TMIncidentAccessResultDTO:
        """
        Executes TM Incident / Stuck TM Current-Traffic Decision Support across the 4 authoritative Goa plants.
        Strict Contract Invariants:
        1. Decision Support Only (Zero live truck tracking, zero truck reservation, zero automatic dispatch).
        2. Location is operator-reported only (Validated strictly, never fabricated or geocoded from arbitrary text).
        3. Authoritative 4 operational plants resolved from DB master tables (ACC_VASCO, ACC_KUNDAIM, ACC_DHARGA, ACC_NESSAI).
        4. Primary ranking by current Google road ETA (not crow-fly distance).
        5. Origin x Destination cache isolation with 300s freshness invariant.
        6. Persists immutable audit snapshot with analysis_context = 'TM_INCIDENT_ACCESS'.
        """
        analysis_id = str(uuid.uuid4())
        analysis_dt = datetime.now(timezone.utc)
        engine_version = "v1.2.1"
        policy_version = "INCIDENT_POLICY_v1.0.0"

        # 1. Validate Operator-Reported Coordinates
        lat = request_dto.reported_latitude
        lng = request_dto.reported_longitude

        if lat is None or lng is None or math.isnan(lat) or math.isnan(lng) or math.isinf(lat) or math.isinf(lng):
            raise DomainValidationError("Operator-reported incident coordinates must be valid finite numbers")

        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lng <= 180.0):
            raise DomainValidationError(f"Operator-reported coordinates out of range: ({lat}, {lng})")

        # 2. Resolve Authoritative Operational Plants
        operational_plants = await cls.resolve_operational_plants(session)
        if not operational_plants:
            result_dto = TMIncidentAccessResultDTO(
                analysis_id=analysis_id,
                analysis_context="TM_INCIDENT_ACCESS",
                incident_type=request_dto.incident_type,
                reported_latitude=lat,
                reported_longitude=lng,
                reported_location_name=request_dto.reported_location_name,
                reported_timestamp=request_dto.reported_timestamp.isoformat() if request_dto.reported_timestamp else None,
                analysis_timestamp=analysis_dt.isoformat(),
                dispatch_reference=request_dto.dispatch_reference,
                vehicle_reference=request_dto.vehicle_reference,
                operator_notes=request_dto.operator_notes,
                operator_identity=operator_username,
                best_access_plant_id=None,
                best_access_plant_code=None,
                best_access_plant_name=None,
                best_access_eta_minutes=None,
                best_access_distance_km=None,
                best_access_traffic_delay_minutes=None,
                decision_state=TMIncidentDecisionState.NO_OPERATIONAL_PLANTS_AVAILABLE,
                decision_summary="No operational master plants found in database.",
                historical_evidence_status="INSUFFICIENT_NO_INCIDENT_BASELINE",
                is_google_fresh=False,
                is_google_stale_cache=False,
                google_cache_age_seconds=0.0,
                candidate_access_matrix=[],
                engine_version=engine_version,
                policy_version=policy_version,
            )
            return result_dto

        # Check plant coordinate validity
        valid_plants: List[Plant] = []
        for p in operational_plants:
            if (
                p.latitude is not None
                and p.longitude is not None
                and -90.0 <= p.latitude <= 90.0
                and -180.0 <= p.longitude <= 180.0
            ):
                valid_plants.append(p)

        if len(valid_plants) < len(operational_plants):
            logger.warning(
                "Some operational plants have missing or invalid master coordinates",
                total=len(operational_plants),
                valid=len(valid_plants),
            )

        # 3. Query Google Routes API v2
        provider = google_provider or GoogleRoutesProvider()

        origins = [
            {
                "plant_id": str(p.id),
                "plant_code": p.code,
                "latitude": p.latitude,
                "longitude": p.longitude,
            }
            for p in valid_plants
        ]
        destination = {
            "site_id": f"INCIDENT_{lat:.4f}_{lng:.4f}",
            "site_code": "REPORTED_INCIDENT_LOC",
            "latitude": lat,
            "longitude": lng,
        }

        fetch_detailed_pids = [str(p.id) for p in valid_plants]

        google_summary: GoogleRouteEvidenceSummaryDTO = await provider.get_route_evidence(
            origins=origins,
            destination=destination,
            mode=RouteAnalysisMode.NOW,
            departure_time=None,
            fetch_detailed_for_plant_ids=fetch_detailed_pids,
            force_refresh=request_dto.force_refresh,
        )

        # 4. Construct Candidate Access Matrix
        candidate_items: List[PlantIncidentAccessItemDTO] = []
        for p in operational_plants:
            pid_str = str(p.id)
            has_coords = (
                p.latitude is not None
                and p.longitude is not None
                and -90.0 <= p.latitude <= 90.0
                and -180.0 <= p.longitude <= 180.0
            )

            crow_fly = (
                haversine_km(p.latitude, p.longitude, lat, lng)
                if has_coords
                else 9999.0
            )

            g_item = google_summary.matrix_items.get(pid_str)
            d_route = google_summary.detailed_routes.get(pid_str)

            if not has_coords:
                candidate_items.append(
                    PlantIncidentAccessItemDTO(
                        plant_id=pid_str,
                        plant_code=p.code,
                        plant_name=p.name,
                        plant_latitude=p.latitude or 0.0,
                        plant_longitude=p.longitude or 0.0,
                        incident_latitude=lat,
                        incident_longitude=lng,
                        crow_fly_distance_km=crow_fly,
                        route_status="UNAVAILABLE",
                        failure_reason="Plant master coordinates missing or invalid",
                    )
                )
            elif crow_fly <= 0.05:  # Origin equals operator-reported incident location (within 50m tolerance)
                candidate_items.append(
                    PlantIncidentAccessItemDTO(
                        plant_id=pid_str,
                        plant_code=p.code,
                        plant_name=p.name,
                        plant_latitude=p.latitude,
                        plant_longitude=p.longitude,
                        incident_latitude=lat,
                        incident_longitude=lng,
                        crow_fly_distance_km=0.0,
                        road_distance_km=0.0,
                        duration_minutes=0.0,
                        static_duration_minutes=0.0,
                        traffic_delay_minutes=0.0,
                        route_status="ORIGIN_EQUALS_DESTINATION",
                        google_queried_at=google_summary.response_timestamp,
                        provider_response_at=google_summary.response_timestamp,
                        cache_age_seconds=0.0,
                        is_cached_result=False,
                        is_stale=False,
                        detailed_route=d_route or GoogleDetailedRouteDTO(
                            plant_id=pid_str,
                            plant_code=p.code,
                            site_id="INCIDENT",
                            site_code="TM_INCIDENT",
                            encoded_polyline="",
                            duration_seconds=0,
                            duration_minutes=0.0,
                            static_duration_seconds=0,
                            static_duration_minutes=0.0,
                            traffic_delay_minutes=0.0,
                            distance_meters=0,
                            distance_km=0.0,
                            speed_reading_intervals=[],
                        ),
                    )
                )
            elif g_item and g_item.status in ("OK", "0", ""):
                candidate_items.append(
                    PlantIncidentAccessItemDTO(
                        plant_id=pid_str,
                        plant_code=p.code,
                        plant_name=p.name,
                        plant_latitude=p.latitude,
                        plant_longitude=p.longitude,
                        incident_latitude=lat,
                        incident_longitude=lng,
                        crow_fly_distance_km=crow_fly,
                        road_distance_km=g_item.distance_km,
                        duration_minutes=g_item.duration_minutes,
                        static_duration_minutes=g_item.static_duration_minutes,
                        traffic_delay_minutes=g_item.traffic_delay_minutes,
                        route_status="OK",
                        google_queried_at=google_summary.response_timestamp,
                        provider_response_at=google_summary.response_timestamp,
                        cache_age_seconds=google_summary.cache_age_seconds,
                        is_cached_result=google_summary.is_stale_cache or (google_summary.cache_age_seconds > 0),
                        is_stale=google_summary.is_stale_cache or (google_summary.cache_age_seconds > 300),
                        detailed_route=d_route,
                    )
                )
            else:
                candidate_items.append(
                    PlantIncidentAccessItemDTO(
                        plant_id=pid_str,
                        plant_code=p.code,
                        plant_name=p.name,
                        plant_latitude=p.latitude,
                        plant_longitude=p.longitude,
                        incident_latitude=lat,
                        incident_longitude=lng,
                        crow_fly_distance_km=crow_fly,
                        route_status="UNAVAILABLE",
                        failure_reason=g_item.error_message if g_item else (google_summary.failure_reason or "Route not found or unroutable"),
                        google_queried_at=google_summary.response_timestamp,
                        cache_age_seconds=google_summary.cache_age_seconds,
                        is_cached_result=google_summary.is_stale_cache or (google_summary.cache_age_seconds > 0),
                        is_stale=google_summary.is_stale_cache or (google_summary.cache_age_seconds > 300),
                    )
                )

        # 5. Determine Primary Ranking by Current Road ETA
        # Filter available routes with valid duration_minutes
        valid_candidates = [c for c in candidate_items if c.route_status in ("OK", "ORIGIN_EQUALS_DESTINATION") and c.duration_minutes is not None]
        # Primary sort: road duration_minutes ASC. Secondary sort: road_distance_km ASC. Tertiary sort: crow_fly ASC.
        valid_candidates.sort(key=lambda x: (x.duration_minutes if x.duration_minutes is not None else 9999.0, x.road_distance_km if x.road_distance_km is not None else 9999.0, x.crow_fly_distance_km))

        # Assign rankings
        for rank_idx, cand in enumerate(valid_candidates, start=1):
            cand.ranking = rank_idx

        # Assign remaining unavailable candidates
        unavail_candidates = [c for c in candidate_items if c.route_status not in ("OK", "ORIGIN_EQUALS_DESTINATION") or c.duration_minutes is None]
        unavail_candidates.sort(key=lambda x: x.crow_fly_distance_km)

        # Re-assemble all candidate items with best access winner tagged
        best_candidate: Optional[PlantIncidentAccessItemDTO] = valid_candidates[0] if valid_candidates else None
        if best_candidate and not google_summary.is_stale_cache:
            best_candidate.is_best_access = True

        # 6. Formulate Decision State and Summary
        decision_state: TMIncidentDecisionState
        decision_summary: str

        if google_summary.is_stale_cache or (google_summary.cache_age_seconds > 300 and not google_summary.is_fresh):
            decision_state = TMIncidentDecisionState.TRAFFIC_EVIDENCE_STALE
            decision_summary = (
                f"Google traffic evidence is stale ({int(google_summary.cache_age_seconds)}s age). "
                "Stale route estimates are displayed for informational reference only. No current-traffic recommendation can be made."
            )
        elif not valid_candidates:
            decision_state = TMIncidentDecisionState.NO_CURRENT_ROUTE_EVIDENCE
            decision_summary = "No valid current road route could be calculated from operational plants to the reported incident location."
        elif len(valid_candidates) < len(operational_plants):
            decision_state = TMIncidentDecisionState.PARTIAL_ROUTE_EVIDENCE
            eta_str = f"{best_candidate.duration_minutes:.1f}" if best_candidate.duration_minutes is not None else "N/A"
            dist_str = f"{best_candidate.road_distance_km:.1f}" if best_candidate.road_distance_km is not None else "N/A"
            decision_summary = (
                f"BEST CURRENT ACCESS — Plant {best_candidate.plant_code}: "
                f"Based on the operator-reported incident location and current Google route estimates, "
                f"Plant {best_candidate.plant_code} currently has the shortest estimated road travel time ({eta_str} mins, {dist_str} km). "
                f"Note: Candidate route evidence was unavailable for {len(operational_plants) - len(valid_candidates)} plant(s)."
            )
        else:
            decision_state = TMIncidentDecisionState.BEST_CURRENT_ACCESS
            eta_str = f"{best_candidate.duration_minutes:.1f}" if best_candidate.duration_minutes is not None else "N/A"
            dist_str = f"{best_candidate.road_distance_km:.1f}" if best_candidate.road_distance_km is not None else "N/A"
            delay_str = f"+{best_candidate.traffic_delay_minutes:.1f}" if best_candidate.traffic_delay_minutes else "+0.0"
            decision_summary = (
                f"BEST CURRENT ACCESS — Plant {best_candidate.plant_code}: "
                f"Based on the operator-reported incident location and current Google route estimates, "
                f"Plant {best_candidate.plant_code} currently has the shortest estimated road travel time to the reported incident location "
                f"({eta_str} mins, {dist_str} km, {delay_str} mins traffic delay)."
            )

        # 7. Assemble Full Result DTO
        result_dto = TMIncidentAccessResultDTO(
            analysis_id=analysis_id,
            analysis_context="TM_INCIDENT_ACCESS",
            incident_type=request_dto.incident_type,
            reported_latitude=lat,
            reported_longitude=lng,
            reported_location_name=request_dto.reported_location_name,
            reported_timestamp=request_dto.reported_timestamp.isoformat() if request_dto.reported_timestamp else None,
            analysis_timestamp=analysis_dt.isoformat(),
            dispatch_reference=request_dto.dispatch_reference,
            vehicle_reference=request_dto.vehicle_reference,
            operator_notes=request_dto.operator_notes,
            operator_identity=operator_username,
            best_access_plant_id=best_candidate.plant_id if (best_candidate and decision_state in (TMIncidentDecisionState.BEST_CURRENT_ACCESS, TMIncidentDecisionState.PARTIAL_ROUTE_EVIDENCE)) else None,
            best_access_plant_code=best_candidate.plant_code if (best_candidate and decision_state in (TMIncidentDecisionState.BEST_CURRENT_ACCESS, TMIncidentDecisionState.PARTIAL_ROUTE_EVIDENCE)) else None,
            best_access_plant_name=best_candidate.plant_name if (best_candidate and decision_state in (TMIncidentDecisionState.BEST_CURRENT_ACCESS, TMIncidentDecisionState.PARTIAL_ROUTE_EVIDENCE)) else None,
            best_access_eta_minutes=best_candidate.duration_minutes if (best_candidate and decision_state in (TMIncidentDecisionState.BEST_CURRENT_ACCESS, TMIncidentDecisionState.PARTIAL_ROUTE_EVIDENCE)) else None,
            best_access_distance_km=best_candidate.road_distance_km if (best_candidate and decision_state in (TMIncidentDecisionState.BEST_CURRENT_ACCESS, TMIncidentDecisionState.PARTIAL_ROUTE_EVIDENCE)) else None,
            best_access_traffic_delay_minutes=best_candidate.traffic_delay_minutes if (best_candidate and decision_state in (TMIncidentDecisionState.BEST_CURRENT_ACCESS, TMIncidentDecisionState.PARTIAL_ROUTE_EVIDENCE)) else None,
            decision_state=decision_state,
            decision_summary=decision_summary,
            historical_evidence_status="INSUFFICIENT_NO_INCIDENT_BASELINE",
            is_google_fresh=google_summary.is_fresh,
            is_google_stale_cache=google_summary.is_stale_cache,
            google_cache_age_seconds=google_summary.cache_age_seconds,
            google_queried_at=google_summary.response_timestamp,
            candidate_access_matrix=(valid_candidates + unavail_candidates),
            engine_version=engine_version,
            policy_version=policy_version,
        )

        # 8. Persist Immutable Audit Snapshot
        await cls._persist_tm_incident_snapshot(
            session=session,
            result=result_dto,
            user_id=user_id,
        )

        return result_dto

    @classmethod
    async def _persist_tm_incident_snapshot(
        cls,
        session: AsyncSession,
        result: TMIncidentAccessResultDTO,
        user_id: Optional[uuid.UUID] = None,
    ) -> RouteAnalysisSnapshot:
        """
        Persists immutable audit snapshot specifically for TM Incident Access analysis.
        Lineage includes operator_reported coordinates, dispatch/vehicle references, and full Google route evidence.
        """
        analysis_uuid = uuid.UUID(result.analysis_id)
        best_plant_uuid = uuid.UUID(result.best_access_plant_id) if result.best_access_plant_id else None

        matrix_payload = [c.model_dump() for c in result.candidate_access_matrix]

        google_payload = {
            "provider_name": "GOOGLE_ROUTES_V2",
            "is_fresh": result.is_google_fresh,
            "is_stale_cache": result.is_google_stale_cache,
            "cache_age_seconds": result.google_cache_age_seconds,
            "response_timestamp": result.google_queried_at,
        }

        lineage_payload = {
            "incident_type": result.incident_type,
            "reported_latitude": result.reported_latitude,
            "reported_longitude": result.reported_longitude,
            "reported_location_name": result.reported_location_name,
            "reported_timestamp": result.reported_timestamp,
            "dispatch_reference": result.dispatch_reference,
            "vehicle_reference": result.vehicle_reference,
            "operator_identity": result.operator_identity,
            "operational_advisory": result.operational_advisory,
        }

        snapshot = RouteAnalysisSnapshot(
            analysis_id=analysis_uuid,
            customer_id=None,
            site_id=None,
            current_source_plant_id=None,
            recommended_plant_id=best_plant_uuid,
            recommendation_status=result.decision_state.value,
            failure_reason_code=None if result.decision_state in (TMIncidentDecisionState.BEST_CURRENT_ACCESS, TMIncidentDecisionState.PARTIAL_ROUTE_EVIDENCE) else result.decision_state.value,
            analysis_mode="NOW",
            planned_departure_time=None,
            engine_version=result.engine_version,
            policy_version=result.policy_version,
            decision_reason_summary=result.decision_summary,
            analysis_context="TM_INCIDENT_ACCESS",
            operator_notes=result.operator_notes,
            erp_import_batch_id=None,
            historical_evidence_payload={
                "status": result.historical_evidence_status,
                "note": "Incident coordinates are operator-reported; no historical T1 baseline exists.",
            },
            google_evidence_payload=google_payload,
            candidate_comparison_matrix=matrix_payload,
            google_queried_at=datetime.fromisoformat(result.google_queried_at) if result.google_queried_at else None,
            data_freshness_seconds=int(result.google_cache_age_seconds),
            is_cached_result=result.is_google_stale_cache or (result.google_cache_age_seconds > 0),
            source_lineage=lineage_payload,
            created_by=user_id,
        )

        session.add(snapshot)
        await session.commit()
        await session.refresh(snapshot)
        return snapshot


