"""
Resumable Upload Session Manager & Chunk Assembly Service
"""

import uuid
from typing import Any

from app.core.exceptions import DomainValidationError, RecordNotFoundError
from app.modules.erp.repositories import ImportJobRepository
from app.modules.erp.services.checksum import ChecksumService
from app.modules.erp.services.state_machine import ImportJobState, ImportStateMachine
from app.modules.erp.storage.provider import BaseStorageProvider


class UploadSessionManager:
    """
    Manages multi-part chunked workbook upload sessions, chunk assembly,
    and resumable upload progress tracking.
    """

    def __init__(
        self,
        storage_provider: BaseStorageProvider,
        checksum_service: ChecksumService,
        job_repository: ImportJobRepository,
    ):
        self.storage = storage_provider
        self.checksum_service = checksum_service
        self.job_repository = job_repository

    async def init_upload_session(
        self,
        job_number: str,
        file_name: str,
        total_chunks: int,
        expected_hash: str | None = None,
    ) -> dict[str, Any]:
        """Initialize a new multi-part chunked upload session for an ImportJob."""
        job = await self.job_repository.get_by_job_number(job_number)
        if not job:
            raise RecordNotFoundError(f"ImportJob {job_number} not found")

        ImportStateMachine.validate_transition(
            job.status, ImportJobState.UPLOADING.value
        )
        job.status = ImportJobState.UPLOADING.value
        await self.job_repository.update(job)

        upload_id = f"upload_{job.id}_{uuid.uuid4().hex[:8]}"

        return {
            "upload_id": upload_id,
            "job_number": job_number,
            "file_name": file_name,
            "total_chunks": total_chunks,
            "expected_hash": expected_hash,
            "received_chunks": 0,
        }

    async def receive_chunk(
        self,
        upload_id: str,
        chunk_index: int,
        total_chunks: int,
        chunk_data: bytes,
    ) -> dict[str, Any]:
        """Receive and store an individual chunk for an active upload session."""
        if chunk_index < 0 or chunk_index >= total_chunks:
            raise DomainValidationError(
                f"Invalid chunk_index {chunk_index} for total_chunks {total_chunks}"
            )

        chunk_path = await self.storage.save_chunk(upload_id, chunk_index, chunk_data)

        return {
            "upload_id": upload_id,
            "chunk_index": chunk_index,
            "chunk_size_bytes": len(chunk_data),
            "chunk_path": chunk_path,
        }

    async def finalize_upload(
        self,
        job_number: str,
        upload_id: str,
        total_chunks: int,
        expected_sha256: str | None = None,
    ) -> dict[str, Any]:
        """
        Assemble all chunks into the final target workbook, verify SHA-256 integrity,
        and transition job to UPLOADED / READY_FOR_PROCESSING.
        """
        job = await self.job_repository.get_by_job_number(job_number)
        if not job:
            raise RecordNotFoundError(f"ImportJob {job_number} not found")

        target_relative_path = f"workbooks/{job.id}/{job.file_name}"
        assembled_path = await self.storage.assemble_chunks(
            upload_id, total_chunks, target_relative_path
        )

        # Compute actual checksum of assembled file
        actual_hash = await self.checksum_service.compute_file_hash(
            target_relative_path
        )

        # Integrity Check if expected hash was provided
        if expected_sha256 and actual_hash.lower() != expected_sha256.lower():
            await self.storage.delete_file(target_relative_path)
            job.status = ImportJobState.FAILED.value
            job.error_count += 1
            await self.job_repository.update(job)
            raise DomainValidationError(
                f"File checksum mismatch! Expected '{expected_sha256}', got '{actual_hash}'"
            )

        job.file_hash = actual_hash
        ImportStateMachine.validate_transition(
            job.status, ImportJobState.UPLOADED.value
        )
        job.status = ImportJobState.UPLOADED.value
        await self.job_repository.update(job)

        # Immediate transition to READY_FOR_PROCESSING
        ImportStateMachine.validate_transition(
            job.status, ImportJobState.READY_FOR_PROCESSING.value
        )
        job.status = ImportJobState.READY_FOR_PROCESSING.value
        await self.job_repository.update(job)

        return {
            "job_number": job_number,
            "status": job.status,
            "file_hash": actual_hash,
            "storage_path": assembled_path,
        }
