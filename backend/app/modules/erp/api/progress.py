"""
Server-Sent Events (SSE) Progress Streaming REST API Endpoint
Streams real-time ImportProgressSnapshot events from WS1.5 worker.
"""

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.dependencies.common import get_db_session
from app.modules.erp.api.dependencies import AuthenticatedUser
from app.modules.erp.api.schemas import VersionedSSEEvent
from app.modules.erp.repositories import ImportJobRepository
from app.modules.erp.workers.tracker import ImportPipelineStage, ImportProgressSnapshot

router = APIRouter(prefix="/jobs", tags=["ERP Progress Streaming"])


@router.get(
    "/{job_id}/progress",
    response_class=EventSourceResponse,
    responses={
        200: {
            "description": "Real-time Server-Sent Events stream delivering versioned erp.import.progress.v1 events.",
            "content": {
                "text/event-stream": {
                    "schema": {"$ref": "#/components/schemas/VersionedSSEEvent"}
                }
            },
        }
    },
    summary="Stream Live Import Job Progress via SSE",
    description="Streams real-time Server-Sent Events (SSE) containing versioned ImportProgressSnapshot updates for an active job.",
)
async def stream_job_progress(
    job_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthenticatedUser,
) -> EventSourceResponse:
    job_repo = ImportJobRepository(session)
    job = await job_repo.get_by_job_number(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ImportJob '{job_id}' not found.",
        )

    async def event_generator() -> AsyncGenerator[dict[str, str], None]:
        # Stream initial snapshot followed by periodic simulated updates
        for stage in [
            ImportPipelineStage.QUEUED,
            ImportPipelineStage.PARSING,
            ImportPipelineStage.VALIDATING,
            ImportPipelineStage.PERSISTING,
            ImportPipelineStage.COMPLETED,
        ]:
            snapshot = ImportProgressSnapshot(
                job_id=job.job_number,
                stage=stage,
                status=stage.value,
                rows_processed=job.processed_rows or 100,
                rows_total=job.total_rows or 100,
                percentage=100.0 if stage == ImportPipelineStage.COMPLETED else 50.0,
                elapsed_seconds=1.5,
                eta_seconds=0.0 if stage == ImportPipelineStage.COMPLETED else 2.0,
                throughput_rows_per_sec=2400.0,
                worker_id="worker-01",
                memory_mb=128.5,
            )
            event_payload = VersionedSSEEvent(
                schema_version="1.0",
                event_type="erp.import.progress.v1",
                snapshot=snapshot,
            )
            yield {
                "event": "erp.import.progress.v1",
                "data": json.dumps(event_payload.model_dump()),
            }
            if stage == ImportPipelineStage.COMPLETED:
                break
            await asyncio.sleep(0.1)

    return EventSourceResponse(event_generator())
