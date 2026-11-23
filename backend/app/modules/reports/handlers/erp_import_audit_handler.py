from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reports.schemas.report_schemas import ReportStatus
from app.modules.reports.schemas.erp_import_audit_canonical import (
    CanonicalERPImportAuditReport,
    ReportMetadataDTO,
    ERPImportAuditKPISummary,
    ERPImportJobRecord,
)
from app.modules.erp.models import ImportJob


class ERPImportAuditReportHandler:
    """Handler for assembling canonical ERP Import Audit reports from ERP ImportJob Repository/Models."""

    async def build_canonical_report(
        self,
        session: AsyncSession,
        execution_id: str,
        requested_scope: Dict[str, Any],
        effective_scope: Dict[str, Any],
        scope_fingerprint: str,
        requested_by: str = "SYSTEM"
    ) -> CanonicalERPImportAuditReport:
        now_str = datetime.now(timezone.utc).isoformat()
        metadata = ReportMetadataDTO(
            execution_id=execution_id,
            report_id="erp_import_audit",
            report_name="ERP Import Audit Report",
            generated_at=now_str,
            requested_by=requested_by
        )

        try:
            stmt = select(ImportJob).order_by(ImportJob.created_at.desc()).limit(100)
            result = await session.execute(stmt)
            jobs = result.scalars().all()

            records = [
                ERPImportJobRecord(
                    job_id=str(j.id),
                    job_number=j.job_number,
                    status=j.status,
                    provider="ExcelERPProvider",
                    file_name=j.file_name,
                    file_hash=j.file_hash,
                    total_rows=j.total_rows,
                    processed_rows=j.processed_rows,
                    error_count=j.error_count,
                    created_at=j.created_at.isoformat() if j.created_at and hasattr(j.created_at, "isoformat") else (str(j.created_at) if j.created_at else None),
                    updated_at=j.updated_at.isoformat() if j.updated_at and hasattr(j.updated_at, "isoformat") else (str(j.updated_at) if j.updated_at else None)
                )
                for j in jobs
            ]

            total_jobs = len(records)
            total_rcv = sum(r.total_rows for r in records)
            total_proc = sum(r.processed_rows for r in records)
            total_err = sum(r.error_count for r in records)
            success_cnt = sum(1 for r in records if r.status in ["COMPLETED", "SUCCESS"])

            kpis = ERPImportAuditKPISummary(
                total_import_jobs=total_jobs,
                total_rows_received=total_rcv,
                total_rows_processed=total_proc,
                total_errors=total_err,
                successful_jobs_count=success_cnt
            )

            status = ReportStatus.COMPLETED if total_jobs > 0 else ReportStatus.NO_DATA

            return CanonicalERPImportAuditReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=status,
                record_count=total_jobs,
                kpis=kpis,
                records=records,
                exceptions=[]
            )
        except Exception:
            return CanonicalERPImportAuditReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=ReportStatus.NO_DATA,
                record_count=0,
                kpis=ERPImportAuditKPISummary(),
                records=[],
                exceptions=[]
            )
