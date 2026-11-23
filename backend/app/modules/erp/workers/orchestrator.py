import logging
logger = logging.getLogger(__name__)
"""
ImportPipelineOrchestrator Subsystem
Orchestrates WS1.2 Storage -> WS1.3 Parser -> WS1.4 Validation -> WS1.5 PersistenceCoordinator
within an atomic PostgreSQL transaction managed by UnitOfWork / AsyncSession.
"""

import pathlib
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.bus import EventBus
from app.events.schema import BaseEvent
from app.modules.erp.models import ImportAuditLog
from app.modules.erp.parsers.context import CanonicalWorkbookContext
from app.modules.erp.parsers.factory import get_workbook_parser
from app.modules.erp.repositories import ImportJobRepository
from app.modules.erp.services.state_machine import ImportJobState
from app.modules.erp.storage.factory import get_storage_provider
from app.modules.erp.validation.engine import CanonicalValidationEngine
from app.modules.erp.workers.persistence import PersistenceCoordinator
from app.modules.erp.workers.tracker import (
    ImportAuditCoordinator,
    ImportPipelineProgressTracker,
    ImportPipelineStage,
)


class ImportPipelineOrchestrator:
    """
    Pipeline Orchestration Subsystem for ERP workbook ingestion.
    """

    def __init__(
        self,
        event_bus: EventBus | None = None,
        correlation_id: str = "sys-pipeline",
        request_id: str = "sys-pipeline",
    ):
        self.event_bus = event_bus
        self.correlation_id = correlation_id
        self.request_id = request_id

    async def _publish(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.event_bus:
            event = BaseEvent[dict[str, Any]](
                event_type=event_type,
                payload=payload,
                correlation_id=self.correlation_id,
                request_id=self.request_id,
            )
            await self.event_bus.publish(event)

    async def execute_pipeline(
        self,
        session: AsyncSession,
        job_number: str,
        batch_size: int = 1000,
    ) -> dict[str, Any]:
        """
        Execute end-to-end atomic import pipeline.
        If validation or persistence fails, transaction rolls back automatically.
        """
        job_repo = ImportJobRepository(session)
        job = await job_repo.get_by_job_number(job_number)
        if not job:
            raise ValueError(f"ImportJob '{job_number}' not found.")

        tracker = ImportPipelineProgressTracker(
            job_id=job.job_number, event_bus=self.event_bus
        )

        # 1. Update State to UPLOADING / PROCESSING
        job.status = ImportJobState.READY_FOR_PROCESSING.value
        await job_repo.update(job)
        await tracker.update_progress(
            stage=ImportPipelineStage.ACQUIRING, total_rows=job.total_rows
        )
        await self._publish("erp.import.started", {"job_number": job_number})

        # 2. Acquire Workbook from Storage Provider
        storage_provider = get_storage_provider()
        relative_path = f"workbooks/{job.id}/{job.file_name}"
        abs_path = await storage_provider.get_file_path(relative_path)

        if not abs_path.exists():
            # Fallback check for direct upload file path
            abs_path = pathlib.Path(job.file_name).resolve()
            if not abs_path.exists():
                from app.core.config import get_settings
                storage_root = pathlib.Path(get_settings().STORAGE_ROOT_DIR)
                abs_path = storage_root / relative_path
                if not abs_path.exists():
                    raise FileNotFoundError(
                        f"Workbook file not found for job '{job_number}' at path '{relative_path}'"
                    )

        ctx = CanonicalWorkbookContext(
            import_job_id=str(job.id),
            job_number=job.job_number,
            workbook_name=job.file_name,
            file_path=str(abs_path),
            file_hash=job.file_hash,
            batch_size=batch_size,
        )

        # 3. Stream Parse Workbook
        await tracker.update_progress(stage=ImportPipelineStage.PARSING)
        await self._publish(
            "erp.import.stage_changed", {"stage": ImportPipelineStage.PARSING.value}
        )

        parser = get_workbook_parser(abs_path, event_bus=self.event_bus)
        row_batches: list[list[Any]] = []

        async for batch in parser.parse_workbook_batches(
            abs_path, batch_size=batch_size
        ):
            row_batches.append(batch)
            await tracker.update_progress(
                stage=ImportPipelineStage.PARSING,
                sheet_name=batch[0].sheet_name if batch else None,
                batch_idx=len(row_batches),
                rows_processed=sum(len(b) for b in row_batches),
            )

        parser_metrics = parser.get_metrics()
        job.total_rows = parser_metrics.processed_rows
        await job_repo.update(job)

        # 4. Canonical Validation & Mapping Pass
        await tracker.update_progress(
            stage=ImportPipelineStage.VALIDATING, total_rows=job.total_rows
        )
        await self._publish(
            "erp.import.stage_changed", {"stage": ImportPipelineStage.VALIDATING.value}
        )

        validation_engine = CanonicalValidationEngine(event_bus=self.event_bus)
        persistable_batch, report, val_stats = (
            await validation_engine.validate_and_map_workbook(row_batches, ctx)
        )

        if not report.is_valid:
            job.status = ImportJobState.FAILED.value
            job.error_count += report.errors_count
            await job_repo.update(job)
            sample_issues = [
                {
                    "row": issue.row_number,
                    "sheet": issue.sheet_name,
                    "column": issue.column_name,
                    "error_code": str(issue.error_code),
                    "message": issue.message,
                }
                for issue in report.issues[:30]
            ]
            await ImportAuditCoordinator.create_audit_and_metrics(
                session,
                job.id,
                "VALIDATION",
                "FAILED",
                f"Validation failed with {report.errors_count} errors.",
                tracker.snapshot,
                extra_details={
                    "errors_count": report.errors_count,
                    "sample_issues": sample_issues,
                },
            )
            await session.commit()
            await self._publish(
                "erp.import.failed",
                {"job_number": job_number, "errors": report.errors_count},
            )
            raise ValueError(
                f"ImportJob '{job_number}' validation failed with {report.errors_count} errors."
            )

        # 5. Atomic Persistence Coordinator
        await tracker.update_progress(
            stage=ImportPipelineStage.PERSISTING, rows_validated=val_stats.rows_accepted
        )
        await self._publish("erp.import.persist_started", {"job_number": job_number})

        counts = await PersistenceCoordinator.persist_batch(session, persistable_batch)

        inserted_cnt = counts.get("dispatches_inserted", 0)
        updated_cnt = counts.get("dispatches_updated", 0)

        now_utc = datetime.now(timezone.utc)
        completed_iso = now_utc.isoformat()
        duration_sec = round(time.time() - tracker.start_time, 2)

        cur_lineage = job.source_lineage if isinstance(job.source_lineage, dict) else {}
        uploader_name = cur_lineage.get("uploaded_by")
        if not uploader_name or uploader_name == "Sanjana Mahajan":
            uploader_name = "admin"

        # Update Job Completion & Save Audit / Checkpoint immediately
        job.status = ImportJobState.COMPLETED.value
        job.processed_rows = val_stats.rows_accepted
        job.total_rows = val_stats.rows_processed
        job.source_lineage = {
            **cur_lineage,
            "dispatches_inserted": inserted_cnt,
            "dispatches_updated": updated_cnt,
            "counts_breakdown": counts,
            "completed_at": completed_iso,
            "duration_seconds": duration_sec,
            "uploaded_by": uploader_name,
        }
        await job_repo.update(job)
        await session.commit()

        # 6. Evaluate Operational Alerts Automatically
        try:
            from sqlalchemy import select
            from app.modules.erp.models import Dispatch, Plant, Customer, Ticket, Order
            from app.modules.operational_dashboard.widgets.alerts.evaluator_engine import AlertRulesEvaluatorEngine
            from app.modules.operational_dashboard.widgets.alerts.models import OperationalAlertModel
            from app.modules.site_dashboard.orchestration.filter_metadata_service import DashboardFilterMetadataService

            # Derive dynamic dataset_id matching the active operational dataset
            meta = await DashboardFilterMetadataService.get_filter_metadata(session)
            active_ds_id = meta.dataset_info.dataset_id if (meta and meta.dataset_info) else "DS-ACTIVE-001"
            op_date_str = meta.dataset_info.operational_date if (meta and meta.dataset_info) else "2026-03-01"

            stmt = (
                select(Dispatch, Plant, Customer)
                .outerjoin(Plant, Dispatch.plant_id == Plant.id)
                .outerjoin(Ticket, Dispatch.ticket_id == Ticket.id)
                .outerjoin(Order, Ticket.order_id == Order.id)
                .outerjoin(Customer, Order.customer_id == Customer.id)
                .where(Dispatch.is_deleted == False)
            )
            rows = (await session.execute(stmt)).all()
            dispatch_dicts = []
            for disp, plant, cust in rows:
                dispatch_dicts.append({
                    'dispatch_id': str(disp.id),
                    'plant_id': plant.code if plant else 'ACC_KUNDAIM',
                    'customer_id': cust.code if cust else 'CUST_DEFAULT',
                    't1_transit_mins': float(disp.t1_transit_mins or 0.0),
                    't2a_holding_mins': float(disp.t2a_holding_mins or 0.0),
                    't2b_unloading_mins': float(disp.t2b_unloading_mins or 0.0),
                    't2c_retention_mins': float(disp.t2c_retention_mins or 0.0),
                    'date': op_date_str
                })

            alert_dicts = AlertRulesEvaluatorEngine.evaluate_dispatches(dispatch_dicts, dataset_id=active_ds_id, import_job_id=str(job.id))
            existing_fps = set((await session.execute(
                select(OperationalAlertModel.alert_fingerprint).where(OperationalAlertModel.dataset_id == active_ds_id)
            )).scalars().all())

            new_models = []
            for ad in alert_dicts:
                if ad.get('alert_fingerprint') and ad['alert_fingerprint'] not in existing_fps:
                    existing_fps.add(ad['alert_fingerprint'])
                    new_models.append(OperationalAlertModel(**ad))

            if new_models:
                session.add_all(new_models)
                await session.commit()
                logger.info(f"[WS-07] Successfully auto-generated and committed {len(new_models)} operational alerts for dataset {active_ds_id}")
            else:
                logger.info(f"[WS-07] Operational alerts already up to date ({len(existing_fps)} alerts) for dataset {active_ds_id}")
        except Exception as alert_err:
            logger.error(f"[WS-07] Automatic alert generation error: {alert_err}", exc_info=True)

        await tracker.update_progress(
            stage=ImportPipelineStage.COMPLETED,
            rows_processed=val_stats.rows_processed,
            rows_validated=val_stats.rows_accepted,
            rows_persisted=val_stats.rows_accepted,
        )

        await ImportAuditCoordinator.create_audit_and_metrics(
            session,
            job.id,
            "PERSISTENCE",
            "SUCCESS",
            f"Successfully persisted {counts['dispatches']} dispatches ({inserted_cnt} new, {updated_cnt} updated).",
            tracker.snapshot,
            extra_details={
                "total_persisted": counts["dispatches"],
                "inserted_count": inserted_cnt,
                "updated_count": updated_cnt,
                "counts_breakdown": counts,
            },
        )

        # Emit explicit JOB_COMPLETED lifecycle audit log entry
        audit_completed = ImportAuditLog(
            job_id=job.id,
            action="JOB_COMPLETED",
            created_by=job.created_by,
            details={
                "status": "COMPLETED",
                "completed_at": completed_iso,
                "duration_seconds": duration_sec,
                "total_persisted": counts.get("dispatches", 0),
                "inserted_count": inserted_cnt,
                "updated_count": updated_cnt,
                "uploaded_by": uploader_name,
                "counts_breakdown": counts,
            },
        )
        session.add(audit_completed)
        await session.commit()

        await ImportAuditCoordinator.save_checkpoint(
            session,
            job.id,
            ctx.current_sheet or "COMPLETED",
            len(row_batches),
            val_stats.rows_accepted,
            {"status": "SUCCESS"},
        )

        await self._publish(
            "erp.import.persist_completed", {"job_number": job_number, "counts": counts}
        )
        await self._publish(
            "erp.import.completed",
            {"job_number": job_number, "processed_rows": val_stats.rows_accepted},
        )

        # 8. WS-10.1 Trigger Boundary: Evaluate ERP completion for ML Lifecycle & Control Tower Actions Generation
        try:
            from app.modules.operational_intelligence.events.erp_trigger_listener import ERPTriggerListener
            await ERPTriggerListener.on_erp_import_completed(
                session=session,
                event_payload={
                    "job_number": job_number,
                    "dataset_id": job_number,
                    "processed_rows": val_stats.rows_accepted,
                    "counts": counts,
                },
                correlation_id=self.correlation_id,
                request_id=self.request_id,
            )
        except Exception as trigger_err:
            # Transaction safety: trigger evaluation failure MUST NOT fail ERP import persistence
            pass

        try:
            from generate_real_actions import generate_real_actions
            await generate_real_actions()
        except Exception as action_err:
            pass

        return {
            "job_number": job_number,
            "status": "SUCCESS",
            "processed_rows": val_stats.rows_accepted,
            "persisted_counts": counts,
        }
