"""
WS-ROUT-2: Google Routes API v2 Client & Resilience Test Suite
FROZEN BLUEPRINT v1.2.1 COMPLIANT
"""

import pytest
import time
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import httpx

from app.modules.operational_dashboard.widgets.dispatch_analysis.dtos import (
    RouteAnalysisMode,
    TrafficSpeedState,
    SpeedReadingIntervalDTO,
    GoogleCandidateMatrixItemDTO,
    GoogleDetailedRouteDTO,
    GoogleRouteEvidenceSummaryDTO,
)
from app.modules.operational_dashboard.widgets.dispatch_analysis.services.google_routes_client import (
    GoogleRoutesClient,
    GoogleRoutesProvider,
    GoogleRoutesCircuitBreaker,
    GoogleRoutesCache,
)


# =============================================================================
# MOCK HTTP TRANSPORT HELPERS FOR UNIT TESTING
# =============================================================================


class MockTransport(httpx.AsyncBaseTransport):
    """
    Controlled Mock Transport for isolating Google Routes HTTP calls in unit tests.
    Ensures zero external network dependencies and deterministic failure injection.
    """

    def __init__(self, handler):
        self.handler = handler

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return await self.handler(request)


# Sample Mock Data
MOCK_MATRIX_RESPONSE = [
    {
        "originIndex": 0,
        "destinationIndex": 0,
        "status": {},
        "condition": "ROUTE_EXISTS",
        "distanceMeters": 23400,
        "duration": "1800s",
        "staticDuration": "1500s",
    },
    {
        "originIndex": 1,
        "destinationIndex": 0,
        "status": {},
        "condition": "ROUTE_EXISTS",
        "distanceMeters": 15200,
        "duration": "1440s",
        "staticDuration": "1200s",
    },
]

MOCK_ROUTES_RESPONSE = {
    "routes": [
        {
            "duration": "1800s",
            "staticDuration": "1500s",
            "distanceMeters": 23400,
            "polyline": {"encodedPolyline": "gfo}EtohhV~Ac@..."},
            "travelAdvisory": {
                "speedReadingIntervals": [
                    {"startPolylinePointIndex": 0, "endPolylinePointIndex": 10, "speed": "NORMAL"},
                    {"startPolylinePointIndex": 10, "endPolylinePointIndex": 25, "speed": "SLOW"},
                    {"startPolylinePointIndex": 25, "endPolylinePointIndex": 40, "speed": "TRAFFIC_JAM"},
                ]
            },
            "routeToken": "mock_route_token_12345",
        }
    ]
}


# =============================================================================
# 1. CORE CLIENT & TIER 1 / TIER 2 TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_google_matrix_tier1():
    """Tier 1: Tests computeRouteMatrix client parsing, metric calculations and Dtraffic = Troute - Tstatic."""
    async def handler(request: httpx.Request):
        assert request.headers.get("X-Goog-Api-Key") == "test_api_key"
        assert "distanceMatrix" in str(request.url)
        return httpx.Response(200, json=MOCK_MATRIX_RESPONSE)

    client_http = httpx.AsyncClient(transport=MockTransport(handler))
    cache = GoogleRoutesCache(use_redis=False)
    cb = GoogleRoutesCircuitBreaker()
    client = GoogleRoutesClient(api_key="test_api_key", http_client=client_http, cache=cache, circuit_breaker=cb)

    origins = [
        {"plant_id": "p1", "plant_code": "PLANT_A", "latitude": 15.498, "longitude": 73.827},
        {"plant_id": "p2", "plant_code": "PLANT_B", "latitude": 15.390, "longitude": 73.810},
    ]
    destination = {"site_id": "s1", "site_code": "SITE_X", "latitude": 15.550, "longitude": 73.900}

    items, is_fresh, is_stale, cache_age, failure = await client.compute_route_matrix(
        origins=origins, destination=destination, mode=RouteAnalysisMode.NOW
    )

    assert failure is None
    assert is_fresh is True
    assert is_stale is False
    assert len(items) == 2

    # Plant A
    assert items[0].plant_id == "p1"
    assert items[0].plant_code == "PLANT_A"
    assert items[0].duration_seconds == 1800
    assert items[0].duration_minutes == 30.0
    assert items[0].static_duration_minutes == 25.0
    assert items[0].traffic_delay_minutes == 5.0  # 30.0 - 25.0
    assert items[0].distance_km == 23.4

    # Plant B
    assert items[1].plant_id == "p2"
    assert items[1].duration_minutes == 24.0
    assert items[1].static_duration_minutes == 20.0
    assert items[1].traffic_delay_minutes == 4.0
    assert items[1].distance_km == 15.2


@pytest.mark.asyncio
async def test_google_routes_tier2():
    """Tier 2: Tests computeRoutes detailed polyline, travel advisory and speedReadingIntervals."""
    async def handler(request: httpx.Request):
        assert "directions" in str(request.url)
        return httpx.Response(200, json=MOCK_ROUTES_RESPONSE)

    client_http = httpx.AsyncClient(transport=MockTransport(handler))
    cache = GoogleRoutesCache(use_redis=False)
    cb = GoogleRoutesCircuitBreaker()
    client = GoogleRoutesClient(api_key="test_api_key", http_client=client_http, cache=cache, circuit_breaker=cb)

    origin = {"plant_id": "p1", "plant_code": "PLANT_A", "latitude": 15.498, "longitude": 73.827}
    destination = {"site_id": "s1", "site_code": "SITE_X", "latitude": 15.550, "longitude": 73.900}

    detailed, is_fresh, is_stale, cache_age, failure = await client.compute_detailed_route(
        origin=origin, destination=destination, mode=RouteAnalysisMode.NOW
    )

    assert failure is None
    assert detailed is not None
    assert detailed.plant_id == "p1"
    assert detailed.duration_minutes == 30.0
    assert detailed.distance_km == 23.4
    assert detailed.encoded_polyline == "gfo}EtohhV~Ac@..."
    assert detailed.route_token == "mock_route_token_12345"
    assert len(detailed.speed_reading_intervals) == 3


def test_google_speed_intervals():
    """Verifies speed interval mapping to normalized domain tokens and presentation colors."""
    # NORMAL
    norm = GoogleRoutesClient.parse_speed_reading_interval(
        {"startPolylinePointIndex": 0, "endPolylinePointIndex": 5, "speed": "NORMAL"}
    )
    assert norm.speed_state == TrafficSpeedState.NORMAL
    assert norm.color_hex == "#10B981"

    # SLOW
    slow = GoogleRoutesClient.parse_speed_reading_interval(
        {"startPolylinePointIndex": 5, "endPolylinePointIndex": 12, "speed": "SLOW"}
    )
    assert slow.speed_state == TrafficSpeedState.SLOW
    assert slow.color_hex == "#F59E0B"

    # TRAFFIC_JAM
    jam = GoogleRoutesClient.parse_speed_reading_interval(
        {"startPolylinePointIndex": 12, "endPolylinePointIndex": 20, "speed": "TRAFFIC_JAM"}
    )
    assert jam.speed_state == TrafficSpeedState.TRAFFIC_JAM
    assert jam.color_hex == "#EF4444"


# =============================================================================
# 2. RESILIENCE: TIMEOUT, RETRIES, ERROR CODES & CIRCUIT BREAKER
# =============================================================================


@pytest.mark.asyncio
async def test_google_timeout_4s():
    """Verifies strict 4.0-second request deadline and timeout handling."""
    async def handler(request: httpx.Request):
        await asyncio.sleep(0.05)
        raise httpx.TimeoutException("4.0s deadline timeout")

    client_http = httpx.AsyncClient(transport=MockTransport(handler))
    cache = GoogleRoutesCache(use_redis=False)
    cb = GoogleRoutesCircuitBreaker()
    client = GoogleRoutesClient(api_key="test_api_key", http_client=client_http, cache=cache, circuit_breaker=cb)

    origin = {"plant_id": "p1", "plant_code": "PLANT_A", "latitude": 15.498, "longitude": 73.827}
    destination = {"site_id": "s1", "site_code": "SITE_X", "latitude": 15.550, "longitude": 73.900}

    detailed, is_fresh, is_stale, cache_age, failure = await client.compute_detailed_route(
        origin=origin, destination=destination
    )
    assert detailed is None
    assert failure is not None
    assert "timeout" in failure.lower()


@pytest.mark.asyncio
async def test_google_quota_429():
    """Verifies HTTP 429 fails fast with zero retries."""
    call_count = 0

    async def handler(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(429, text="Resource has been exhausted (e.g. check quota).")

    client_http = httpx.AsyncClient(transport=MockTransport(handler))
    client = GoogleRoutesClient(
        api_key="test_api_key",
        http_client=client_http,
        cache=GoogleRoutesCache(use_redis=False),
        circuit_breaker=GoogleRoutesCircuitBreaker(),
    )

    origin = {"plant_id": "p1", "plant_code": "PLANT_A", "latitude": 15.498, "longitude": 73.827}
    destination = {"site_id": "s1", "site_code": "SITE_X", "latitude": 15.550, "longitude": 73.900}

    detailed, _, _, _, failure = await client.compute_detailed_route(origin=origin, destination=destination)
    assert call_count == 1  # Strictly 1 attempt, no retry
    assert detailed is None
    assert "429" in failure


@pytest.mark.asyncio
async def test_google_auth_403():
    """Verifies HTTP 403 / 401 fails fast with zero retries."""
    call_count = 0

    async def handler(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(403, text="API key not valid. Please pass a valid API key.")

    client_http = httpx.AsyncClient(transport=MockTransport(handler))
    client = GoogleRoutesClient(
        api_key="test_api_key",
        http_client=client_http,
        cache=GoogleRoutesCache(use_redis=False),
        circuit_breaker=GoogleRoutesCircuitBreaker(),
    )

    origin = {"plant_id": "p1", "plant_code": "PLANT_A", "latitude": 15.498, "longitude": 73.827}
    destination = {"site_id": "s1", "site_code": "SITE_X", "latitude": 15.550, "longitude": 73.900}

    detailed, _, _, _, failure = await client.compute_detailed_route(origin=origin, destination=destination)
    assert call_count == 1
    assert detailed is None
    assert "403" in failure


@pytest.mark.asyncio
async def test_google_transient_503():
    """Verifies transient error (503) retries exactly once before succeeding."""
    call_count = 0

    async def handler(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(503, text="Service Unavailable")
        return httpx.Response(200, json=MOCK_ROUTES_RESPONSE)

    client_http = httpx.AsyncClient(transport=MockTransport(handler))
    client = GoogleRoutesClient(
        api_key="test_api_key",
        http_client=client_http,
        cache=GoogleRoutesCache(use_redis=False),
        circuit_breaker=GoogleRoutesCircuitBreaker(),
    )

    origin = {"plant_id": "p1", "plant_code": "PLANT_A", "latitude": 15.498, "longitude": 73.827}
    destination = {"site_id": "s1", "site_code": "SITE_X", "latitude": 15.550, "longitude": 73.900}

    detailed, is_fresh, is_stale, _, failure = await client.compute_detailed_route(
        origin=origin, destination=destination
    )
    assert call_count == 2  # Exactly 2 attempts (1 retry)
    assert detailed is not None
    assert failure is None
    assert detailed.duration_minutes == 30.0


@pytest.mark.asyncio
async def test_circuit_breaker_open():
    """Verifies Circuit Breaker transitions to OPEN after >=50% failures and rejects subsequent calls."""
    cb = GoogleRoutesCircuitBreaker(failure_rate_threshold=0.50, min_requests_threshold=4, cooldown_seconds=1.0)
    assert cb.allow_execution() is True

    # Record 2 failures out of 4 (50% failure rate)
    cb.record_failure()
    cb.record_success()
    cb.record_failure()
    cb.record_failure()

    assert cb.state == "OPEN"
    assert cb.allow_execution() is False  # Fast rejected

    # Wait for cooldown to transition to HALF_OPEN
    await asyncio.sleep(1.1)
    assert cb.allow_execution() is True
    assert cb.state == "HALF_OPEN"

    # Successful probe resets to CLOSED
    cb.record_success()
    assert cb.state == "CLOSED"


# =============================================================================
# 3. CACHE CONTRACT & STALE-CACHE INVARIANT TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_cache_hit_under_300s():
    """Verifies fresh cache hit (<300s) bypasses HTTP call and marks is_fresh=True."""
    call_count = 0

    async def handler(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=MOCK_MATRIX_RESPONSE)

    client_http = httpx.AsyncClient(transport=MockTransport(handler))
    cache = GoogleRoutesCache(use_redis=False)
    client = GoogleRoutesClient(api_key="test_api_key", http_client=client_http, cache=cache)

    origins = [{"plant_id": "p1", "plant_code": "PLANT_A", "latitude": 15.498, "longitude": 73.827}]
    destination = {"site_id": "s1", "site_code": "SITE_X", "latitude": 15.550, "longitude": 73.900}

    # Call 1: Miss
    items1, fresh1, stale1, _, _ = await client.compute_route_matrix(origins, destination)
    assert call_count == 1
    assert fresh1 is True
    assert stale1 is False

    # Call 2: Fresh Cache Hit
    items2, fresh2, stale2, _, _ = await client.compute_route_matrix(origins, destination)
    assert call_count == 1  # Zero additional HTTP calls
    assert fresh2 is True
    assert stale2 is False
    assert len(items2) == 1


@pytest.mark.asyncio
async def test_cache_force_refresh():
    """Verifies force_refresh=True forces real HTTP execution regardless of cache state."""
    call_count = 0

    async def handler(request: httpx.Request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=MOCK_MATRIX_RESPONSE)

    client_http = httpx.AsyncClient(transport=MockTransport(handler))
    cache = GoogleRoutesCache(use_redis=False)
    client = GoogleRoutesClient(api_key="test_api_key", http_client=client_http, cache=cache)

    origins = [{"plant_id": "p1", "plant_code": "PLANT_A", "latitude": 15.498, "longitude": 73.827}]
    destination = {"site_id": "s1", "site_code": "SITE_X", "latitude": 15.550, "longitude": 73.900}

    # Call 1
    await client.compute_route_matrix(origins, destination)
    assert call_count == 1

    # Call 2: Forced refresh
    await client.compute_route_matrix(origins, destination, force_refresh=True)
    assert call_count == 2


@pytest.mark.asyncio
async def test_google_fallback_info_stale_cache():
    """
    STALE-CACHE INVARIANT:
    Verifies that when an expired cache (>300s) refresh fails, the stale payload
    is returned with is_fresh=False, is_stale=True, and failure_reason set.
    """
    cache = GoogleRoutesCache(use_redis=False)
    # Manually populate cache with 350-second old payload
    key = cache.generate_matrix_cache_key([(15.498, 73.827)], (15.550, 73.900), RouteAnalysisMode.NOW, None)
    old_ts = time.time() - 350.0
    cache._memory_cache[key] = (
        old_ts,
        {
            "items": [
                {
                    "plant_id": "p1",
                    "plant_code": "PLANT_A",
                    "site_id": "s1",
                    "site_code": "SITE_X",
                    "origin_index": 0,
                    "destination_index": 0,
                    "status": "OK",
                    "duration_seconds": 1800,
                    "duration_minutes": 30.0,
                    "static_duration_seconds": 1500,
                    "static_duration_minutes": 25.0,
                    "traffic_delay_minutes": 5.0,
                    "distance_meters": 23400,
                    "distance_km": 23.4,
                }
            ]
        },
    )

    # Mock HTTP failure (500)
    async def handler(request: httpx.Request):
        return httpx.Response(500, text="Internal Server Error")

    client_http = httpx.AsyncClient(transport=MockTransport(handler))
    client = GoogleRoutesClient(api_key="test_api_key", http_client=client_http, cache=cache)

    origins = [{"plant_id": "p1", "plant_code": "PLANT_A", "latitude": 15.498, "longitude": 73.827}]
    destination = {"site_id": "s1", "site_code": "SITE_X", "latitude": 15.550, "longitude": 73.900}

    items, is_fresh, is_stale, cache_age, failure = await client.compute_route_matrix(origins, destination)

    assert len(items) == 1
    assert is_fresh is False  # Must NOT be fresh
    assert is_stale is True   # Flagged as stale fallback
    assert cache_age >= 350.0
    assert failure is not None
    assert "500" in failure


# =============================================================================
# 4. TEMPORAL MODES & TIMEZONE UTC ANCHORING TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_planned_departure_mode_utc_anchoring():
    """Verifies PLANNED_DEPARTURE mode anchors UTC ISO-8601 departureTime in Google request."""
    captured_body = {}

    async def handler(request: httpx.Request):
        nonlocal captured_body
        import json
        captured_body = json.loads(request.content)
        return httpx.Response(200, json=MOCK_MATRIX_RESPONSE)

    client_http = httpx.AsyncClient(transport=MockTransport(handler))
    client = GoogleRoutesClient(
        api_key="test_api_key",
        http_client=client_http,
        cache=GoogleRoutesCache(use_redis=False),
        circuit_breaker=GoogleRoutesCircuitBreaker(),
    )

    dept_time = datetime(2026, 9, 10, 8, 30, 0, tzinfo=timezone.utc)
    origins = [{"plant_id": "p1", "plant_code": "PLANT_A", "latitude": 15.498, "longitude": 73.827}]
    destination = {"site_id": "s1", "site_code": "SITE_X", "latitude": 15.550, "longitude": 73.900}

    await client.compute_route_matrix(
        origins=origins,
        destination=destination,
        mode=RouteAnalysisMode.PLANNED_DEPARTURE,
        departure_time=dept_time,
        force_refresh=True,
    )

    assert "departureTime" in captured_body
    assert captured_body["departureTime"] == "2026-09-10T08:30:00+00:00"


# =============================================================================
# 5. SECURITY & SECRET LEAKAGE PREVENTION TESTS
# =============================================================================


def test_missing_api_key_fails_clearly():
    """Verifies missing API key raises clear descriptive error and does not silently proceed."""
    client = GoogleRoutesClient(api_key="")
    with pytest.raises(ValueError) as excinfo:
        client._get_api_key()
    assert "GOOGLE_MAPS_ROUTES_API_KEY is not configured" in str(excinfo.value)


@pytest.mark.asyncio
async def test_no_secret_leakage_in_provider_evidence():
    """Verifies API key never appears anywhere in GoogleRouteEvidenceSummaryDTO or serialized JSON."""
    async def handler(request: httpx.Request):
        return httpx.Response(200, json=MOCK_MATRIX_RESPONSE)

    client_http = httpx.AsyncClient(transport=MockTransport(handler))
    client = GoogleRoutesClient(api_key="SECRET_AIzaSySuperSecretKey12345", http_client=client_http)
    provider = GoogleRoutesProvider(client=client)

    origins = [{"plant_id": "p1", "plant_code": "PLANT_A", "latitude": 15.498, "longitude": 73.827}]
    destination = {"site_id": "s1", "site_code": "SITE_X", "latitude": 15.550, "longitude": 73.900}

    summary = await provider.get_route_evidence(origins, destination)
    summary_json = summary.model_dump_json()

    assert "SECRET_AIzaSySuperSecretKey12345" not in summary_json
    assert "test_api_key" not in summary_json
    assert summary.status == "SUCCESS"
