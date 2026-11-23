"""
Diagnostic Health & Readiness API Router

Provides /health/liveness and /health/readiness endpoints reporting process state,
PostgreSQL database pool status, Redis status, worker heartbeat, worker metrics,
environment settings, build version, and system uptime.
"""

import time
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, status

from app.core.config import settings
from app.core.context import RequestContext
from app.core.database import check_database_health
from app.core.redis import check_redis_health
from app.schemas.envelope import APIResponse
from app.workers import heartbeat_monitor, task_queue

router = APIRouter(prefix="/health", tags=["System Diagnostics"])

# Record application process launch timestamp
_START_TIMESTAMP: float = time.time()


@router.get(
    "/liveness",
    summary="Process Liveness Probe",
    description="Returns HTTP 200 OK if backend application server process is alive.",
    status_code=status.HTTP_200_OK,
)
async def liveness_probe() -> APIResponse[dict[str, str]]:
    """Simple process liveness health check."""
    return APIResponse.ok(
        data={"status": "alive", "environment": settings.ENVIRONMENT},
        correlation_id=RequestContext.get_correlation_id(),
        request_id=RequestContext.get_request_id(),
        duration_ms=RequestContext.get_execution_duration_ms(),
    )


@router.get(
    "/readiness",
    summary="Application Readiness Probe",
    description="Checks downstream dependencies (PostgreSQL, Redis, Worker Heartbeat) and returns full system readiness status.",
    status_code=status.HTTP_200_OK,
)
async def readiness_probe() -> APIResponse[dict[str, Any]]:
    """Comprehensive system readiness probe checking database, Redis, worker metrics, uptime, and configuration."""
    db_health = await check_database_health()
    redis_health = await check_redis_health()
    heartbeat_status = heartbeat_monitor.get_status()
    worker_metrics = task_queue.get_metrics().model_dump()
    uptime_seconds = round(time.time() - _START_TIMESTAMP, 2)

    is_ready = (
        db_health.get("status") == "healthy" and redis_health.get("status") == "healthy"
    )

    readiness_data: dict[str, Any] = {
        "status": "ready" if is_ready else "unhealthy",
        "environment": settings.ENVIRONMENT,
        "api_version": "v1",
        "platform_version": "1.0.0",
        "uptime_seconds": uptime_seconds,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "database": db_health,
            "redis": redis_health,
            "worker_heartbeat": heartbeat_status,
            "worker_metrics": worker_metrics,
        },
    }

    return APIResponse.ok(
        data=readiness_data,
        correlation_id=RequestContext.get_correlation_id(),
        request_id=RequestContext.get_request_id(),
        duration_ms=RequestContext.get_execution_duration_ms(),
    )
