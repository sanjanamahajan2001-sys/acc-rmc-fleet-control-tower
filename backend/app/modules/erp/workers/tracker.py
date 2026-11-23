"""
Progress Tracker, Audit Logger, Statistics Aggregator, Checkpoint Manager & Metrics Collector for WS1.5
Automatically populates ImportAuditLog, ImportStatistic, ImportPerformanceMetrics, ImportCheckpoint, and ImportEvent entities.
"""

import time
from enum import Enum
from typing import Any

import psutil
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.bus import EventBus
from app.events.schema import BaseEvent
from app.modules.erp.models import (
    ImportAuditLog,
    ImportCheckpoint,
    ImportEvent,
    ImportPerformanceMetrics,
    ImportStatistic,
)


class ImportPipelineStage(str, Enum):
    """
    Strongly typed enum defining execution stages of the ERP ingestion pipeline.
    """

    QUEUED = "QUEUED"
    ACQUIRING = "ACQUIRING"
    PARSING = "PARSING"
    VALIDATING = "VALIDATING"
    PERSISTING = "PERSISTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ImportProgressSnapshot(BaseModel):
    """
    Unified progress snapshot DTO for API serialization (WS1.6) and Frontend UI rendering (WS1.7).
    """

    job_id: str
    stage: ImportPipelineStage = Field(default=ImportPipelineStage.QUEUED)
    status: str = "QUEUED"
    rows_processed: int = 0
    rows_total: int = 0
    rows_validated: int = 0
    rows_persisted: int = 0
    rows_failed: int = 0
    percentage: float = 0.0
    elapsed_seconds: float = 0.0
    eta_seconds: float = 0.0
    throughput_rows_per_sec: float = 0.0
    worker_id: str = "worker-01"
    memory_mb: float = 0.0
    current_sheet: str | None = None
    batch_number: int = 0


# Backwards-compatible alias for tracker internal state
ProgressTrackerState = ImportProgressSnapshot


class ImportPipelineProgressTracker:
    """
    Tracks and publishes real-time ingestion progress and performance metrics.
    """

    def __init__(
        self,
        job_id: str,
        worker_id: str = "worker-01",
        event_bus: EventBus | None = None,
    ):
        self.job_id = job_id
        self.worker_id = worker_id
        self.event_bus = event_bus
        self.start_time = time.time()
        self.snapshot = ImportProgressSnapshot(job_id=job_id, worker_id=worker_id)

    @property
    def state(self) -> ImportProgressSnapshot:
        return self.snapshot

    async def update_progress(
        self,
        stage: ImportPipelineStage | str,
        sheet_name: str | None = None,
        batch_idx: int = 0,
        rows_processed: int = 0,
        rows_validated: int = 0,
        rows_persisted: int = 0,
        rows_failed: int = 0,
        total_rows: int = 0,
    ) -> None:
        elapsed = max(0.001, time.time() - self.start_time)
        if isinstance(stage, str):
            stage_enum = ImportPipelineStage(stage)
        else:
            stage_enum = stage

        self.snapshot.stage = stage_enum
        self.snapshot.status = stage_enum.value
        if sheet_name:
            self.snapshot.current_sheet = sheet_name
        self.snapshot.batch_number = batch_idx
        self.snapshot.rows_processed = rows_processed
        self.snapshot.rows_validated = rows_validated
        self.snapshot.rows_persisted = rows_persisted
        self.snapshot.rows_failed = rows_failed
        if total_rows > 0:
            self.snapshot.rows_total = total_rows

        if self.snapshot.rows_total > 0:
            self.snapshot.percentage = round(
                (rows_processed / self.snapshot.rows_total) * 100.0, 2
            )
            remaining_rows = max(0, self.snapshot.rows_total - rows_processed)
            rate = rows_processed / elapsed
            self.snapshot.throughput_rows_per_sec = round(rate, 2)
            if rate > 0:
                self.snapshot.eta_seconds = round(remaining_rows / rate, 2)

        self.snapshot.elapsed_seconds = round(elapsed, 2)
        proc = psutil.Process()
        self.snapshot.memory_mb = round(proc.memory_info().rss / (1024 * 1024), 2)

        if self.event_bus:
            event = BaseEvent[dict[str, Any]](
                event_type="erp.import.progress",
                payload=self.snapshot.model_dump(),
                correlation_id=self.job_id,
                request_id=self.job_id,
            )
            await self.event_bus.publish(event)


class ImportAuditCoordinator:
    """
    Automatically creates audit log entries, performance metrics, and events in PostgreSQL.
    """

    @staticmethod
    async def create_audit_and_metrics(
        session: AsyncSession,
        job_db_id: Any,
        stage_name: str,
        status: str,
        message: str,
        snapshot: ImportProgressSnapshot,
        extra_details: dict[str, Any] | None = None,
    ) -> None:
        details_payload = {"message": message, "worker": snapshot.worker_id}
        if extra_details:
            details_payload.update(extra_details)

        # 1. Audit Log
        audit = ImportAuditLog(
            job_id=job_db_id,
            action=f"{stage_name}_{status}",
            details=details_payload,
        )
        session.add(audit)

        # 2. Event
        evt = ImportEvent(
            job_id=job_db_id,
            event_name=f"erp.import.{stage_name.lower()}",
            payload={
                "status": status,
                "message": message,
                "elapsed": snapshot.elapsed_seconds,
                **(extra_details or {}),
            },
        )
        session.add(evt)

        # 3. Performance Metrics
        metrics = ImportPerformanceMetrics(
            job_id=job_db_id,
            cpu_usage_pct=0.0,
            memory_usage_mb=snapshot.memory_mb,
            io_write_mb=0.0,
        )
        session.add(metrics)

        # 4. Statistics
        stat = ImportStatistic(
            job_id=job_db_id,
            duration_ms=snapshot.elapsed_seconds * 1000.0,
            rows_per_sec=snapshot.throughput_rows_per_sec,
            peak_memory_mb=snapshot.memory_mb,
        )
        session.add(stat)

        await session.flush()

    @staticmethod
    async def save_checkpoint(
        session: AsyncSession,
        job_db_id: Any,
        sheet_name: str,
        batch_idx: int,
        row_offset: int,
        checkpoint_data: dict[str, Any],
    ) -> None:
        checkpoint = ImportCheckpoint(
            job_id=job_db_id,
            last_processed_row=row_offset,
            checkpoint_data={
                "sheet_name": sheet_name,
                "batch_index": batch_idx,
                **checkpoint_data,
            },
        )
        session.add(checkpoint)
        await session.flush()
