"""
WS-10 Phase 6.4 Telemetry & Snapshot Invalidation Service
Provides database-derived read-only telemetry observability and Phase 4 compliant snapshot invalidation.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, func, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.ml_batch_cursor import MLBatchProcessingCursor
from app.modules.operational_intelligence.services.authoritative_resolver import (
    AuthoritativeModelResolver,
    SUPPORTED_MODEL_FAMILIES,
)
from app.modules.operational_intelligence.schemas.predictive_management_dtos import (
    InvalidateSnapshotsRequestDTO,
    InvalidationResponseDTO,
    TelemetryObservabilityDTO,
)

logger = logging.getLogger(__name__)


class PredictiveTelemetryService:
    """
    Service layer for Phase 6.4 REST endpoints:
    1. Read-only system telemetry observability.
    2. Phase 4 compliant targeted prediction snapshot invalidation.
    """

    @classmethod
    async def get_telemetry(cls, session: AsyncSession) -> TelemetryObservabilityDTO:
        """
        Pure read-only query compiling live production authority metrics,
        prediction snapshot counts, and batch processing cursor timestamps.
        Does NOT execute inference, update cursors, or mutate cache.
        """
        now = datetime.now(timezone.utc)

        # 1. Authority metrics
        stmt_prom = select(MLModelVersion).where(
            MLModelVersion.lifecycle_status == "PROMOTED",
            MLModelVersion.is_deleted == False,
        )
        res_prom = await session.execute(stmt_prom)
        promoted_models = list(res_prom.scalars().all())

        family_map: Dict[str, Any] = {}
        for m in promoted_models:
            family_map[m.model_name] = {
                "id": str(m.id),
                "model_version": m.model_version,
                "artifact_sha256": m.artifact_sha256,
                "training_timestamp": m.training_timestamp.isoformat() if m.training_timestamp else None,
            }

        missing_families = [fam for fam in SUPPORTED_MODEL_FAMILIES if fam not in family_map]
        auth_count = len(family_map)
        is_authoritative = (auth_count == len(SUPPORTED_MODEL_FAMILIES)) and (len(missing_families) == 0)

        # 2. Snapshot counts
        stmt_total_snaps = select(func.count(MLPredictionSnapshot.id))
        total_snaps = (await session.execute(stmt_total_snaps)).scalar() or 0

        stmt_stale_snaps = select(func.count(MLPredictionSnapshot.id)).where(
            MLPredictionSnapshot.is_stale == True
        )
        stale_snaps = (await session.execute(stmt_stale_snaps)).scalar() or 0

        active_snaps = total_snaps - stale_snaps

        # 3. Batch cursor state
        stmt_cursor = select(MLBatchProcessingCursor).where(
            MLBatchProcessingCursor.batch_job_name == "DISPATCH_BATCH_INFERENCE_CURSOR"
        )
        res_cursor = await session.execute(stmt_cursor)
        cursor = res_cursor.scalars().first()

        cursor_info = {
            "last_processed_timestamp": cursor.last_processed_timestamp.isoformat() if cursor and cursor.last_processed_timestamp else None,
            "last_processed_dispatch_id": cursor.last_processed_dispatch_id if cursor else None,
            "total_dispatches_processed": cursor.total_dispatches_processed if cursor else 0,
            "total_snapshots_generated": cursor.total_snapshots_generated if cursor else 0,
        }

        cursor_age = None
        if cursor and cursor.last_processed_timestamp:
            cursor_age = round((now - cursor.last_processed_timestamp).total_seconds(), 2)

        return TelemetryObservabilityDTO(
            generated_at=now.isoformat(),
            production_authority="AUTHORITATIVE" if is_authoritative else "DEGRADED",
            authoritative_model_count=auth_count,
            expected_model_family_count=len(SUPPORTED_MODEL_FAMILIES),
            missing_families=missing_families,
            authority_status=family_map,
            snapshot_metrics={
                "total_snapshots": total_snaps,
                "stale_snapshots": stale_snaps,
                "active_snapshots": active_snaps,
            },
            batch_cursor={
                **cursor_info,
                "cursor_age_seconds": cursor_age,
            },
            system_status="HEALTHY" if is_authoritative else "DEGRADED",
        )

    @classmethod
    async def invalidate_snapshots(
        cls,
        session: AsyncSession,
        request: InvalidateSnapshotsRequestDTO,
    ) -> InvalidationResponseDTO:
        """
        Phase 4 compliant targeted snapshot invalidation.
        Marks matching prediction snapshots as is_stale=True in ml_prediction_snapshots.
        Does NOT alter ml_model_versions or model authority.
        """
        now = datetime.now(timezone.utc)
        stmt = update(MLPredictionSnapshot).where(MLPredictionSnapshot.is_stale == False)

        if request.dispatch_id:
            stmt = stmt.where(MLPredictionSnapshot.dispatch_id == str(request.dispatch_id))
        if request.model_family:
            stmt = stmt.where(MLPredictionSnapshot.model_name == str(request.model_family))

        stmt = stmt.values(
            is_stale=True,
            updated_at=now,
        )

        res = await session.execute(stmt)
        await session.commit()
        invalidated_count = res.rowcount if hasattr(res, "rowcount") else 0

        logger.info(
            f"[PREDICTIVE TELEMETRY] Invalidated {invalidated_count} snapshots. "
            f"Target dispatch_id={request.dispatch_id}, model_family={request.model_family}, reason='{request.reason}'"
        )

        return InvalidationResponseDTO(
            invalidated_snapshots_count=invalidated_count,
            dispatch_id=request.dispatch_id,
            model_family=request.model_family,
            reason=request.reason,
            timestamp=now.isoformat(),
        )
