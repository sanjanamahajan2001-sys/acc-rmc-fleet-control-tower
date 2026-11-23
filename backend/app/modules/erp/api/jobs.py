"""
Import Job Management REST API Endpoints
Provides endpoints to list, query details, cancel, and retry ERP import jobs.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.common import get_db_session
from app.modules.erp.api.dependencies import AuthenticatedUser, TimedEnvelope
from app.modules.erp.api.schemas import (
    ImportJobResponse,
    JobActionResponse,
    PaginatedResponse,
)
from app.modules.erp.repositories import ImportJobRepository
from app.repositories.pagination import PageRequest
from app.modules.erp.services.checksum import ChecksumService
from app.modules.erp.services.job_service import ImportJobService
from app.modules.erp.storage.factory import get_storage_provider
from app.schemas.envelope import APIResponse

import re

router = APIRouter(prefix="/jobs", tags=["ERP Import Jobs"])


def classify_dataset_file(file_name: str, lineage: dict | None = None) -> tuple[str, str, str]:
    """
    Classifies an ERP workbook into:
    (dataset_key, dataset_period, file_type)

    Resilient matching:
    - Normalizes calendar periods regardless of prefix numbers or naming discrepancies.
    - Uses database lineage (dispatches_inserted vs dispatches_updated) as ground truth.
    - Handles edge cases: missing prefix, differing numbers, full vs abbreviated months.
    """
    clean = (file_name or "").strip()
    lower = clean.lower()
    lineage = lineage or {}

    # 1. Determine file type: Database lineage ground truth first, then filename
    ins = lineage.get("dispatches_inserted") or 0
    upd = lineage.get("dispatches_updated") or 0
    if upd > 0 and ins == 0:
        file_type = "Trip Drum Telemetry"
    elif ins > 0 and upd == 0:
        file_type = "ERP Dispatches"
    elif "drum" in lower or "sensor" in lower or "rotation" in lower:
        file_type = "Trip Drum Telemetry"
    else:
        file_type = "ERP Dispatches"

    # 2. Year normalization
    year = "2026"
    if "2025" in lower or re.search(r"[\s._-]25(\.|\s|_|-|$)", lower):
        year = "2025"
    elif "2024" in lower or re.search(r"[\s._-]24(\.|\s|_|-|$)", lower):
        year = "2024"

    # 3. Normalized calendar period matching (immune to differing or missing prefixes)
    if any(m in lower for m in ["mar", "apr", "march", "april", "03-2026", "04-2026"]):
        period_key = f"{year}-MAR-APR"
        period_label = f"Mar-Apr {year}"
    elif any(m in lower for m in ["jan", "feb", "january", "february", "01-2026", "02-2026"]):
        period_key = f"{year}-JAN-FEB"
        period_label = f"Jan-Feb {year}"
    elif any(m in lower for m in ["jul", "aug", "july", "august", "15-06", "15-08", "07-2025", "08-2025"]):
        period_key = f"{year}-JUL-AUG"
        period_label = f"Jul-Aug {year}"
    elif any(m in lower for m in ["sep", "oct", "september", "october"]):
        period_key = f"{year}-SEP-OCT"
        period_label = f"Sep-Oct {year}"
    elif any(m in lower for m in ["nov", "dec", "november", "december"]):
        period_key = f"{year}-NOV-DEC"
        period_label = f"Nov-Dec {year}"
    elif any(m in lower for m in ["may"]):
        period_key = f"{year}-MAY"
        period_label = f"May {year}"
    else:
        period_key = f"{year}-OPERATIONAL"
        period_label = f"Operational Period {year}"

    # 4. Prefix presentation
    prefix_match = re.match(r"^0?(\d+)[.\s_-]", clean)
    prefix_str = f"Dataset {prefix_match.group(1).zfill(2)}" if prefix_match else "Dataset"

    display_period = f"{prefix_str} ({period_label})"
    return period_key, display_period, file_type


@router.get(
    "",
    response_model=APIResponse[PaginatedResponse[ImportJobResponse]],
    status_code=status.HTTP_200_OK,
    summary="List and Filter ERP Import Jobs",
    description="Returns paginated list of import jobs filtered by status, dates, plant, customer, or search keyword.",
)
async def list_jobs(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthenticatedUser,
    envelope: TimedEnvelope,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=500)] = 20,
    search: Annotated[str | None, Query()] = None,
) -> APIResponse[PaginatedResponse[ImportJobResponse]]:
    job_repo = ImportJobRepository(session)
    page_req = PageRequest(page=page, size=page_size)
    page_result = await job_repo.find(page_request=page_req)

    def _extract_metadata(job):
        lineage = job.source_lineage if isinstance(job.source_lineage, dict) else {}
        ins = lineage.get("dispatches_inserted")
        upd = lineage.get("dispatches_updated")
        uploader = lineage.get("uploaded_by")
        if not uploader or uploader == "Sanjana Mahajan":
            uploader = "admin"
        comp_str = lineage.get("completed_at")
        comp_dt = None
        if comp_str:
            try:
                comp_dt = datetime.fromisoformat(comp_str.replace("Z", "+00:00"))
            except Exception:
                comp_dt = None
        elif job.status == "COMPLETED":
            comp_dt = job.updated_at

        is_reset = bool(lineage.get("is_reset", False))
        reset_str = lineage.get("reset_at")
        reset_dt = None
        if reset_str:
            try:
                reset_dt = datetime.fromisoformat(reset_str.replace("Z", "+00:00"))
            except Exception:
                reset_dt = None

        return ins, upd, uploader, comp_dt, is_reset, reset_dt

    from app.modules.erp.models import Dispatch, ImportJob
    from sqlalchemy import func, select
    active_rows_cnt = (await session.execute(select(func.count()).select_from(Dispatch))).scalar_one() or 0

    # Determine active dataset key from the most recent non-reset completed job across the database
    active_dataset_key = None
    if active_rows_cnt > 0:
        latest_stmt = (
            select(ImportJob)
            .where(
                ImportJob.is_deleted == False,
                ImportJob.status.in_(["COMPLETED", "UPLOADED", "READY_FOR_PROCESSING"]),
            )
            .order_by(ImportJob.created_at.desc())
        )
        candidates = (await session.execute(latest_stmt)).scalars().all()
        for c in candidates:
            c_lineage = c.source_lineage if isinstance(c.source_lineage, dict) else {}
            if not c_lineage.get("is_reset"):
                d_key, _, _ = classify_dataset_file(c.file_name, c_lineage)
                active_dataset_key = d_key
                break

    items = []
    for job in page_result.items:
        ins, upd, uploader, comp_dt, is_reset, reset_dt = _extract_metadata(job)
        lineage = job.source_lineage if isinstance(job.source_lineage, dict) else {}
        d_key, d_period, f_type = classify_dataset_file(job.file_name, lineage)

        is_active = False
        if not is_reset and active_dataset_key and d_key == active_dataset_key:
            is_active = True

        items.append(
            ImportJobResponse(
                id=job.id,
                job_number=job.job_number,
                status=job.status,
                file_name=job.file_name,
                file_hash=job.file_hash,
                total_rows=job.total_rows,
                processed_rows=job.processed_rows,
                error_count=job.error_count,
                created_at=job.created_at,
                updated_at=job.updated_at,
                inserted_rows=ins,
                updated_rows=upd,
                uploaded_by=uploader,
                completed_at=comp_dt,
                is_reset=is_reset,
                reset_at=reset_dt,
                dataset_period=d_period,
                file_type=f_type,
                is_active_dataset=is_active,
            )
        )

    paginated_data = PaginatedResponse[ImportJobResponse](
        items=items,
        total_records=page_result.total_elements,
        page=page,
        page_size=page_size,
        total_pages=page_result.total_pages,
        has_next=page_result.has_next,
        has_previous=page_result.has_previous,
    )

    return envelope.success(paginated_data)


@router.get(
    "/{job_id}",
    response_model=APIResponse[ImportJobResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Complete Import Job Details",
    description="Fetches full details of a specific import job by UUID or job_number.",
)
async def get_job_details(
    job_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthenticatedUser,
    envelope: TimedEnvelope,
) -> APIResponse[ImportJobResponse]:
    job_repo = ImportJobRepository(session)
    job = await job_repo.get_by_job_number(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ImportJob '{job_id}' not found.",
        )

    ins, upd, uploader, comp_dt, is_reset, reset_dt = _extract_metadata(job)
    lineage = job.source_lineage if isinstance(job.source_lineage, dict) else {}
    d_key, d_period, f_type = classify_dataset_file(job.file_name, lineage)

    from app.modules.erp.models import Dispatch, ImportJob
    from sqlalchemy import func, select
    active_rows_cnt = (await session.execute(select(func.count()).select_from(Dispatch))).scalar_one() or 0
    is_active = False
    if not is_reset and active_rows_cnt > 0:
        latest_job = (await session.execute(
            select(ImportJob).order_by(ImportJob.created_at.desc())
        )).scalars().first()
        if latest_job:
            latest_lin = latest_job.source_lineage if isinstance(latest_job.source_lineage, dict) else {}
            latest_key, _, _ = classify_dataset_file(latest_job.file_name, latest_lin)
            if d_key == latest_key:
                is_active = True

    response_data = ImportJobResponse(
        id=job.id,
        job_number=job.job_number,
        status=job.status,
        file_name=job.file_name,
        file_hash=job.file_hash,
        total_rows=job.total_rows,
        processed_rows=job.processed_rows,
        error_count=job.error_count,
        created_at=job.created_at,
        updated_at=job.updated_at,
        inserted_rows=ins,
        updated_rows=upd,
        uploaded_by=uploader,
        completed_at=comp_dt,
        is_reset=is_reset,
        reset_at=reset_dt,
        dataset_period=d_period,
        file_type=f_type,
        is_active_dataset=is_active,
    )
    return envelope.success(response_data)


@router.post(
    "/{job_id}/cancel",
    response_model=APIResponse[JobActionResponse],
    status_code=status.HTTP_200_OK,
    summary="Cancel ERP Import Job",
    description="Transitions active import job to CANCELLED state.",
)
async def cancel_job(
    job_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthenticatedUser,
    envelope: TimedEnvelope,
) -> APIResponse[JobActionResponse]:
    job_repo = ImportJobRepository(session)
    storage = get_storage_provider()
    checksum_svc = ChecksumService(storage)
    job_service = ImportJobService(session, job_repo, storage, checksum_svc)

    job = await job_service.cancel_job(job_id)
    await session.commit()

    res = JobActionResponse(
        job_number=job.job_number,
        action="CANCEL",
        previous_status="PROCESSING",
        new_status=job.status,
        message=f"Job '{job.job_number}' successfully cancelled.",
    )
    return envelope.success(res)


@router.post(
    "/{job_id}/retry",
    response_model=APIResponse[JobActionResponse],
    status_code=status.HTTP_200_OK,
    summary="Retry Failed ERP Import Job",
    description="Re-queues a failed import job for execution.",
)
async def retry_job(
    job_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthenticatedUser,
    envelope: TimedEnvelope,
) -> APIResponse[JobActionResponse]:
    job_repo = ImportJobRepository(session)
    storage = get_storage_provider()
    checksum_svc = ChecksumService(storage)
    job_service = ImportJobService(session, job_repo, storage, checksum_svc)

    job = await job_service.retry_job(job_id)
    await session.commit()

    import asyncio

    async def _run_pipeline(j_num: str) -> None:
        try:
            from app.core.database import AsyncSessionFactory
            from app.modules.erp.workers.orchestrator import ImportPipelineOrchestrator

            async with AsyncSessionFactory() as pipe_session:
                orchestrator = ImportPipelineOrchestrator()
                await orchestrator.execute_pipeline(pipe_session, j_num)
                await pipe_session.commit()
        except Exception as exc:  # noqa: BLE001
            from app.core.logging import get_logger

            logger = get_logger("app.modules.erp.api.jobs")
            logger.error(f"Pipeline background retry failed for {j_num}: {exc}", exc_info=True)

    asyncio.create_task(_run_pipeline(job.job_number))

    res = JobActionResponse(
        job_number=job.job_number,
        action="RETRY",
        previous_status="FAILED",
        new_status=job.status,
        message=f"Job '{job.job_number}' re-queued for processing.",
    )
    return envelope.success(res)
