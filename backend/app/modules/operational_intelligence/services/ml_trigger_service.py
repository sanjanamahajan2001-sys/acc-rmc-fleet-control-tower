import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_intelligence.models.ml_lifecycle_trigger import MLLifecycleTrigger

logger = logging.getLogger(__name__)


class MLTriggerService:
    """
    WS-10.1 Authoritative ML Lifecycle Trigger Evaluation & Management Service.
    Connects ERP persistence completion events to durable PostgreSQL triggers.
    Enforces dispatch thresholds (>= 100), 6-hour debounce windows, idempotency,
    and FOR UPDATE row-level locking for concurrent execution protection.
    """

    MIN_NEW_DISPATCHES = 100
    DEFAULT_COOLDOWN_HOURS = 6.0

    @staticmethod
    async def evaluate_and_create_trigger(
        session: AsyncSession,
        import_job_id: uuid.UUID | None,
        job_number: str,
        dataset_id: str,
        model_family: str = "ALL_FAMILIES",
        new_dispatches_in_batch: int = 0,
        request_id: str = "sys-trigger",
    ) -> MLLifecycleTrigger:
        """
        Evaluates an ERP import persistence event and creates an ML trigger record.
        Enforces idempotency, 100-dispatch threshold, 6-hour debouncing cooldown,
        and concurrent job queueing (PENDING_NEXT_RUN).
        """
        # Type coerce new_dispatches_in_batch safely
        try:
            dispatch_count = int(new_dispatches_in_batch)
        except (ValueError, TypeError):
            dispatch_count = 0

        # 1. Idempotency Check: Same job_number duplicate event?
        stmt = select(MLLifecycleTrigger).where(MLLifecycleTrigger.job_number == job_number)
        res = await session.execute(stmt)
        existing = res.scalars().first()
        if existing:
            logger.info(
                f"[WS-10.1 TELEMETRY] Duplicate ERP completion event ignored. "
                f"job_number={job_number}, existing_trigger_id={existing.trigger_id}"
            )
            return existing

        trigger_id = f"trig-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        # 2. Check active RUNNING job for this model family (Concurrent Execution Queueing)
        stmt_running = (
            select(MLLifecycleTrigger)
            .where(
                MLLifecycleTrigger.model_family == model_family,
                MLLifecycleTrigger.status == "RUNNING",
            )
            .with_for_update(skip_locked=False)
        )
        res_running = await session.execute(stmt_running)
        running_job = res_running.scalars().first()

        if running_job:
            logger.info(
                f"[WS-10.1 TELEMETRY] Concurrent RUNNING job active for family={model_family}. "
                f"Queueing trigger as PENDING_NEXT_RUN. job_number={job_number}"
            )
            trigger = MLLifecycleTrigger(
                trigger_id=trigger_id,
                import_job_id=import_job_id,
                job_number=job_number,
                dataset_id=dataset_id,
                model_family=model_family,
                status="PENDING_NEXT_RUN",
                new_dispatch_count=dispatch_count,
                cooldown_hours=MLTriggerService.DEFAULT_COOLDOWN_HOURS,
                reason=f"Active training job is currently RUNNING ({running_job.trigger_id}). Saved for next cycle.",
                created_at=now,
                updated_at=now,
            )
            session.add(trigger)
            return trigger

        # 3. Check 100-dispatch threshold policy
        if dispatch_count < MLTriggerService.MIN_NEW_DISPATCHES:
            logger.info(
                f"[WS-10.1 TELEMETRY] Ingested dispatches ({dispatch_count}) below threshold "
                f"({MLTriggerService.MIN_NEW_DISPATCHES}). Skipping training trigger."
            )
            trigger = MLLifecycleTrigger(
                trigger_id=trigger_id,
                import_job_id=import_job_id,
                job_number=job_number,
                dataset_id=dataset_id,
                model_family=model_family,
                status="SKIPPED_THRESHOLD",
                new_dispatch_count=dispatch_count,
                cooldown_hours=MLTriggerService.DEFAULT_COOLDOWN_HOURS,
                reason=f"Dispatch count ({dispatch_count}) below minimum threshold ({MLTriggerService.MIN_NEW_DISPATCHES})",
                created_at=now,
                updated_at=now,
            )
            session.add(trigger)
            return trigger

        # 4. Check 6-hour debounce cooldown policy
        cutoff = now - timedelta(hours=MLTriggerService.DEFAULT_COOLDOWN_HOURS)
        stmt_cooldown = select(MLLifecycleTrigger).where(
            MLLifecycleTrigger.model_family == model_family,
            MLLifecycleTrigger.status.in_(["COMPLETED", "RUNNING", "PENDING"]),
            MLLifecycleTrigger.created_at >= cutoff,
        )
        res_cooldown = await session.execute(stmt_cooldown)
        recent_trigger = res_cooldown.scalars().first()

        if recent_trigger:
            logger.info(
                f"[WS-10.1 TELEMETRY] Debounce cooldown active for family={model_family}. "
                f"Last trigger created at {recent_trigger.created_at}. Skipping trigger."
            )
            trigger = MLLifecycleTrigger(
                trigger_id=trigger_id,
                import_job_id=import_job_id,
                job_number=job_number,
                dataset_id=dataset_id,
                model_family=model_family,
                status="SKIPPED_COOLDOWN",
                new_dispatch_count=dispatch_count,
                cooldown_hours=MLTriggerService.DEFAULT_COOLDOWN_HOURS,
                reason=f"6-hour debounce cooldown active for family {model_family} (last trigger: {recent_trigger.trigger_id})",
                created_at=now,
                updated_at=now,
            )
            session.add(trigger)
            return trigger

        # 5. Satisfies all rules -> Create PENDING lifecycle trigger
        logger.info(
            f"[WS-10.1 TELEMETRY] Eligible ERP import event. Creating PENDING ML trigger {trigger_id} "
            f"for job_number={job_number}, dispatches={dispatch_count}"
        )
        trigger = MLLifecycleTrigger(
            trigger_id=trigger_id,
            import_job_id=import_job_id,
            job_number=job_number,
            dataset_id=dataset_id,
            model_family=model_family,
            status="PENDING",
            new_dispatch_count=dispatch_count,
            cooldown_hours=MLTriggerService.DEFAULT_COOLDOWN_HOURS,
            reason="ERP persistence threshold satisfied & cooldown clear",
            created_at=now,
            updated_at=now,
        )
        session.add(trigger)
        return trigger

    @staticmethod
    async def get_pending_trigger(
        session: AsyncSession, model_family: str = "ALL_FAMILIES"
    ) -> MLLifecycleTrigger | None:
        """
        Retrieves the oldest PENDING or PENDING_NEXT_RUN trigger for a given model family,
        locking the row with FOR UPDATE to prevent race conditions.
        """
        stmt = (
            select(MLLifecycleTrigger)
            .where(
                MLLifecycleTrigger.model_family == model_family,
                MLLifecycleTrigger.status.in_(["PENDING", "PENDING_NEXT_RUN"]),
            )
            .order_by(MLLifecycleTrigger.created_at.asc())
            .with_for_update(skip_locked=True)
        )
        res = await session.execute(stmt)
        return res.scalars().first()

    @staticmethod
    async def update_trigger_status(
        session: AsyncSession,
        trigger_id: str,
        status: str,
        reason: str | None = None,
        error_metadata: dict[str, Any] | None = None,
    ) -> MLLifecycleTrigger | None:
        """
        Updates the status and lifecycle timestamps of an ML trigger record.
        """
        stmt = select(MLLifecycleTrigger).where(MLLifecycleTrigger.trigger_id == trigger_id)
        res = await session.execute(stmt)
        trig = res.scalars().first()
        if not trig:
            return None

        trig.status = status
        trig.updated_at = datetime.now(timezone.utc)
        if reason is not None:
            trig.reason = reason
        if error_metadata is not None:
            trig.error_metadata = error_metadata

        if status == "RUNNING" and not trig.started_at:
            trig.started_at = datetime.now(timezone.utc)
        elif status in ["COMPLETED", "FAILED", "SKIPPED_THRESHOLD", "SKIPPED_COOLDOWN"]:
            trig.completed_at = datetime.now(timezone.utc)

        return trig

    @staticmethod
    async def retry_failed_trigger(
        session: AsyncSession, trigger_id: str
    ) -> MLLifecycleTrigger | None:
        """
        Safely resets a FAILED trigger to PENDING status for re-execution without duplicate creation.
        """
        stmt = select(MLLifecycleTrigger).where(
            MLLifecycleTrigger.trigger_id == trigger_id,
            MLLifecycleTrigger.status == "FAILED",
        )
        res = await session.execute(stmt)
        trig = res.scalars().first()
        if not trig:
            return None

        trig.status = "PENDING"
        trig.reason = "Manual retry requested"
        trig.started_at = None
        trig.completed_at = None
        trig.error_metadata = None
        trig.updated_at = datetime.now(timezone.utc)
        return trig
