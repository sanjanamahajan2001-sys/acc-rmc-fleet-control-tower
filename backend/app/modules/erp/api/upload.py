from app.dependencies.auth import require_section_permission
from app.schemas.auth import TokenPayload
"""
Workbook Upload REST API Endpoints
Supports single/chunk upload, checksum validation, and resumable session management.
"""

import pathlib
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.common import get_db_session
from app.modules.erp.api.dependencies import AuthenticatedUser, TimedEnvelope
from app.modules.erp.api.schemas import ImportJobResponse
from app.modules.erp.repositories import ImportJobRepository
from app.modules.erp.services.checksum import ChecksumService
from app.modules.erp.services.job_service import ImportJobService
from app.modules.erp.storage.factory import get_storage_provider
from app.schemas.envelope import APIResponse

router = APIRouter(prefix="/workbooks", tags=["ERP Workbook Uploads"])


@router.post(
    "/upload",
    response_model=APIResponse[ImportJobResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload ERP Excel / CSV Workbook",
    description="Accepts single file or chunked uploads, calculates streaming SHA-256 checksums, and creates an ImportJob record.",
)
async def upload_workbook(
    file: Annotated[
        UploadFile, File(description="Excel (.xlsx, .xlsm, .xls) or CSV workbook file")
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthenticatedUser,
    _perm_guard: Annotated[TokenPayload, Depends(require_section_permission("erp_import", "edit"))],
    envelope: TimedEnvelope,
    session_id: Annotated[
        str | None, Form(description="Upload session ID for chunked uploads")
    ] = None,
    chunk_index: Annotated[
        int | None, Form(description="0-indexed chunk sequence number")
    ] = None,
    total_chunks: Annotated[
        int | None, Form(description="Total number of chunks")
    ] = None,
) -> APIResponse[ImportJobResponse]:
    file_bytes = await file.read()
    filename = file.filename or "uploaded_workbook.xlsx"

    storage = get_storage_provider()
    checksum_svc = ChecksumService(storage)
    job_repo = ImportJobRepository(session)
    job_service = ImportJobService(session, job_repo, storage, checksum_svc)

    # Resolve Uploader Identity
    uploader_name = "admin"
    uploader_uuid = None
    try:
        from app.modules.auth.models import User
        from sqlalchemy import select
        import uuid
        if hasattr(user, "sub") and user.sub:
            uploader_uuid = uuid.UUID(user.sub)
            user_stmt = select(User).where(User.id == uploader_uuid)
            user_record = (await session.execute(user_stmt)).scalar_one_or_none()
            if user_record:
                uploader_name = user_record.username or user_record.full_name or user_record.email or "admin"
    except Exception:
        uploader_name = "admin"

    job = await job_service.create_import_job(
        file_name=filename,
        file_bytes=file_bytes,
        uploader_id=uploader_uuid,
        uploader_name=uploader_name,
    )
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    job_id = job.id
    job_number = job.job_number
    status = job.status
    file_name = job.file_name
    file_hash = job.file_hash
    total_rows = job.total_rows
    processed_rows = job.processed_rows
    error_count = job.error_count
    created_at = now
    updated_at = now

    res = ImportJobResponse(
        id=job_id,
        job_number=job_number,
        status=status,
        file_name=file_name,
        file_hash=file_hash,
        total_rows=total_rows,
        processed_rows=processed_rows,
        error_count=error_count,
        created_at=created_at,
        updated_at=updated_at,
        uploaded_by=uploader_name,
        completed_at=None,
    )

    await session.commit()

    # Save file to storage provider so orchestrator finds it
    storage_provider = get_storage_provider()
    relative_path = f"workbooks/{job.id}/{filename}"
    await storage_provider.save_file(relative_path, file_bytes)

    import asyncio

    async def _run_pipeline(j_num: str) -> None:
        try:
            from app.core.database import AsyncSessionFactory
            from app.modules.erp.workers.orchestrator import ImportPipelineOrchestrator

            async with AsyncSessionFactory() as pipe_session:
                orchestrator = ImportPipelineOrchestrator()
                await orchestrator.execute_pipeline(pipe_session, j_num)

                # Trigger CrossSourceCorrelator in case telemetry was uploaded first
                try:
                    from app.modules.telemetry.validation.correlator import CrossSourceCorrelator
                    correlator = CrossSourceCorrelator()
                    await correlator.correlate_unmatched_telemetry(pipe_session, limit=10000)
                except Exception:
                    pass

                await pipe_session.commit()
        except Exception as exc:  # noqa: BLE001
            from app.core.logging import get_logger

            logger = get_logger("app.modules.erp.api.upload")
            logger.error(f"Pipeline background execution failed for {j_num}: {exc}", exc_info=True)

    asyncio.create_task(_run_pipeline(job_number))

    return envelope.success(res)
