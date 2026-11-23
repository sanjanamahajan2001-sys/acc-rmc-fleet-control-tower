import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.modules.reports.models.report_execution import ReportExecutionAudit
from app.modules.reports.schemas.report_schemas import ReportStatus, ScopeValidationStatus, ReportFormat


class ReportService:
    async def create_execution_record(
        self,
        session: AsyncSession,
        report_id: str,
        report_type: str,
        format: str,
        requested_by: str,
        requested_scope: Dict[str, Any],
        effective_scope: Dict[str, Any],
        scope_fingerprint: str,
        validation_status: str,
        record_count: int = 0,
        dataset_id: Optional[str] = None,
        status: str = "QUEUED",
        error_code: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> ReportExecutionAudit:
        from datetime import timedelta
        from app.core.config import settings

        now_utc = datetime.now(timezone.utc)
        retention_days = max(1, settings.REPORT_ARTIFACT_RETENTION_DAYS)
        expires_at = now_utc + timedelta(days=retention_days)

        execution = ReportExecutionAudit(
            execution_id=f"REPLOG-{uuid.uuid4().hex[:12]}",
            report_id=report_id,
            report_type=report_type,
            format=format,
            requested_by=requested_by,
            requested_at=now_utc,
            requested_scope=requested_scope,
            effective_scope=effective_scope,
            scope_fingerprint=scope_fingerprint,
            scope_validation_status=validation_status,
            record_count=record_count,
            dataset_id=dataset_id,
            status=status,
            error_code=error_code,
            error_message=error_message,
            retention_expires_at=expires_at
        )

        session.add(execution)
        await session.commit()
        await session.refresh(execution)
        return execution

    async def list_executions(
        self,
        session: AsyncSession,
        limit: int = 50,
        offset: int = 0
    ) -> List[ReportExecutionAudit]:
        query = select(ReportExecutionAudit).order_by(desc(ReportExecutionAudit.requested_at)).limit(limit).offset(offset)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def purge_expired_artifacts(self, session: AsyncSession) -> Dict[str, Any]:
        """
        Scans for expired artifacts beyond retention_expires_at and safely purges files.
        Also performs orphan directory cleanup for deleted/missing execution records.
        Preserves historical audit log record intact while updating status to PURGED.
        """
        now_utc = datetime.now(timezone.utc)
        query = select(ReportExecutionAudit).where(
            ReportExecutionAudit.retention_expires_at <= now_utc,
            ReportExecutionAudit.status.in_([ReportStatus.COMPLETED.value, ReportStatus.NO_DATA.value])
        )
        result = await session.execute(query)
        expired_executions = list(result.scalars().all())

        scanned = len(expired_executions)
        purged = 0
        failed = 0
        reclaimed_bytes = 0

        from app.modules.reports.storage.artifact_storage import ReportArtifactStorage
        from app.modules.reports.services.telemetry import ARTIFACT_PURGE_TOTAL, ARTIFACT_PURGE_FAILURES_TOTAL

        for exec_record in expired_executions:
            try:
                bytes_freed = ReportArtifactStorage.purge_execution_artifacts(exec_record.execution_id)
                reclaimed_bytes += bytes_freed
                exec_record.status = "PURGED"
                purged += 1
                ARTIFACT_PURGE_TOTAL.labels(purge_type="expired").inc()
            except Exception:
                failed += 1
                ARTIFACT_PURGE_FAILURES_TOTAL.inc()

        await session.commit()

        # Orphan directory cleanup logic
        all_execs_query = select(ReportExecutionAudit.execution_id)
        all_execs_result = await session.execute(all_execs_query)
        valid_exec_ids = set(all_execs_result.scalars().all())
        orphans_purged = ReportArtifactStorage.cleanup_orphan_directories(valid_exec_ids)
        if orphans_purged > 0:
            ARTIFACT_PURGE_TOTAL.labels(purge_type="orphan").inc(orphans_purged)


        return {
            "scanned": scanned,
            "eligible": scanned,
            "purged": purged,
            "failed": failed,
            "orphans_purged": orphans_purged,
            "reclaimed_bytes": reclaimed_bytes
        }



