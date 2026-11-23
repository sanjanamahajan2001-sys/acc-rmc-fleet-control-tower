"""
Google Routes API v2 Client, Resilience Layer, Multi-Tier Caching, and Route Provider
Authoritative implementation compliant with Route Analysis Decision Support Engine v1.2.1 (FROZEN).
"""

import time
import json
import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis import get_redis_client
from app.modules.operational_dashboard.widgets.dispatch_analysis.dtos import (
    RouteAnalysisMode,
    TrafficSpeedState,
    SpeedReadingIntervalDTO,
    RouteWaypointDTO,
    GoogleCandidateMatrixItemDTO,
    GoogleDetailedRouteDTO,
    GoogleRouteEvidenceSummaryDTO,
)

logger = get_logger("app.google_routes")


# =============================================================================
# 1. CIRCUIT BREAKER FOR GOOGLE ROUTES API v2
# =============================================================================


class GoogleRoutesCircuitBreaker:
    """
    Deterministic, production-safe Circuit Breaker.
    Frozen contract rules:
    - Breaker opens after failure rate reaches/exceeds 50% across rolling window (minimum sample 4 calls)
    - Cooldown reset timeout = 60.0 seconds
    - In OPEN state: fast-rejects requests and prevents cascading upstream timeouts.
    - After cooldown: transitions to HALF_OPEN to probe upstream health.
    """

    def __init__(
        self,
        failure_rate_threshold: float = 0.50,
        min_requests_threshold: int = 4,
        cooldown_seconds: float = 60.0,
    ):
        self.failure_rate_threshold = failure_rate_threshold
        self.min_requests_threshold = min_requests_threshold
        self.cooldown_seconds = cooldown_seconds
        self.state: str = "CLOSED"  # "CLOSED", "OPEN", "HALF_OPEN"
        self.total_requests: int = 0
        self.failed_requests: int = 0
        self.last_state_change: float = time.time()
        self._history: List[bool] = []  # True for success, False for failure

    def allow_execution(self) -> bool:
        now = time.time()
        if self.state == "OPEN":
            if now - self.last_state_change >= self.cooldown_seconds:
                self.state = "HALF_OPEN"
                self.last_state_change = now
                logger.info("Google Routes circuit breaker transitioned to HALF_OPEN probe state")
                return True
            return False
        return True

    def record_success(self) -> None:
        self._history.append(True)
        if len(self._history) > 20:
            self._history.pop(0)
        self.total_requests = len(self._history)
        self.failed_requests = self._history.count(False)

        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.last_state_change = time.time()
            logger.info("Google Routes circuit breaker probe successful -> reset to CLOSED")

    def record_failure(self) -> None:
        self._history.append(False)
        if len(self._history) > 20:
            self._history.pop(0)
        self.total_requests = len(self._history)
        self.failed_requests = self._history.count(False)

        if self.state == "HALF_OPEN":
            self.state = "OPEN"
            self.last_state_change = time.time()
            logger.warning("Google Routes circuit breaker probe failed -> transitioned back to OPEN")
            return

        if self.total_requests >= self.min_requests_threshold:
            rate = self.failed_requests / self.total_requests
            if rate >= self.failure_rate_threshold and self.state != "OPEN":
                self.state = "OPEN"
                self.last_state_change = time.time()
                logger.error(
                    "Google Routes circuit breaker OPENED due to high failure rate",
                    failure_rate=rate,
                    failed=self.failed_requests,
                    total=self.total_requests,
                    cooldown_seconds=self.cooldown_seconds,
                )

    def reset(self) -> None:
        self.state = "CLOSED"
        self.total_requests = 0
        self.failed_requests = 0
        self._history = []
        self.last_state_change = time.time()


# Singleton circuit breaker instance for Google Routes
google_routes_circuit_breaker = GoogleRoutesCircuitBreaker()


# =============================================================================
# 2. MULTI-TIER CACHING & STALE-CACHE INVARIANT ENGINE
# =============================================================================


class GoogleRoutesCache:
    """
    Dual-TTL Cache for Google Route Estimates.
    Frozen contract rules:
    - GOOGLE_TRAFFIC_CACHE_TTL_SECONDS = 300 (5 mins) for live/traffic-aware route matrix
    - GOOGLE_STATIC_CACHE_TTL_SECONDS = 86400 (24 hrs) for static/non-traffic geometry
    - Strict Invariant: Stale cached payload (> 300s) may only be displayed for INFORMATIONAL / AUDIT
      purposes and MUST NEVER generate or participate in a current recommendation.
    """

    TRAFFIC_CACHE_TTL_SECONDS: int = 300
    STATIC_CACHE_TTL_SECONDS: int = 86400

    def __init__(self, use_redis: bool = True):
        self.use_redis = use_redis
        self._memory_cache: Dict[str, Tuple[float, dict]] = {}  # key -> (timestamp, payload)

    @classmethod
    def generate_matrix_cache_key(
        cls,
        origin_coords: List[Tuple[float, float]],
        dest_coords: Tuple[float, float],
        mode: RouteAnalysisMode,
        departure_time: Optional[str] = None,
    ) -> str:
        origins_str = ";".join(f"{lat:.6f},{lon:.6f}" for lat, lon in origin_coords)
        dest_str = f"{dest_coords[0]:.6f},{dest_coords[1]:.6f}"
        dept_str = departure_time or "NOW"
        return f"routes:matrix:{origins_str}->{dest_str}:{mode.value}:{dept_str}"

    @classmethod
    def generate_detailed_cache_key(
        cls,
        origin_coord: Tuple[float, float],
        dest_coord: Tuple[float, float],
        mode: RouteAnalysisMode,
        departure_time: Optional[str] = None,
    ) -> str:
        orig_str = f"{origin_coord[0]:.6f},{origin_coord[1]:.6f}"
        dest_str = f"{dest_coord[0]:.6f},{dest_coord[1]:.6f}"
        dept_str = departure_time or "NOW"
        return f"routes:detailed:{orig_str}->{dest_coord[0]:.6f},{dest_coord[1]:.6f}:{mode.value}:{dept_str}"

    async def get(self, key: str) -> Tuple[Optional[dict], bool, float]:
        """
        Returns (payload, is_fresh, age_seconds).
        If not found: (None, False, 0.0)
        If found and age <= 300: (payload, True, age)
        If found and age > 300: (payload, False, age)  <-- Stale cache invariant
        """
        now = time.time()
        # 1. Check in-memory fast tier
        if key in self._memory_cache:
            ts, payload = self._memory_cache[key]
            age = now - ts
            is_fresh = (age <= self.TRAFFIC_CACHE_TTL_SECONDS)
            return payload, is_fresh, age

        # 2. Check Redis if enabled
        if self.use_redis:
            try:
                redis_client = get_redis_client()
                val = await redis_client.get(key)
                if val:
                    record = json.loads(val)
                    ts = record.get("cached_at", now)
                    payload = record.get("payload")
                    age = now - ts
                    is_fresh = (age <= self.TRAFFIC_CACHE_TTL_SECONDS)
                    self._memory_cache[key] = (ts, payload)
                    return payload, is_fresh, age
            except Exception as e:
                logger.debug("Redis cache read skipped or failed", error=str(e))

        return None, False, 0.0

    async def set(self, key: str, payload: dict, is_static: bool = False) -> None:
        now = time.time()
        self._memory_cache[key] = (now, payload)
        ttl = self.STATIC_CACHE_TTL_SECONDS if is_static else self.TRAFFIC_CACHE_TTL_SECONDS

        if self.use_redis:
            try:
                redis_client = get_redis_client()
                record = json.dumps({"cached_at": now, "payload": payload})
                # We keep in Redis for up to 86400s so stale fallback lookup is possible if Google is down
                await redis_client.set(key, record, ex=self.STATIC_CACHE_TTL_SECONDS)
            except Exception as e:
                logger.debug("Redis cache write skipped or failed", error=str(e))

    def clear(self) -> None:
        self._memory_cache.clear()


# Singleton cache instance
google_routes_cache = GoogleRoutesCache()


# =============================================================================
# 3. GOOGLE ROUTES API v2 CLIENT (HTTP TRANSPORT & RESILIENCE)
# =============================================================================


class GoogleRoutesClient:
    """
    Production Client for Google Routes API v2 (computeRouteMatrix and computeRoutes).
    Strict contract:
    - 4.0-second request deadline (timeout)
    - Transient retry (502, 503, 504) exactly once with 200ms backoff
    - Non-transient errors (400, 401, 403, 429) fail fast with zero retries
    - No secret leakage in logs or payloads
    """

    ROUTES_MATRIX_URL = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"
    ROUTES_COMPUTE_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"

    REQUEST_DEADLINE_SECONDS: float = 4.0
    MAX_CANDIDATE_PLANTS_LIMIT: int = 4

    def __init__(
        self,
        api_key: Optional[str] = None,
        circuit_breaker: Optional[GoogleRoutesCircuitBreaker] = None,
        cache: Optional[GoogleRoutesCache] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self._api_key = api_key if api_key is not None else getattr(settings, "GOOGLE_MAPS_ROUTES_API_KEY", "")
        self.circuit_breaker = circuit_breaker or GoogleRoutesCircuitBreaker()
        self.cache = cache or GoogleRoutesCache()
        self._http_client = http_client

    def _get_api_key(self) -> str:
        key = self._api_key if self._api_key is not None else getattr(settings, "GOOGLE_MAPS_ROUTES_API_KEY", "")
        if not key or not key.strip():
            raise ValueError(
                "GOOGLE_MAPS_ROUTES_API_KEY is not configured in the backend environment. "
                "Cannot initiate real Google Routes API calls."
            )
        return key.strip()

    @classmethod
    def parse_speed_reading_interval(cls, interval_dict: dict) -> SpeedReadingIntervalDTO:
        """
        Maps Google Routes speedReadingIntervals to normalized domain tokens.
        Google speed states: NORMAL, SLOW, TRAFFIC_JAM
        UI Color Mapping:
        NORMAL -> #10B981
        SLOW -> #F59E0B
        TRAFFIC_JAM -> #EF4444
        """
        speed_raw = str(interval_dict.get("speed", "NORMAL")).upper()
        if speed_raw == "SLOW":
            state = TrafficSpeedState.SLOW
            color = "#F59E0B"
        elif speed_raw in ("TRAFFIC_JAM", "JAM", "HEAVY"):
            state = TrafficSpeedState.TRAFFIC_JAM
            color = "#EF4444"
        else:
            state = TrafficSpeedState.NORMAL
            color = "#10B981"

        return SpeedReadingIntervalDTO(
            start_polyline_point_index=int(interval_dict.get("startPolylinePointIndex", 0)),
            end_polyline_point_index=int(interval_dict.get("endPolylinePointIndex", 0)),
            speed_state=state,
            color_hex=color,
        )

    @staticmethod
    async def _record_usage_telemetry(
        api_service: str,
        endpoint: str,
        request_count: int = 1,
        status_code: int = 200,
        is_cached: bool = False,
        latency_ms: float = 0.0,
    ) -> None:
        """
        Records API usage telemetry safely and asynchronously.
        Never raises or interrupts calling execution flow.
        """
        try:
            from app.core.database import AsyncSessionFactory
            from app.modules.operational_dashboard.widgets.dispatch_analysis.services.google_usage_service import (
                GoogleApiUsageService,
            )
            async with AsyncSessionFactory() as session:
                await GoogleApiUsageService.record_usage(
                    session=session,
                    api_service=api_service,
                    endpoint=endpoint,
                    request_count=request_count,
                    status_code=status_code,
                    is_cached=is_cached,
                    latency_ms=latency_ms,
                )
        except Exception as exc:
            logger.warning("Google API telemetry logging error suppressed", error=str(exc))

    async def _execute_http_request(
        self,
        url: str,
        headers: dict,
        payload: dict,
        field_mask: str,
    ) -> Tuple[int, Any]:
        """
        Executes HTTP POST request with strict 4.0s deadline and single-retry transient error policy.
        """
        api_key = self._get_api_key()
        req_headers = {
            **headers,
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": field_mask,
            "Content-Type": "application/json",
        }

        # Check circuit breaker
        if not self.circuit_breaker.allow_execution():
            logger.warning("Google Routes API call rejected by OPEN circuit breaker")
            raise RuntimeError("Circuit breaker is OPEN for Google Routes API v2")

        max_attempts = 2  # 1 initial + at most 1 retry for 502/503/504
        client = self._http_client or httpx.AsyncClient(timeout=self.REQUEST_DEADLINE_SECONDS)
        should_close_client = (self._http_client is None)

        start_time = time.time()
        last_status = 0
        last_error_text = ""

        try:
            for attempt in range(1, max_attempts + 1):
                try:
                    resp = await client.post(url, headers=req_headers, json=payload)
                    latency = round(time.time() - start_time, 3)
                    last_status = resp.status_code

                    # 1. Success (200 OK)
                    if resp.status_code == 200:
                        self.circuit_breaker.record_success()
                        logger.info(
                            "Google Routes API call succeeded",
                            endpoint=url.split("/")[-1],
                            latency_seconds=latency,
                            status_code=200,
                            attempt=attempt,
                        )
                        return 200, resp.json()

                    # 2. Non-transient errors: fail fast without retry
                    if resp.status_code in (400, 401, 403, 429):
                        self.circuit_breaker.record_failure()
                        last_error_text = resp.text
                        logger.error(
                            "Google Routes API non-transient error (no retry)",
                            status_code=resp.status_code,
                            endpoint=url.split("/")[-1],
                            attempt=attempt,
                            error_snippet=last_error_text[:200],
                        )
                        return resp.status_code, {"error": last_error_text, "status": resp.status_code}

                    # 3. Transient errors: 502, 503, 504 -> retry at most once
                    if resp.status_code in (502, 503, 504) and attempt < max_attempts:
                        logger.warning(
                            "Google Routes API transient error, scheduling single retry",
                            status_code=resp.status_code,
                            attempt=attempt,
                            backoff_ms=200,
                        )
                        await asyncio.sleep(0.2)
                        continue

                    # Unhandled status or second attempt failure
                    self.circuit_breaker.record_failure()
                    return resp.status_code, {"error": resp.text, "status": resp.status_code}

                except (httpx.TimeoutException, httpx.ConnectTimeout) as te:
                    self.circuit_breaker.record_failure()
                    logger.error(
                        "Google Routes API request timed out (4.0s deadline exceeded)",
                        endpoint=url.split("/")[-1],
                        attempt=attempt,
                        error=str(te),
                    )
                    if attempt < max_attempts:
                        await asyncio.sleep(0.2)
                        continue
                    return 504, {"error": "Google Routes API 4.0s request timeout exceeded", "status": 504}

                except Exception as exc:
                    self.circuit_breaker.record_failure()
                    logger.error(
                        "Google Routes API connection error",
                        endpoint=url.split("/")[-1],
                        attempt=attempt,
                        error=str(exc),
                    )
                    return 500, {"error": str(exc), "status": 500}

            return last_status or 500, {"error": last_error_text or "Unknown Google Routes error", "status": last_status}

        finally:
            if should_close_client:
                await client.aclose()

    # =========================================================================
    # TIER 1: computeRouteMatrix
    # =========================================================================

    async def compute_route_matrix(
        self,
        origins: List[Dict[str, Any]],  # [{plant_id, plant_code, latitude, longitude}]
        destination: Dict[str, Any],    # {site_id, site_code, latitude, longitude}
        mode: RouteAnalysisMode = RouteAnalysisMode.NOW,
        departure_time: Optional[datetime] = None,
        force_refresh: bool = False,
    ) -> Tuple[List[GoogleCandidateMatrixItemDTO], bool, bool, float, Optional[str]]:
        """
        Executes Google Routes API v2 computeRouteMatrix for candidate plants.
        Returns (matrix_items, is_fresh, is_stale, cache_age, failure_reason).
        """
        if not origins:
            return [], True, False, 0.0, None

        if len(origins) > self.MAX_CANDIDATE_PLANTS_LIMIT:
            origins = origins[:self.MAX_CANDIDATE_PLANTS_LIMIT]

        site_coord = (float(destination["latitude"]), float(destination["longitude"]))
        origin_coords = [(float(o["latitude"]), float(o["longitude"])) for o in origins]

        dept_time_str = departure_time.isoformat() if departure_time else None
        cache_key = self.cache.generate_matrix_cache_key(origin_coords, site_coord, mode, dept_time_str)

        # 1. Check Cache
        cached_payload, is_fresh, cache_age = await self.cache.get(cache_key)
        if cached_payload and not force_refresh:
            if is_fresh:
                # Fresh cache (< 300s) -> return directly
                try:
                    asyncio.create_task(
                        self._record_usage_telemetry(
                            api_service="ROUTES_MATRIX_V2",
                            endpoint="distanceMatrix/v2:computeRouteMatrix",
                            request_count=len(origins),
                            status_code=200,
                            is_cached=True,
                            latency_ms=0.0,
                        )
                    )
                except Exception:
                    pass
                items = [GoogleCandidateMatrixItemDTO(**it) for it in cached_payload.get("items", [])]
                return items, True, False, cache_age, None

        # 2. Build Request Body
        origins_payload = [
            {
                "waypoint": {
                    "location": {
                        "latLng": {
                            "latitude": float(o["latitude"]),
                            "longitude": float(o["longitude"]),
                        }
                    }
                }
            }
            for o in origins
        ]

        destinations_payload = [
            {
                "waypoint": {
                    "location": {
                        "latLng": {
                            "latitude": site_coord[0],
                            "longitude": site_coord[1],
                        }
                    }
                }
            }
        ]

        body: Dict[str, Any] = {
            "origins": origins_payload,
            "destinations": destinations_payload,
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE",
        }

        if mode == RouteAnalysisMode.PLANNED_DEPARTURE and departure_time:
            # Anchor UTC ISO-8601 string
            if departure_time.tzinfo is None:
                dept_dt = departure_time.replace(tzinfo=timezone.utc)
            else:
                dept_dt = departure_time
            body["departureTime"] = dept_dt.isoformat()

        field_mask = "originIndex,destinationIndex,status,condition,distanceMeters,duration,staticDuration"

        # 3. Execute HTTP Call
        call_start = time.time()
        try:
            status_code, resp_data = await self._execute_http_request(
                url=self.ROUTES_MATRIX_URL,
                headers={},
                payload=body,
                field_mask=field_mask,
            )
            latency_ms = round((time.time() - call_start) * 1000.0, 2)
            try:
                asyncio.create_task(
                    self._record_usage_telemetry(
                        api_service="ROUTES_MATRIX_V2",
                        endpoint="distanceMatrix/v2:computeRouteMatrix",
                        request_count=len(origins),
                        status_code=status_code,
                        is_cached=False,
                        latency_ms=latency_ms,
                    )
                )
            except Exception:
                pass
        except Exception as exc:
            latency_ms = round((time.time() - call_start) * 1000.0, 2)
            try:
                asyncio.create_task(
                    self._record_usage_telemetry(
                        api_service="ROUTES_MATRIX_V2",
                        endpoint="distanceMatrix/v2:computeRouteMatrix",
                        request_count=len(origins),
                        status_code=500,
                        is_cached=False,
                        latency_ms=latency_ms,
                    )
                )
            except Exception:
                pass
            # Circuit open or unrecoverable error
            if cached_payload:
                # Stale fallback for audit/informational view only
                items = [GoogleCandidateMatrixItemDTO(**it) for it in cached_payload.get("items", [])]
                return items, False, True, cache_age, str(exc)
            return [], False, False, 0.0, str(exc)

        if status_code != 200:
            err_msg = f"Google computeRouteMatrix returned HTTP {status_code}: {resp_data.get('error', '')}"
            if cached_payload:
                items = [GoogleCandidateMatrixItemDTO(**it) for it in cached_payload.get("items", [])]
                return items, False, True, cache_age, err_msg
            return [], False, False, 0.0, err_msg

        # 4. Parse Response Items
        raw_elements = resp_data if isinstance(resp_data, list) else resp_data.get("elements", [])
        items_map: Dict[int, dict] = {}
        for elem in raw_elements:
            orig_idx = int(elem.get("originIndex", 0))
            items_map[orig_idx] = elem

        parsed_items: List[GoogleCandidateMatrixItemDTO] = []
        for idx, origin in enumerate(origins):
            elem = items_map.get(idx, {})
            status_elem = elem.get("status", {})
            status_str = status_elem.get("code", "OK") if isinstance(status_elem, dict) else str(status_elem or "OK")
            if status_str == "0" or not status_str or status_str == "None":
                status_str = "OK"

            duration_raw = elem.get("duration")
            static_duration_raw = elem.get("staticDuration")
            distance_meters = elem.get("distanceMeters")

            duration_sec = self._parse_seconds(duration_raw)
            static_duration_sec = self._parse_seconds(static_duration_raw)

            duration_min = round(duration_sec / 60.0, 2) if duration_sec is not None else None
            static_min = round(static_duration_sec / 60.0, 2) if static_duration_sec is not None else None
            
            # Dtraffic = Troute - Tstatic
            traffic_delay_min = None
            if duration_min is not None and static_min is not None:
                traffic_delay_min = round(max(0.0, duration_min - static_min), 2)

            dist_km = round(distance_meters / 1000.0, 2) if distance_meters is not None else None

            item = GoogleCandidateMatrixItemDTO(
                plant_id=str(origin["plant_id"]),
                plant_code=str(origin["plant_code"]),
                site_id=str(destination["site_id"]),
                site_code=str(destination["site_code"]),
                origin_index=idx,
                destination_index=0,
                status=status_str,
                duration_seconds=duration_sec,
                duration_minutes=duration_min,
                static_duration_seconds=static_duration_sec,
                static_duration_minutes=static_min,
                traffic_delay_minutes=traffic_delay_min,
                distance_meters=distance_meters,
                distance_km=dist_km,
                condition=elem.get("condition"),
            )
            parsed_items.append(item)

        # 5. Store in Cache
        serialized = {"items": [it.model_dump() for it in parsed_items]}
        await self.cache.set(cache_key, serialized)

        return parsed_items, True, False, 0.0, None

    # =========================================================================
    # TIER 2: computeRoutes (Selected / Recommended Routes)
    # =========================================================================

    async def compute_detailed_route(
        self,
        origin: Dict[str, Any],       # {plant_id, plant_code, latitude, longitude}
        destination: Dict[str, Any],  # {site_id, site_code, latitude, longitude}
        mode: RouteAnalysisMode = RouteAnalysisMode.NOW,
        departure_time: Optional[datetime] = None,
        force_refresh: bool = False,
    ) -> Tuple[Optional[GoogleDetailedRouteDTO], bool, bool, float, Optional[str]]:
        """
        Executes Google Routes API v2 computeRoutes for detailed polyline and speed intervals.
        Returns (detailed_route, is_fresh, is_stale, cache_age, failure_reason).
        """
        orig_coord = (float(origin["latitude"]), float(origin["longitude"]))
        dest_coord = (float(destination["latitude"]), float(destination["longitude"]))

        dept_time_str = departure_time.isoformat() if departure_time else None
        cache_key = self.cache.generate_detailed_cache_key(orig_coord, dest_coord, mode, dept_time_str)

        # 1. Check Cache
        cached_payload, is_fresh, cache_age = await self.cache.get(cache_key)
        if cached_payload and not force_refresh:
            if is_fresh:
                try:
                    asyncio.create_task(
                        self._record_usage_telemetry(
                            api_service="ROUTES_COMPUTE_V2",
                            endpoint="directions/v2:computeRoutes",
                            request_count=1,
                            status_code=200,
                            is_cached=True,
                            latency_ms=0.0,
                        )
                    )
                except Exception:
                    pass
                route_dto = GoogleDetailedRouteDTO(**cached_payload)
                return route_dto, True, False, cache_age, None

        # 2. Build Request Body
        body: Dict[str, Any] = {
            "origin": {
                "location": {
                    "latLng": {
                        "latitude": orig_coord[0],
                        "longitude": orig_coord[1],
                    }
                }
            },
            "destination": {
                "location": {
                    "latLng": {
                        "latitude": dest_coord[0],
                        "longitude": dest_coord[1],
                    }
                }
            },
            "travelMode": "DRIVE",
            "routingPreference": "TRAFFIC_AWARE",
            "polylineQuality": "OVERVIEW",
            "polylineEncoding": "ENCODED_POLYLINE",
            "extraComputations": ["TRAFFIC_ON_POLYLINE"],
        }

        if mode == RouteAnalysisMode.PLANNED_DEPARTURE and departure_time:
            if departure_time.tzinfo is None:
                dept_dt = departure_time.replace(tzinfo=timezone.utc)
            else:
                dept_dt = departure_time
            body["departureTime"] = dept_dt.isoformat()

        field_mask = (
            "routes.duration,routes.staticDuration,routes.distanceMeters,"
            "routes.polyline.encodedPolyline,routes.travelAdvisory.speedReadingIntervals,"
            "routes.routeToken"
        )

        # 3. Execute HTTP Call
        call_start = time.time()
        try:
            status_code, resp_data = await self._execute_http_request(
                url=self.ROUTES_COMPUTE_URL,
                headers={},
                payload=body,
                field_mask=field_mask,
            )
            latency_ms = round((time.time() - call_start) * 1000.0, 2)
            try:
                asyncio.create_task(
                    self._record_usage_telemetry(
                        api_service="ROUTES_COMPUTE_V2",
                        endpoint="directions/v2:computeRoutes",
                        request_count=1,
                        status_code=status_code,
                        is_cached=False,
                        latency_ms=latency_ms,
                    )
                )
            except Exception:
                pass
        except Exception as exc:
            latency_ms = round((time.time() - call_start) * 1000.0, 2)
            try:
                asyncio.create_task(
                    self._record_usage_telemetry(
                        api_service="ROUTES_COMPUTE_V2",
                        endpoint="directions/v2:computeRoutes",
                        request_count=1,
                        status_code=500,
                        is_cached=False,
                        latency_ms=latency_ms,
                    )
                )
            except Exception:
                pass
            if cached_payload:
                return GoogleDetailedRouteDTO(**cached_payload), False, True, cache_age, str(exc)
            return None, False, False, 0.0, str(exc)

        if status_code != 200:
            err_msg = f"Google computeRoutes returned HTTP {status_code}: {resp_data.get('error', '')}"
            if cached_payload:
                return GoogleDetailedRouteDTO(**cached_payload), False, True, cache_age, err_msg
            return None, False, False, 0.0, err_msg

        # 4. Parse Detailed Route
        routes = resp_data.get("routes", [])
        if not routes:
            return None, True, False, 0.0, "Google returned empty routes array"

        first_route = routes[0]
        duration_sec = self._parse_seconds(first_route.get("duration")) or 0
        static_duration_sec = self._parse_seconds(first_route.get("staticDuration"))
        distance_meters = int(first_route.get("distanceMeters", 0))

        duration_min = round(duration_sec / 60.0, 2)
        static_min = round(static_duration_sec / 60.0, 2) if static_duration_sec is not None else None
        traffic_delay_min = round(max(0.0, duration_min - static_min), 2) if static_min is not None else None
        dist_km = round(distance_meters / 1000.0, 2)

        encoded_polyline = first_route.get("polyline", {}).get("encodedPolyline", "")

        # Speed reading intervals
        advisory = first_route.get("travelAdvisory", {})
        raw_intervals = advisory.get("speedReadingIntervals", []) if advisory else []
        speed_intervals = [self.parse_speed_reading_interval(it) for it in raw_intervals]

        detailed_dto = GoogleDetailedRouteDTO(
            plant_id=str(origin["plant_id"]),
            plant_code=str(origin["plant_code"]),
            site_id=str(destination["site_id"]),
            site_code=str(destination["site_code"]),
            encoded_polyline=encoded_polyline,
            duration_seconds=duration_sec,
            duration_minutes=duration_min,
            static_duration_seconds=static_duration_sec,
            static_duration_minutes=static_min,
            traffic_delay_minutes=traffic_delay_min,
            distance_meters=distance_meters,
            distance_km=dist_km,
            speed_reading_intervals=speed_intervals,
            travel_advisory=advisory,
            route_token=first_route.get("routeToken"),
        )

        # 5. Store in Cache
        await self.cache.set(cache_key, detailed_dto.model_dump())

        return detailed_dto, True, False, 0.0, None

    @classmethod
    def _parse_seconds(cls, raw_duration: Any) -> Optional[int]:
        """Parses Google duration string like '1234s' or numeric seconds into int."""
        if raw_duration is None:
            return None
        if isinstance(raw_duration, (int, float)):
            return int(raw_duration)
        s_val = str(raw_duration).strip().rstrip("s")
        try:
            return int(float(s_val))
        except (ValueError, TypeError):
            return None


# =============================================================================
# 4. PROVIDER ABSTRACTION LAYER (FOR WS-ROUT-3 SYNTHESIS CONSUMPTION)
# =============================================================================


class IRouteProvider(ABC):
    """Abstract provider contract for external routing services."""

    @abstractmethod
    async def get_route_evidence(
        self,
        origins: List[Dict[str, Any]],
        destination: Dict[str, Any],
        mode: RouteAnalysisMode = RouteAnalysisMode.NOW,
        departure_time: Optional[datetime] = None,
        fetch_detailed_for_plant_ids: Optional[List[str]] = None,
        force_refresh: bool = False,
    ) -> GoogleRouteEvidenceSummaryDTO:
        pass


class GoogleRoutesProvider(IRouteProvider):
    """
    Production Google Routes Provider implementation.
    Consumes GoogleRoutesClient and packages normalized evidence for WS-ROUT-3.
    """

    def __init__(self, client: Optional[GoogleRoutesClient] = None):
        self.client = client or GoogleRoutesClient()

    async def get_route_evidence(
        self,
        origins: List[Dict[str, Any]],
        destination: Dict[str, Any],
        mode: RouteAnalysisMode = RouteAnalysisMode.NOW,
        departure_time: Optional[datetime] = None,
        fetch_detailed_for_plant_ids: Optional[List[str]] = None,
        force_refresh: bool = False,
    ) -> GoogleRouteEvidenceSummaryDTO:
        """
        Queries Tier 1 Matrix for all candidates and Tier 2 computeRoutes for requested plants.
        """
        now_ts = datetime.now(timezone.utc).isoformat()
        circuit_state = self.client.circuit_breaker.state

        # Check circuit breaker before query
        if not self.client.circuit_breaker.allow_execution():
            return GoogleRouteEvidenceSummaryDTO(
                provider_name="GOOGLE_ROUTES_V2",
                status="CIRCUIT_OPEN",
                mode=mode,
                requested_departure_time=departure_time.isoformat() if departure_time else None,
                response_timestamp=now_ts,
                is_fresh=False,
                is_stale_cache=False,
                failure_reason="Google Routes circuit breaker is OPEN due to high error rate",
                circuit_state=circuit_state,
            )

        # 1. Tier 1 Matrix Query
        matrix_items, is_fresh, is_stale, cache_age, failure_reason = await self.client.compute_route_matrix(
            origins=origins,
            destination=destination,
            mode=mode,
            departure_time=departure_time,
            force_refresh=force_refresh,
        )

        matrix_dict = {item.plant_id: item for item in matrix_items}

        # 2. Tier 2 Detailed Query for requested candidate(s)
        detailed_dict: Dict[str, GoogleDetailedRouteDTO] = {}
        if fetch_detailed_for_plant_ids:
            for orig in origins:
                pid = str(orig["plant_id"])
                if pid in fetch_detailed_for_plant_ids:
                    detailed_route, d_fresh, d_stale, d_age, d_err = await self.client.compute_detailed_route(
                        origin=orig,
                        destination=destination,
                        mode=mode,
                        departure_time=departure_time,
                        force_refresh=force_refresh,
                    )
                    if detailed_route:
                        detailed_dict[pid] = detailed_route

        # Determine overall provider status
        if failure_reason:
            status = "STALE_FALLBACK" if is_stale else "PROVIDER_FAILURE"
        elif not matrix_items and origins:
            status = "PROVIDER_FAILURE"
        else:
            status = "SUCCESS"

        return GoogleRouteEvidenceSummaryDTO(
            provider_name="GOOGLE_ROUTES_V2",
            status=status,
            mode=mode,
            requested_departure_time=departure_time.isoformat() if departure_time else None,
            response_timestamp=now_ts,
            is_fresh=is_fresh,
            is_stale_cache=is_stale,
            cache_age_seconds=cache_age,
            matrix_items=matrix_dict,
            detailed_routes=detailed_dict,
            failure_reason=failure_reason,
            circuit_state=self.client.circuit_breaker.state,
        )
