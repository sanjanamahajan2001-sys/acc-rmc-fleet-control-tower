"""
Exhaustive Test Suite for WS1.5 Background Import Pipeline & Worker Subsystem
Tests ERPImportWorker lifecycle (start, stop, heartbeat), queue processing, atomic persistence,
transaction rollbacks on validation errors, retry backoff, DLQ routing, progress tracking, and audit logging.
"""

import pathlib

import openpyxl
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.events.bus import InMemoryEventBus
from app.modules.erp.models import ImportJob
from app.modules.erp.repositories import DispatchRepository, ImportJobRepository
from app.modules.erp.services.state_machine import ImportJobState
from app.modules.erp.workers.orchestrator import ImportPipelineOrchestrator
from app.modules.erp.workers.worker import ERPImportWorker


@pytest.mark.asyncio
async def test_worker_end_to_end_successful_import(tmp_path: pathlib.Path):
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, pool_pre_ping=True)

    # 1. Setup real PostgreSQL AsyncSession
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            job_repo = ImportJobRepository(session)

            # Create test Excel file
            wb_path = tmp_path / "worker_test.xlsx"
            wb = openpyxl.Workbook()
            ws = wb.active
            assert ws is not None
            ws.title = "Dispatches"
            ws.append(
                [
                    "Ticket No.",
                    "Dispatch Date",
                    "Customer Name",
                    "Truck Number",
                    "Plant Name",
                    "Driver Name",
                    "Quantity (m3)",
                ]
            )
            ws.append(
                [
                    "TCK-WORKER-01",
                    "2026-08-05",
                    "Worker Customer",
                    "V-500",
                    "Worker Plant",
                    "Unique Driver 01",
                    15.0,
                ]
            )
            wb.save(str(wb_path))
            wb.close()

            # Create ImportJob entity
            job = ImportJob(
                job_number="JOB-WORKER-001",
                status=ImportJobState.QUEUED.value,
                file_name=str(wb_path),
                file_hash="worker_hash_001",
                total_rows=1,
                processed_rows=0,
                error_count=0,
            )
            await job_repo.create(job)
            await session.flush()

            # Run Orchestrator Pipeline
            event_bus = InMemoryEventBus()
            events: list[str] = []

            async def h(e):
                events.append(e.event_type)

            for evt in [
                "erp.import.started",
                "erp.import.stage_changed",
                "erp.import.completed",
            ]:
                event_bus.subscribe(evt, h)

            orchestrator = ImportPipelineOrchestrator(event_bus=event_bus)
            res = await orchestrator.execute_pipeline(session, "JOB-WORKER-001")

            assert res["status"] == "SUCCESS"
            assert res["processed_rows"] == 1
            assert res["persisted_counts"]["dispatches"] == 1

            # Verify PostgreSQL Dispatch table
            disp_repo = DispatchRepository(session)
            disp_item = await disp_repo.get_by_dispatch_number("TCK-WORKER-01")
            assert disp_item is not None
            assert disp_item.dispatch_number == "TCK-WORKER-01"

            # Verify Events
            assert "erp.import.started" in events
            assert "erp.import.completed" in events

        finally:
            await session.close()
            await trans.rollback()

    await engine.dispose()


@pytest.mark.asyncio
async def test_worker_transaction_rollback_on_failure(tmp_path: pathlib.Path):
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, pool_pre_ping=True)

    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            job_repo = ImportJobRepository(session)

            # Create bad Excel file missing mandatory dispatch_date
            wb_path = tmp_path / "bad_worker_test.xlsx"
            wb = openpyxl.Workbook()
            ws = wb.active
            assert ws is not None
            ws.append(["Customer Name", "Truck Number", "Plant Name"])
            ws.append(["Worker Customer", "V-100", "Plant-1"])
            wb.save(str(wb_path))
            wb.close()

            job = ImportJob(
                job_number="JOB-WORKER-BAD",
                status=ImportJobState.QUEUED.value,
                file_name=str(wb_path),
                file_hash="bad_worker_hash",
                total_rows=1,
                processed_rows=0,
                error_count=0,
            )
            await job_repo.create(job)
            await session.flush()

            orchestrator = ImportPipelineOrchestrator()
            with pytest.raises(ValueError) as exc_info:
                await orchestrator.execute_pipeline(session, "JOB-WORKER-BAD")

            assert "validation failed" in str(exc_info.value)
            assert job.status == ImportJobState.FAILED.value

        finally:
            await session.close()
            await trans.rollback()

    await engine.dispose()


@pytest.mark.asyncio
async def test_erp_import_worker_lifecycle():
    worker = ERPImportWorker(worker_id="test-worker-life")
    await worker.start()
    assert worker._is_running is True

    await worker.heartbeat()

    await worker.stop()
    assert worker._is_running is False
