import asyncio
import logging
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionFactory

from app.modules.reports.models.report_execution import ReportExecutionAudit
from app.modules.reports.schemas.report_schemas import ReportStatus
from app.modules.reports.services.report_service import ReportService
from app.modules.reports.services.report_registry import ReportRegistry
from app.modules.reports.handlers.dispatch_analysis_handler import DispatchAnalysisReportHandler
from app.modules.reports.handlers.site_operations_handler import SiteOperationsReportHandler
from app.modules.reports.handlers.fleet_operations_handler import FleetOperationsReportHandler
from app.modules.reports.handlers.site_comparison_handler import SiteComparisonReportHandler
from app.modules.reports.handlers.dispatch_optimization_handler import DispatchOptimizationReportHandler
from app.modules.reports.handlers.operational_intelligence_handler import OperationalIntelligenceReportHandler
from app.modules.reports.handlers.predictive_intelligence_handler import PredictiveIntelligenceReportHandler
from app.modules.reports.handlers.action_execution_handler import ActionExecutionReportHandler
from app.modules.reports.handlers.alerts_incidents_handler import AlertsIncidentsReportHandler
from app.modules.reports.handlers.timeline_operations_handler import TimelineOperationsReportHandler
from app.modules.reports.handlers.erp_import_audit_handler import ERPImportAuditReportHandler
from app.modules.reports.handlers.erp_data_explorer_handler import ERPDataExplorerReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
import time
from app.modules.reports.storage.artifact_storage import ReportArtifactStorage
from app.modules.reports.services.telemetry import (
    ReportingMetricsCollector,
    REPORT_CANONICAL_ASSEMBLY_DURATION_SECONDS,
    REPORT_RENDER_DURATION_SECONDS
)


logger = logging.getLogger(__name__)

dispatch_handler = DispatchAnalysisReportHandler()
site_operations_handler = SiteOperationsReportHandler()
fleet_operations_handler = FleetOperationsReportHandler()
site_comparison_handler = SiteComparisonReportHandler()
dispatch_optimization_handler = DispatchOptimizationReportHandler()
operational_intelligence_handler = OperationalIntelligenceReportHandler()
predictive_intelligence_handler = PredictiveIntelligenceReportHandler()
action_execution_handler = ActionExecutionReportHandler()
alerts_incidents_handler = AlertsIncidentsReportHandler()
timeline_operations_handler = TimelineOperationsReportHandler()
erp_import_audit_handler = ERPImportAuditReportHandler()
erp_data_explorer_handler = ERPDataExplorerReportHandler()


class ReportBackgroundWorker:
    """
    Background worker process/task manager for asynchronous report execution offloading.
    Protects the HTTP ASGI worker event loop while managing state transitions:
    QUEUED ➔ PROCESSING ➔ COMPLETED / NO_DATA / FAILED
    """

    @classmethod
    async def process_report_task(
        cls,
        execution_id: str,
        report_id: str,
        requested_scope: Dict[str, Any],
        effective_scope: Dict[str, Any],
        requested_by: str,
        session_factory=AsyncSessionFactory

    ):
        async with session_factory() as db:
            execution = await db.get(ReportExecutionAudit, execution_id)
            if not execution:
                logger.error(f"Worker task error: Execution ID '{execution_id}' not found.")
                return

            # State Guard / Idempotency Check
            if execution.status in [ReportStatus.COMPLETED.value, ReportStatus.NO_DATA.value, ReportStatus.FAILED.value]:
                logger.warning(f"Worker task skipped: Execution ID '{execution_id}' is already terminal ({execution.status}).")
                return

            # Transition QUEUED ➔ PROCESSING
            execution.status = ReportStatus.PROCESSING.value
            await db.commit()

            t_start = time.perf_counter()
            try:
                t_canon_start = time.perf_counter()
                # Dispatch to appropriate handler
                if report_id == "site_operations":
                    canonical_report = await site_operations_handler.build_canonical_report(
                        session=db, execution_id=execution_id, requested_scope=requested_scope,
                        effective_scope=effective_scope, scope_fingerprint=execution.scope_fingerprint, requested_by=requested_by
                    )
                elif report_id == "fleet_operations":
                    canonical_report = await fleet_operations_handler.build_canonical_report(
                        session=db, execution_id=execution_id, requested_scope=requested_scope,
                        effective_scope=effective_scope, scope_fingerprint=execution.scope_fingerprint, requested_by=requested_by
                    )
                elif report_id == "site_comparison":
                    canonical_report = await site_comparison_handler.build_canonical_report(
                        session=db, execution_id=execution_id, requested_scope=requested_scope,
                        effective_scope=effective_scope, scope_fingerprint=execution.scope_fingerprint, requested_by=requested_by
                    )
                elif report_id == "dispatch_optimization":
                    canonical_report = await dispatch_optimization_handler.build_canonical_report(
                        session=db, execution_id=execution_id, requested_scope=requested_scope,
                        effective_scope=effective_scope, scope_fingerprint=execution.scope_fingerprint, requested_by=requested_by
                    )
                elif report_id == "operational_intelligence":
                    canonical_report = await operational_intelligence_handler.build_canonical_report(
                        session=db, execution_id=execution_id, requested_scope=requested_scope,
                        effective_scope=effective_scope, scope_fingerprint=execution.scope_fingerprint, requested_by=requested_by
                    )
                elif report_id == "predictive_intelligence":
                    canonical_report = await predictive_intelligence_handler.build_canonical_report(
                        session=db, execution_id=execution_id, requested_scope=requested_scope,
                        effective_scope=effective_scope, scope_fingerprint=execution.scope_fingerprint, requested_by=requested_by
                    )
                elif report_id == "action_execution":
                    canonical_report = await action_execution_handler.build_canonical_report(
                        session=db, execution_id=execution_id, requested_scope=requested_scope,
                        effective_scope=effective_scope, scope_fingerprint=execution.scope_fingerprint, requested_by=requested_by
                    )
                elif report_id == "alerts_incidents":
                    canonical_report = await alerts_incidents_handler.build_canonical_report(
                        session=db, execution_id=execution_id, requested_scope=requested_scope,
                        effective_scope=effective_scope, scope_fingerprint=execution.scope_fingerprint, requested_by=requested_by
                    )
                elif report_id == "timeline_operations":
                    canonical_report = await timeline_operations_handler.build_canonical_report(
                        session=db, execution_id=execution_id, requested_scope=requested_scope,
                        effective_scope=effective_scope, scope_fingerprint=execution.scope_fingerprint, requested_by=requested_by
                    )
                elif report_id == "erp_import_audit":
                    canonical_report = await erp_import_audit_handler.build_canonical_report(
                        session=db, execution_id=execution_id, requested_scope=requested_scope,
                        effective_scope=effective_scope, scope_fingerprint=execution.scope_fingerprint, requested_by=requested_by
                    )
                elif report_id == "erp_data_explorer":
                    canonical_report = await erp_data_explorer_handler.build_canonical_report(
                        session=db, execution_id=execution_id, requested_scope=requested_scope,
                        effective_scope=effective_scope, scope_fingerprint=execution.scope_fingerprint, requested_by=requested_by
                    )
                else:
                    canonical_report = await dispatch_handler.build_canonical_report(
                        session=db, execution_id=execution_id, requested_by=requested_by,
                        requested_scope=requested_scope, effective_scope=effective_scope,
                        status=ReportStatus.COMPLETED if execution.record_count > 0 else ReportStatus.NO_DATA
                    )

                t_canon_duration = time.perf_counter() - t_canon_start
                REPORT_CANONICAL_ASSEMBLY_DURATION_SECONDS.labels(report_id=report_id).observe(t_canon_duration)

                # Render into JSON, XLSX, and PDF formats
                t_render_start = time.perf_counter()
                json_bytes = JSONReportRenderer.render(canonical_report)
                xlsx_bytes = XLSXReportRenderer.render(canonical_report)
                pdf_bytes = PDFReportRenderer.render(canonical_report)
                t_render_duration = time.perf_counter() - t_render_start
                REPORT_RENDER_DURATION_SECONDS.labels(format="MULTI").observe(t_render_duration)

                # Save artifacts securely into storage/reports/{execution_id}/
                ReportArtifactStorage.save_artifacts(
                    execution_id=execution_id,
                    artifacts={"json": json_bytes, "xlsx": xlsx_bytes, "pdf": pdf_bytes}
                )

                # Transition to COMPLETED / NO_DATA terminal status
                rec_count = getattr(canonical_report, "record_count", execution.record_count)
                final_status = ReportStatus.NO_DATA.value if rec_count == 0 else ReportStatus.COMPLETED.value
                execution.status = final_status
                execution.record_count = rec_count
                await db.commit()

                t_total_duration = time.perf_counter() - t_start
                ReportingMetricsCollector.record_completion(
                    report_id=report_id,
                    format_str=execution.format,
                    duration_sec=t_total_duration,
                    record_count=rec_count
                )

                logger.info(
                    "Worker execution completed successfully",
                    extra={
                        "execution_id": execution_id,
                        "report_id": report_id,
                        "status": final_status,
                        "record_count": rec_count,
                        "duration_ms": round(t_total_duration * 1000, 2)
                    }
                )

            except Exception as exc:
                import traceback
                tb_str = traceback.format_exc()
                t_total_duration = time.perf_counter() - t_start
                logger.error(f"Worker execution failed for Execution ID '{execution_id}': {exc}\n{tb_str}", exc_info=True)
                
                # Cleanup any partial artifacts generated prior to failure
                try:
                    ReportArtifactStorage.purge_execution_artifacts(execution_id)
                except Exception:
                    pass

                error_cat = "TIMEOUT" if "Timeout" in str(exc) or "timeout" in str(exc) else "INTERNAL_ERROR"

                ReportingMetricsCollector.record_failure(
                    report_id=report_id,
                    format_str=execution.format,
                    error_category=error_cat
                )
                # Extract last line of traceback for UI visibility
                tb_lines = [line.strip() for line in tb_str.strip().split("\n") if line.strip()]
                last_tb_location = tb_lines[-2] if len(tb_lines) >= 2 else "Unknown Location"

                # Failure Recovery: Transition PROCESSING ➔ FAILED
                execution.status = ReportStatus.FAILED.value
                execution.error_code = "REPORT_GENERATION_FAILED"
                execution.error_message = f"Report execution failed ({type(exc).__name__}): {str(exc)} at {last_tb_location}"
                await db.commit()




