import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_intelligence.services.ml_trigger_service import MLTriggerService

logger = logging.getLogger(__name__)


class ERPTriggerListener:
    """
    WS-10.1 ERP Trigger Listener.
    Consumes ERP import persistence completion events and delegates trigger evaluation to MLTriggerService.
    """

    @staticmethod
    async def on_erp_import_completed(
        session: AsyncSession,
        event_payload: dict[str, Any],
        correlation_id: str = "sys-trigger-listener",
        request_id: str = "sys-trigger-listener",
    ) -> Any:
        """
        Handler invoked when ERP persistence stage completes.
        Payload expects: job_number, processed_rows, persisted_counts (or counts).
        """
        if not isinstance(event_payload, dict):
            logger.error(
                f"[WS-10.1 EVENT ERROR] Received non-dict payload: {type(event_payload)}. Skipping trigger."
            )
            return None

        job_number = event_payload.get("job_number")
        if not job_number:
            logger.error("[WS-10.1 EVENT ERROR] Missing job_number in event payload")
            return None

        dataset_id = event_payload.get("dataset_id", job_number)
        model_family = event_payload.get("model_family", "ALL_FAMILIES")
        import_job_id = event_payload.get("import_job_id")

        # Ingested dispatch count
        counts = event_payload.get("counts") or event_payload.get("persisted_counts") or {}
        new_dispatches = counts.get("dispatches", event_payload.get("processed_rows", 0))

        try:
            from app.modules.operational_intelligence.services.refresh_service import WS10ContinuousMLRefreshService
            from app.modules.operational_intelligence.services.active_inference_service import WS10ActiveModelInferenceService

            refresh_summary = await WS10ContinuousMLRefreshService.execute_automatic_refresh_pipeline(
                session=session,
                job_number=job_number,
                import_job_id=import_job_id,
                new_dispatches_in_batch=new_dispatches,
            )

            inference_summary = await WS10ActiveModelInferenceService.execute_batch_inference_for_new_dispatches(
                session=session,
                job_number=job_number,
                import_job_id=import_job_id,
            )

            # Phase 4 ERP Change Dependency & Invalidation Chain Integration
            updated_dispatch_id = event_payload.get("updated_dispatch_id") or event_payload.get("dispatch_id")
            changed_fields = event_payload.get("changed_fields")

            invalidation_summary = None
            if updated_dispatch_id:
                from app.modules.operational_intelligence.services.erp_invalidation_service import ERPInvalidationService
                invalidation_summary = await ERPInvalidationService.process_erp_dispatch_change(
                    session=session,
                    dispatch_id=updated_dispatch_id,
                    changed_fields=changed_fields,
                )

            logger.info(
                f"[WS-10.10 EVENT LISTENER] Continuous ML refresh & Phase 1 active inference completed for job_number={job_number}. "
                f"Candidates: {len(refresh_summary.get('promotion_eligible_candidates', []))}, "
                f"Snapshots Created: {inference_summary.get('snapshots_created', 0)}"
            )

            return {
                "refresh_summary": refresh_summary,
                "inference_summary": inference_summary,
                "invalidation_summary": invalidation_summary,
            }
        except Exception as e:
            logger.error(
                f"[WS-10.10 EVENT LISTENER ERROR] Exception during trigger execution: {str(e)}",
                exc_info=True,
            )
            # Safe isolation: do not re-raise; allow ERP import persistence to conclude cleanly
            return None
