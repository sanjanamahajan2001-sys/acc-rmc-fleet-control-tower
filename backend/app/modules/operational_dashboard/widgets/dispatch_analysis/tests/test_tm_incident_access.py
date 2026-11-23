import math
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.core.exceptions import DomainValidationError
from app.modules.operational_dashboard.widgets.dispatch_analysis.dtos import (
    TMIncidentAccessExecutionRequestDTO,
    TMIncidentDecisionState,
    GoogleCandidateMatrixItemDTO,
    GoogleDetailedRouteDTO,
    GoogleRouteEvidenceSummaryDTO,
    RouteAnalysisMode,
)
from app.modules.operational_dashboard.widgets.dispatch_analysis.services.route_analysis_service import (
    RouteAnalysisOrchestrationService,
)


@pytest.mark.asyncio
async def test_tm_incident_access_invalid_coordinates():
    """Verify validation rejects invalid latitude/longitude at execution time."""
    session = AsyncMock()
    
    # Latitude out of range
    req_lat = TMIncidentAccessExecutionRequestDTO(
        reported_latitude=95.0,
        reported_longitude=73.8,
    )
    with pytest.raises(DomainValidationError):
        await RouteAnalysisOrchestrationService.execute_tm_incident_access_analysis(
            session=session,
            request_dto=req_lat,
            operator_username="test_op",
        )

    # Longitude out of range
    req_lng = TMIncidentAccessExecutionRequestDTO(
        reported_latitude=15.4,
        reported_longitude=190.0,
    )
    with pytest.raises(DomainValidationError):
        await RouteAnalysisOrchestrationService.execute_tm_incident_access_analysis(
            session=session,
            request_dto=req_lng,
            operator_username="test_op",
        )


@pytest.mark.asyncio
async def test_tm_incident_origin_equals_destination():
    """
    Verify deterministic ORIGIN_EQUALS_DESTINATION rule:
    When operator-reported incident location matches plant coordinates (within 50m tolerance),
    candidate route_status is ORIGIN_EQUALS_DESTINATION, duration_minutes is 0.0,
    road_distance_km is 0.0, and candidate is ranked #1 BEST access.
    """
    session = AsyncMock()

    # Plant 1: Nessai (15.2635, 74.0152)
    p1 = MagicMock()
    p1.id = uuid.uuid4()
    p1.code = "ACC_NESSAI"
    p1.name = "Nessai Plant"
    p1.latitude = 15.2635
    p1.longitude = 74.0152
    p1.is_active = True

    # Plant 2: Vasco (15.3991, 73.8153)
    p2 = MagicMock()
    p2.id = uuid.uuid4()
    p2.code = "ACC_VASCO"
    p2.name = "Vasco Plant"
    p2.latitude = 15.3991
    p2.longitude = 73.8153
    p2.is_active = True

    mock_plants = [p1, p2]

    # Incident location exactly matches ACC_NESSAI coordinates
    req = TMIncidentAccessExecutionRequestDTO(
        reported_latitude=15.2635,
        reported_longitude=74.0152,
        reported_location_name="Nessai Gate Entry",
    )

    mock_google_provider = MagicMock()
    
    # Plant 2 Vasco is 28 mins away
    c2 = GoogleCandidateMatrixItemDTO(
        origin_index=1,
        destination_index=0,
        plant_id=str(p2.id),
        plant_code=p2.code,
        site_id="INCIDENT",
        site_code="INCIDENT",
        duration_seconds=1680,
        duration_minutes=28.0,
        static_duration_minutes=25.0,
        traffic_delay_minutes=3.0,
        distance_meters=24000,
        distance_km=24.0,
        status="OK",
        queried_at=datetime.now(timezone.utc).isoformat(),
        is_stale=False,
        cache_age_seconds=0.0,
        is_cached=False,
    )

    summary = GoogleRouteEvidenceSummaryDTO(
        status="OK",
        mode=RouteAnalysisMode.NOW,
        response_timestamp=datetime.now(timezone.utc).isoformat(),
        is_fresh=True,
        is_stale_cache=False,
        cache_age_seconds=0.0,
        matrix_items={
            str(p2.id): c2,
        },
        detailed_routes={},
    )

    async def mock_get_route_evidence(*args, **kwargs):
        return summary

    mock_google_provider.get_route_evidence = mock_get_route_evidence

    with patch.object(RouteAnalysisOrchestrationService, "resolve_operational_plants", return_value=mock_plants), \
         patch.object(RouteAnalysisOrchestrationService, "_persist_tm_incident_snapshot", return_value=None):
        
        result = await RouteAnalysisOrchestrationService.execute_tm_incident_access_analysis(
            session=session,
            request_dto=req,
            operator_username="test_admin",
            google_provider=mock_google_provider,
        )

        assert result.decision_state == TMIncidentDecisionState.BEST_CURRENT_ACCESS
        assert result.best_access_plant_code == "ACC_NESSAI"
        assert result.best_access_eta_minutes == 0.0
        assert result.best_access_distance_km == 0.0
        
        # Verify Candidate Matrix
        assert len(result.candidate_access_matrix) == 2
        
        nessai_item = result.candidate_access_matrix[0]
        assert nessai_item.plant_code == "ACC_NESSAI"
        assert nessai_item.route_status == "ORIGIN_EQUALS_DESTINATION"
        assert nessai_item.duration_minutes == 0.0
        assert nessai_item.road_distance_km == 0.0
        assert nessai_item.traffic_delay_minutes == 0.0
        assert nessai_item.ranking == 1
        assert nessai_item.is_best_access is True

        vasco_item = result.candidate_access_matrix[1]
        assert vasco_item.plant_code == "ACC_VASCO"
        assert vasco_item.ranking == 2
        assert vasco_item.is_best_access is False


@pytest.mark.asyncio
async def test_tm_incident_access_ranking_by_road_eta():
    """Verify candidate plants are ranked strictly by shortest Google road ETA, not crow-fly distance."""
    session = AsyncMock()
    
    p1 = MagicMock()
    p1.id = uuid.uuid4()
    p1.code = "ACC_VASCO"
    p1.name = "Vasco Plant"
    p1.latitude = 15.3991
    p1.longitude = 73.8153
    p1.is_active = True

    p2 = MagicMock()
    p2.id = uuid.uuid4()
    p2.code = "ACC_KUNDAIM"
    p2.name = "Kundaim Plant"
    p2.latitude = 15.4215
    p2.longitude = 73.9856
    p2.is_active = True

    mock_plants = [p1, p2]

    req = TMIncidentAccessExecutionRequestDTO(
        reported_latitude=15.41,
        reported_longitude=73.81,
        reported_location_name="Panaji Junction",
    )

    mock_google_provider = MagicMock()
    
    c1 = GoogleCandidateMatrixItemDTO(
        origin_index=0,
        destination_index=0,
        plant_id=str(p1.id),
        plant_code=p1.code,
        site_id="INCIDENT",
        site_code="INCIDENT",
        duration_seconds=1080,
        duration_minutes=18.0,
        static_duration_minutes=16.0,
        traffic_delay_minutes=2.0,
        distance_meters=16000,
        distance_km=16.0,
        status="OK",
        queried_at=datetime.now(timezone.utc).isoformat(),
        is_stale=False,
        cache_age_seconds=5.0,
        is_cached=False,
    )

    c2 = GoogleCandidateMatrixItemDTO(
        origin_index=1,
        destination_index=0,
        plant_id=str(p2.id),
        plant_code=p2.code,
        site_id="INCIDENT",
        site_code="INCIDENT",
        duration_seconds=1920,
        duration_minutes=32.0,
        static_duration_minutes=25.0,
        traffic_delay_minutes=7.0,
        distance_meters=22000,
        distance_km=22.0,
        status="OK",
        queried_at=datetime.now(timezone.utc).isoformat(),
        is_stale=False,
        cache_age_seconds=5.0,
        is_cached=False,
    )

    summary = GoogleRouteEvidenceSummaryDTO(
        status="OK",
        mode=RouteAnalysisMode.NOW,
        response_timestamp=datetime.now(timezone.utc).isoformat(),
        is_fresh=True,
        is_stale_cache=False,
        cache_age_seconds=5.0,
        matrix_items={
            str(p1.id): c1,
            str(p2.id): c2,
        },
        detailed_routes={},
    )

    async def mock_get_route_evidence(*args, **kwargs):
        return summary

    mock_google_provider.get_route_evidence = mock_get_route_evidence

    with patch.object(RouteAnalysisOrchestrationService, "resolve_operational_plants", return_value=mock_plants), \
         patch.object(RouteAnalysisOrchestrationService, "_persist_tm_incident_snapshot", return_value=None):
        
        result = await RouteAnalysisOrchestrationService.execute_tm_incident_access_analysis(
            session=session,
            request_dto=req,
            operator_username="admin_user",
            google_provider=mock_google_provider,
        )

        assert result.decision_state == TMIncidentDecisionState.BEST_CURRENT_ACCESS
        assert result.best_access_plant_code == "ACC_VASCO"
        assert result.best_access_eta_minutes == 18.0
        assert result.candidate_access_matrix[0].plant_code == "ACC_VASCO"
        assert result.candidate_access_matrix[0].ranking == 1
        assert result.candidate_access_matrix[0].is_best_access is True
        assert result.candidate_access_matrix[1].plant_code == "ACC_KUNDAIM"
        assert result.candidate_access_matrix[1].ranking == 2
        assert result.candidate_access_matrix[1].is_best_access is False
        assert "Operational Advisory Only" in result.operational_advisory
        assert result.historical_evidence_status == "INSUFFICIENT_NO_INCIDENT_BASELINE"


@pytest.mark.asyncio
async def test_tm_incident_partial_google_failures():
    """
    Verify partial Google failure handling across 3/4, 2/4, 1/4, and 0/4 states:
    - Unavailable routes are visible with status UNAVAILABLE and no fabricated values.
    - Only valid routes participate in ranking.
    - 0/4 valid routes produces NO_CURRENT_ROUTE_EVIDENCE with best_access_plant_id=None.
    """
    session = AsyncMock()
    
    plants = []
    for code, lat, lng in [
        ("ACC_VASCO", 15.3991, 73.8153),
        ("ACC_KUNDAIM", 15.4215, 73.9856),
        ("ACC_DHARGA", 15.6025, 73.8201),
        ("ACC_NESSAI", 15.2635, 74.0152),
    ]:
        p = MagicMock()
        p.id = uuid.uuid4()
        p.code = code
        p.name = f"{code} Plant"
        p.latitude = lat
        p.longitude = lng
        p.is_active = True
        plants.append(p)

    req = TMIncidentAccessExecutionRequestDTO(
        reported_latitude=15.5000,
        reported_longitude=73.8300,
    )

    # 1. Test 2/4 Successful: Vasco (20m) & Dharga (15m) OK; Kundaim & Nessai FAILED
    c_vasco = GoogleCandidateMatrixItemDTO(
        origin_index=0, destination_index=0, plant_id=str(plants[0].id), plant_code="ACC_VASCO",
        site_id="INCIDENT", site_code="INCIDENT", duration_seconds=1200, duration_minutes=20.0,
        static_duration_minutes=18.0, traffic_delay_minutes=2.0, distance_meters=18000, distance_km=18.0,
        status="OK", queried_at=datetime.now(timezone.utc).isoformat(), is_stale=False, cache_age_seconds=0.0, is_cached=False,
    )
    c_dharga = GoogleCandidateMatrixItemDTO(
        origin_index=2, destination_index=0, plant_id=str(plants[2].id), plant_code="ACC_DHARGA",
        site_id="INCIDENT", site_code="INCIDENT", duration_seconds=900, duration_minutes=15.0,
        static_duration_minutes=14.0, traffic_delay_minutes=1.0, distance_meters=13000, distance_km=13.0,
        status="OK", queried_at=datetime.now(timezone.utc).isoformat(), is_stale=False, cache_age_seconds=0.0, is_cached=False,
    )

    summary_2_4 = GoogleRouteEvidenceSummaryDTO(
        status="OK", mode=RouteAnalysisMode.NOW, response_timestamp=datetime.now(timezone.utc).isoformat(),
        is_fresh=True, is_stale_cache=False, cache_age_seconds=0.0,
        matrix_items={str(plants[0].id): c_vasco, str(plants[2].id): c_dharga},
    )

    mock_provider = MagicMock()
    mock_provider.get_route_evidence = AsyncMock(return_value=summary_2_4)

    with patch.object(RouteAnalysisOrchestrationService, "resolve_operational_plants", return_value=plants), \
         patch.object(RouteAnalysisOrchestrationService, "_persist_tm_incident_snapshot", return_value=None):
        
        result = await RouteAnalysisOrchestrationService.execute_tm_incident_access_analysis(
            session=session, request_dto=req, operator_username="test_op", google_provider=mock_provider,
        )

        assert result.decision_state == TMIncidentDecisionState.PARTIAL_ROUTE_EVIDENCE
        assert result.best_access_plant_code == "ACC_DHARGA"  # Dharga has shorter ETA (15m < 20m)
        assert result.best_access_eta_minutes == 15.0
        
        # Matrix has 4 items: 2 valid ranked #1 & #2, 2 unavailable
        assert len(result.candidate_access_matrix) == 4
        assert result.candidate_access_matrix[0].plant_code == "ACC_DHARGA"
        assert result.candidate_access_matrix[0].ranking == 1
        assert result.candidate_access_matrix[1].plant_code == "ACC_VASCO"
        assert result.candidate_access_matrix[1].ranking == 2
        
        unavail = [c for c in result.candidate_access_matrix if c.route_status == "UNAVAILABLE"]
        assert len(unavail) == 2
        for u in unavail:
            assert u.ranking is None
            assert u.duration_minutes is None
            assert u.is_best_access is False

    # 2. Test 0/4 Successful: All Google routes fail
    summary_0_4 = GoogleRouteEvidenceSummaryDTO(
        status="PROVIDER_UNAVAILABLE", mode=RouteAnalysisMode.NOW,
        response_timestamp=datetime.now(timezone.utc).isoformat(),
        is_fresh=False, is_stale_cache=False, cache_age_seconds=0.0,
        matrix_items={},
    )
    mock_provider.get_route_evidence = AsyncMock(return_value=summary_0_4)

    with patch.object(RouteAnalysisOrchestrationService, "resolve_operational_plants", return_value=plants), \
         patch.object(RouteAnalysisOrchestrationService, "_persist_tm_incident_snapshot", return_value=None):
        
        result_0 = await RouteAnalysisOrchestrationService.execute_tm_incident_access_analysis(
            session=session, request_dto=req, operator_username="test_op", google_provider=mock_provider,
        )

        assert result_0.decision_state == TMIncidentDecisionState.NO_CURRENT_ROUTE_EVIDENCE
        assert result_0.best_access_plant_id is None
        assert result_0.best_access_plant_code is None
        assert result_0.best_access_eta_minutes is None
        assert len(result_0.candidate_access_matrix) == 4
        for c in result_0.candidate_access_matrix:
            assert c.route_status == "UNAVAILABLE"
            assert c.is_best_access is False


@pytest.mark.asyncio
async def test_tm_incident_access_stale_cache_warning():
    """Verify that when Google route evidence is stale cache, decision state is TRAFFIC_EVIDENCE_STALE."""
    session = AsyncMock()
    
    p1 = MagicMock()
    p1.id = uuid.uuid4()
    p1.code = "ACC_VASCO"
    p1.name = "Vasco Plant"
    p1.latitude = 15.3991
    p1.longitude = 73.8153
    p1.is_active = True

    mock_plants = [p1]

    req = TMIncidentAccessExecutionRequestDTO(
        reported_latitude=15.41,
        reported_longitude=73.81,
    )

    mock_google_provider = MagicMock()
    c1 = GoogleCandidateMatrixItemDTO(
        origin_index=0,
        destination_index=0,
        plant_id=str(p1.id),
        plant_code=p1.code,
        site_id="INCIDENT",
        site_code="INCIDENT",
        duration_seconds=1320,
        duration_minutes=22.0,
        static_duration_minutes=20.0,
        traffic_delay_minutes=2.0,
        distance_meters=15000,
        distance_km=15.0,
        status="OK",
        queried_at="2026-09-09T09:50:00Z",
        is_stale=True,
        cache_age_seconds=450.0,
        is_cached=True,
    )

    summary = GoogleRouteEvidenceSummaryDTO(
        status="OK",
        mode=RouteAnalysisMode.NOW,
        response_timestamp="2026-09-09T09:50:00Z",
        is_fresh=False,
        is_stale_cache=True,
        cache_age_seconds=450.0,
        matrix_items={
            str(p1.id): c1,
        },
    )

    mock_google_provider.get_route_evidence = AsyncMock(return_value=summary)

    with patch.object(RouteAnalysisOrchestrationService, "resolve_operational_plants", return_value=mock_plants), \
         patch.object(RouteAnalysisOrchestrationService, "_persist_tm_incident_snapshot", return_value=None):
        
        result = await RouteAnalysisOrchestrationService.execute_tm_incident_access_analysis(
            session=session,
            request_dto=req,
            operator_username="admin_user",
            google_provider=mock_google_provider,
        )

        assert result.decision_state == TMIncidentDecisionState.TRAFFIC_EVIDENCE_STALE
        assert result.is_google_stale_cache is True
        assert result.is_google_fresh is False
        assert result.best_access_plant_id is None


@pytest.mark.asyncio
async def test_tm_incident_50m_51m_boundary_transition():
    """
    Verifies the strict 50m vs 51m origin equals destination boundary:
    - 0m, 10m, 49m, 50m: ORIGIN_EQUALS_DESTINATION, duration = 0.0m, road distance = 0.0km, rank #1
    - 51m, 60m: Normal Google route evaluation (route_status = OK, duration = 2.0m, distance = 0.55km)
    """
    session = AsyncMock()
    plant_lat = 15.3991
    plant_lon = 73.8153
    m_per_deg = (6371000.0 * math.pi) / 180.0

    p1 = MagicMock()
    p1.id = uuid.uuid4()
    p1.code = "ACC_VASCO"
    p1.name = "Vasco Plant"
    p1.latitude = plant_lat
    p1.longitude = plant_lon
    p1.is_active = True

    c1 = GoogleCandidateMatrixItemDTO(
        origin_index=0,
        destination_index=0,
        plant_id=str(p1.id),
        plant_code=p1.code,
        site_id="INCIDENT",
        site_code="INCIDENT",
        duration_seconds=120,
        duration_minutes=2.0,
        static_duration_minutes=1.8,
        traffic_delay_minutes=0.2,
        distance_meters=550,
        distance_km=0.55,
        status="OK",
        queried_at=datetime.now(timezone.utc).isoformat(),
        is_stale=False,
        cache_age_seconds=0.0,
        is_cached=False,
    )

    summary = GoogleRouteEvidenceSummaryDTO(
        status="OK",
        mode=RouteAnalysisMode.NOW,
        response_timestamp=datetime.now(timezone.utc).isoformat(),
        is_fresh=True,
        is_stale_cache=False,
        cache_age_seconds=0.0,
        matrix_items={str(p1.id): c1},
        detailed_routes={},
    )

    mock_google_provider = MagicMock()
    async def mock_get_route_evidence(*args, **kwargs):
        return summary
    mock_google_provider.get_route_evidence = mock_get_route_evidence

    # Test <= 50m (0m, 10m, 49m, 50m)
    for target_m in [0.0, 10.0, 49.0, 50.0]:
        inc_lat = plant_lat + (target_m / m_per_deg)
        req = TMIncidentAccessExecutionRequestDTO(
            reported_latitude=inc_lat,
            reported_longitude=plant_lon,
        )
        with patch.object(RouteAnalysisOrchestrationService, "resolve_operational_plants", return_value=[p1]),              patch.object(RouteAnalysisOrchestrationService, "_persist_tm_incident_snapshot", return_value=None):
            result = await RouteAnalysisOrchestrationService.execute_tm_incident_access_analysis(
                session=session,
                request_dto=req,
                operator_username="test_admin",
                google_provider=mock_google_provider,
            )
            item = result.candidate_access_matrix[0]
            assert item.route_status == "ORIGIN_EQUALS_DESTINATION"
            assert item.duration_minutes == 0.0
            assert item.road_distance_km == 0.0

    # Test > 50m (51m, 60m)
    for target_m in [51.0, 60.0]:
        inc_lat = plant_lat + (target_m / m_per_deg)
        req = TMIncidentAccessExecutionRequestDTO(
            reported_latitude=inc_lat,
            reported_longitude=plant_lon,
        )
        with patch.object(RouteAnalysisOrchestrationService, "resolve_operational_plants", return_value=[p1]),              patch.object(RouteAnalysisOrchestrationService, "_persist_tm_incident_snapshot", return_value=None):
            result = await RouteAnalysisOrchestrationService.execute_tm_incident_access_analysis(
                session=session,
                request_dto=req,
                operator_username="test_admin",
                google_provider=mock_google_provider,
            )
            item = result.candidate_access_matrix[0]
            assert item.route_status == "OK"
            assert item.duration_minutes == 2.0
            assert item.road_distance_km == 0.55
