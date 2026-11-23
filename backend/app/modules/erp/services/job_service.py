"""
Complete ImportJob Lifecycle, Duplicate Detection & Storage Cleanup Engine
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainValidationError, RecordNotFoundError
from app.modules.erp.models import ImportAuditLog, ImportFile, ImportJob
from app.modules.erp.repositories import ImportJobRepository
from app.modules.erp.services.checksum import ChecksumService
from app.modules.erp.services.state_machine import ImportJobState, ImportStateMachine
from app.modules.erp.storage.provider import BaseStorageProvider


class ImportJobService:
    """
    Core Domain Service managing ImportJob state transitions, duplicate workbook detection,
    cancellation, retry policies, and storage cleanup.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        job_repository: ImportJobRepository,
        storage_provider: BaseStorageProvider,
        checksum_service: ChecksumService,
    ):
        self.db = db_session
        self.job_repository = job_repository
        self.storage = storage_provider
        self.checksum_service = checksum_service

    async def create_import_job(
        self,
        file_name: str,
        file_bytes: bytes,
        job_number_override: str | None = None,
        uploader_id: Any | None = None,
        uploader_name: str | None = None,
    ) -> ImportJob:
        """
        Create a new ImportJob, check for duplicate SHA-256 workbooks,
        and store the complete file buffer to storage.
        """
        file_hash = ChecksumService.compute_bytes_sha256(file_bytes)

        # Duplicate Workbook Detection
        existing_job = await self.check_duplicate_workbook(file_hash)
        if existing_job:
            raise DomainValidationError(
                f"Duplicate workbook detected! File SHA-256 hash '{file_hash}' already imported "
                f"by ImportJob '{existing_job.job_number}' (Status: {existing_job.status})."
            )

        import uuid
        from datetime import datetime, timezone

        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        job_number = job_number_override or f"JOB-{today_str}-{uuid.uuid4().hex[:8].upper()}"

        now = datetime.now(timezone.utc)
        display_uploader = uploader_name or "admin"
        job = ImportJob(
            job_number=job_number,
            status=ImportJobState.QUEUED.value,
            file_name=file_name,
            file_hash=file_hash,
            total_rows=0,
            processed_rows=0,
            error_count=0,
            created_at=now,
            updated_at=now,
            created_by=uploader_id,
            source_lineage={
                "uploaded_by": display_uploader,
                "uploader_id": str(uploader_id) if uploader_id else None,
            },
        )
        await self.job_repository.create(job)
        await self.db.flush()

        # Save workbook file
        relative_path = f"workbooks/{job.id}/{file_name}"
        await self.storage.save_file(relative_path, file_bytes)

        # Audit Log
        audit = ImportAuditLog(
            job_id=job.id,
            action="JOB_CREATED",
            created_by=uploader_id,
            details={
                "file_name": file_name,
                "file_hash": file_hash,
                "file_size_bytes": len(file_bytes),
                "uploaded_by": display_uploader,
            },
        )
        self.db.add(audit)

        # File Metadata Reference
        import_file = ImportFile(
            job_id=job.id,
            file_path=relative_path,
            file_size_bytes=len(file_bytes),
        )
        self.db.add(import_file)

        # Transition state to UPLOADED ➔ READY_FOR_PROCESSING
        ImportStateMachine.validate_transition(
            job.status, ImportJobState.UPLOADING.value
        )
        job.status = ImportJobState.UPLOADING.value

        ImportStateMachine.validate_transition(
            job.status, ImportJobState.UPLOADED.value
        )
        job.status = ImportJobState.UPLOADED.value

        ImportStateMachine.validate_transition(
            job.status, ImportJobState.READY_FOR_PROCESSING.value
        )
        job.status = ImportJobState.READY_FOR_PROCESSING.value

        await self.job_repository.update(job)
        await self.db.flush()
        return job

    async def check_duplicate_workbook(self, file_hash: str) -> ImportJob | None:
        """Find an active or completed ImportJob with the exact same file_hash."""
        stmt = select(ImportJob).where(
            ImportJob.file_hash == file_hash,
            ImportJob.is_deleted.is_(False),
            ImportJob.status.in_(
                [
                    ImportJobState.QUEUED.value,
                    ImportJobState.UPLOADING.value,
                    ImportJobState.UPLOADED.value,
                    ImportJobState.READY_FOR_PROCESSING.value,
                ]
            ),
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def cancel_job(
        self, job_number: str, reason: str = "User requested cancellation"
    ) -> ImportJob:
        """Cancel an in-flight or queued ImportJob and clean up storage artifacts."""
        job = await self.job_repository.get_by_job_number(job_number)
        if not job:
            raise RecordNotFoundError(f"ImportJob {job_number} not found")

        ImportStateMachine.validate_transition(
            job.status, ImportJobState.CANCELLED.value
        )
        job.status = ImportJobState.CANCELLED.value
        await self.job_repository.update(job)

        audit = ImportAuditLog(
            job_id=job.id,
            action="JOB_CANCELLED",
            details={"reason": reason},
        )
        self.db.add(audit)
        await self.db.flush()

        # Storage cleanup
        relative_path = f"workbooks/{job.id}/{job.file_name}"
        await self.storage.delete_file(relative_path)
        return job

    async def retry_job(self, job_number: str) -> ImportJob:
        """Retry a FAILED or CANCELLED ImportJob by resetting state to QUEUED."""
        job = await self.job_repository.get_by_job_number(job_number)
        if not job:
            raise RecordNotFoundError(f"ImportJob {job_number} not found")

        ImportStateMachine.validate_transition(job.status, ImportJobState.QUEUED.value)
        job.status = ImportJobState.QUEUED.value
        job.error_count = 0
        await self.job_repository.update(job)

        audit = ImportAuditLog(
            job_id=job.id,
            action="JOB_RETRIED",
            details={"previous_status": job.status},
        )
        self.db.add(audit)
        await self.db.flush()
        return job

    async def resume_job(self, job_number: str) -> ImportJob:
        """Resume a RESUMABLE ImportJob."""
        job = await self.job_repository.get_by_job_number(job_number)
        if not job:
            raise RecordNotFoundError(f"ImportJob {job_number} not found")

        ImportStateMachine.validate_transition(
            job.status, ImportJobState.UPLOADING.value
        )
        job.status = ImportJobState.UPLOADING.value
        await self.job_repository.update(job)

        audit = ImportAuditLog(
            job_id=job.id,
            action="JOB_RESUMED",
            details={},
        )
        self.db.add(audit)
        await self.db.flush()
        return job

    async def cleanup_job_storage(self, job_number: str) -> bool:
        """Purge stored workbook files for a specific ImportJob."""
        job = await self.job_repository.get_by_job_number(job_number)
        if not job:
            return False

        relative_path = f"workbooks/{job.id}"
        return await self.storage.delete_file(relative_path)
