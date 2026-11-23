"""
WS-10 Phase 6.3 Watermarked Batch Prediction Engine
Executes incremental batch inference for newly arrived ERP dispatches using persistent high-watermark cursors.
Includes production failure atomicity, partial batch recovery, and lexicographical watermark predicate.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.erp.models import Dispatch
from app.modules.operational_intelligence.models.ml_batch_cursor import MLBatchProcessingCursor
from app.modules.operational_intelligence.services.production_inference_service import ProductionInferenceService

logger = logging.getLogger(__name__)


@dataclass
class BatchInferenceResponseDTO:
    dispatches_processed: int
    snapshots_created: int
    snapshots_reused: int
    execution_time_ms: float
    watermark_timestamp: Optional[str]
    watermark_dispatch_id: Optional[str]
    failed_dispatch_id: Optional[str] = None


class BatchPredictionEngine:
    """
    Production Watermarked Batch Inference Engine.
    Processes dispatches incrementally using lexicographical (created_at, dispatch_id) high-watermarks.
    Guarantees that the cursor never advances past an unprocessed or failed dispatch.
    """

    CURSOR_JOB_NAME = "DISPATCH_BATCH_INFERENCE_CURSOR"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_cursor(self) -> MLBatchProcessingCursor:
        stmt = select(MLBatchProcessingCursor).where(MLBatchProcessingCursor.batch_job_name == self.CURSOR_JOB_NAME)
        res = await self.session.execute(stmt)
        cursor = res.scalars().first()

        if not cursor:
            cursor = MLBatchProcessingCursor(
                id=str(uuid.uuid4()),
                batch_job_name=self.CURSOR_JOB_NAME,
                last_processed_timestamp=None,
                last_processed_dispatch_id=None,
                total_dispatches_processed=0,
                total_snapshots_generated=0,
            )
            self.session.add(cursor)
            await self.session.commit()
        return cursor

    async def process_incremental_batch(
        self,
        max_dispatches: int = 200,
        force_reprocess: bool = False,
    ) -> BatchInferenceResponseDTO:
        start_time = datetime.now(timezone.utc)
        cursor = await self.get_or_create_cursor()

        # Build lexicographical watermark predicate: (created_at > watermark) OR (created_at == watermark AND id > watermark_id)
        stmt = select(Dispatch).order_by(Dispatch.created_at.asc(), Dispatch.id.asc())
        if cursor.last_processed_timestamp and not force_reprocess:
            if cursor.last_processed_dispatch_id:
                last_id_str = str(cursor.last_processed_dispatch_id)
                stmt = stmt.where(
                    (Dispatch.created_at > cursor.last_processed_timestamp) |
                    (
                        (Dispatch.created_at == cursor.last_processed_timestamp) &
                        (text("dispatches.id > CAST(:last_id AS UUID)"))
                    )
                ).params(last_id=last_id_str)
            else:
                stmt = stmt.where(Dispatch.created_at > cursor.last_processed_timestamp)

        stmt = stmt.limit(max_dispatches)
        res = await self.session.execute(stmt)
        dispatches = res.scalars().all()

        if not dispatches:
            logger.info("[BATCH PREDICTION ENGINE] 0 new dispatches to process.")
            return BatchInferenceResponseDTO(
                dispatches_processed=0,
                snapshots_created=0,
                snapshots_reused=0,
                execution_time_ms=(datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0,
                watermark_timestamp=cursor.last_processed_timestamp.isoformat() if cursor.last_processed_timestamp else None,
                watermark_dispatch_id=cursor.last_processed_dispatch_id,
            )

        inference_service = ProductionInferenceService(self.session)
        total_created = 0
        total_reused = 0
        successful_dispatches_count = 0
        last_successful_dispatch: Optional[Dispatch] = None
        failed_dispatch_id: Optional[str] = None

        for disp in dispatches:
            try:
                result = await inference_service.execute_inference(
                    dispatch_id=str(disp.id),
                    model_family=None, # Execute all 4 families
                    force_reprocess=force_reprocess,
                )
                total_created += result.snapshots_created
                total_reused += result.snapshots_reused
                successful_dispatches_count += 1
                last_successful_dispatch = disp
            except Exception as e:
                failed_dispatch_id = str(disp.id)
                logger.error(f"[BATCH PREDICTION ENGINE] Failure executing inference for dispatch {disp.id}: {e}")
                # Halting batch execution so watermark NEVER advances past an unprocessed or failed dispatch
                break

        # Atomically advance watermark up to the last successful dispatch only
        if last_successful_dispatch:
            cursor.last_processed_timestamp = last_successful_dispatch.created_at
            cursor.last_processed_dispatch_id = str(last_successful_dispatch.id)
            cursor.total_dispatches_processed += successful_dispatches_count
            cursor.total_snapshots_generated += total_created
            self.session.add(cursor)
            await self.session.commit()

        exec_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000.0
        logger.info(
            f"[BATCH PREDICTION ENGINE] Processed {successful_dispatches_count}/{len(dispatches)} dispatches "
            f"({total_created} created, {total_reused} reused, failed: {failed_dispatch_id}) in {exec_ms:.1f}ms."
        )

        return BatchInferenceResponseDTO(
            dispatches_processed=successful_dispatches_count,
            snapshots_created=total_created,
            snapshots_reused=total_reused,
            execution_time_ms=exec_ms,
            watermark_timestamp=cursor.last_processed_timestamp.isoformat() if cursor.last_processed_timestamp else None,
            watermark_dispatch_id=cursor.last_processed_dispatch_id,
            failed_dispatch_id=failed_dispatch_id,
        )
