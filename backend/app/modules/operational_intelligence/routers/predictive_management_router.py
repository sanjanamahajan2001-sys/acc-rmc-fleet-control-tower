"""
WS-10 Phase 6.4 REST Predictive Management Router
Provides production FastAPI endpoints for:
1. Triggering watermarked batch prediction engine runs (POST /predictive/batch-run).
2. Targeted prediction snapshot invalidation (POST /predictive/invalidate-snapshots).
3. Read-only system telemetry observability (GET /predictive/telemetry).
"""

import uuid
import asyncio
import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.common import get_db_session
from app.modules.operational_intelligence.services.batch_prediction_engine import (
    BatchPredictionEngine,
    BatchInferenceResponseDTO,
)
from app.modules.operational_intelligence.services.authoritative_resolver import SUPPORTED_MODEL_FAMILIES
from app.modules.operational_intelligence.services.predictive_telemetry_service import PredictiveTelemetryService
from app.modules.operational_intelligence.schemas.predictive_management_dtos import (
    BatchRunRequestDTO,
    InvalidateSnapshotsRequestDTO,
    InvalidationResponseDTO,
    TelemetryObservabilityDTO,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictive", tags=["Predictive Management & Observability"])

# Production concurrency lock for single-run serialization
_batch_run_lock = asyncio.Lock()


@router.post(
    "/batch-run",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Trigger Watermarked Batch Prediction Engine Run (WS-10 Section 6.4)",
    description="Triggers incremental batch inference using WS6.3 lexicographical watermarks. Serialized via execution lock.",
)
async def trigger_batch_prediction_run(
    request: BatchRunRequestDTO,
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    if _batch_run_lock.locked():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="BATCH_ALREADY_RUNNING: A batch prediction run is currently in progress.",
        )

    async with _batch_run_lock:
        try:
            engine = BatchPredictionEngine(session)
            res: BatchInferenceResponseDTO = await engine.process_incremental_batch(
                max_dispatches=request.max_dispatches,
                force_reprocess=request.force_reprocess,
            )
            data_dict = {
                "dispatches_processed": res.dispatches_processed,
                "snapshots_created": res.snapshots_created,
                "snapshots_reused": res.snapshots_reused,
                "execution_time_ms": res.execution_time_ms,
                "watermark_timestamp": res.watermark_timestamp,
                "watermark_dispatch_id": res.watermark_dispatch_id,
                "failed_dispatch_id": res.failed_dispatch_id,
                "force_reprocess_requested": request.force_reprocess,
            }
            return {"success": True, "data": data_dict}
        except Exception as e:
            logger.error(f"[REST BATCH RUN] Failure executing batch inference run: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Batch execution failed: {str(e)}",
            )


@router.post(
    "/invalidate-snapshots",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Invalidate Prediction Snapshots (WS-10 Section 6.4)",
    description="Marks matching prediction snapshots as stale using Phase 4 invalidation rules. Requires positive target scope and reason.",
)
async def invalidate_prediction_snapshots(
    request: InvalidateSnapshotsRequestDTO,
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    # Validate UUID format if dispatch_id provided
    if request.dispatch_id:
        try:
            uuid.UUID(str(request.dispatch_id))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid dispatch_id UUID format: '{request.dispatch_id}'",
            )

    # Validate model family if provided
    if request.model_family and request.model_family not in SUPPORTED_MODEL_FAMILIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown model_family '{request.model_family}'. Must be one of {SUPPORTED_MODEL_FAMILIES}",
        )

    try:
        dto: InvalidationResponseDTO = await PredictiveTelemetryService.invalidate_snapshots(session, request)
        return {"success": True, "data": dto.model_dump()}
    except Exception as e:
        logger.error(f"[REST INVALIDATION] Failure invalidating snapshots: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Snapshot invalidation failed: {str(e)}",
        )


@router.get(
    "/telemetry",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Predictive Intelligence System Telemetry (WS-10 Section 6.4)",
    description="Pure read-only observation endpoint exposing active authority, snapshot statistics, and batch watermark state.",
)
async def get_predictive_system_telemetry(
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    try:
        dto: TelemetryObservabilityDTO = await PredictiveTelemetryService.get_telemetry(session)
        return {"success": True, "data": dto.model_dump()}
    except Exception as e:
        logger.error(f"[REST TELEMETRY] Failure fetching system telemetry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Telemetry retrieval failed: {str(e)}",
        )
