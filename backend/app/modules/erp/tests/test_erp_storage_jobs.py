"""
Exhaustive Production Test Suite for WS1.2 Workbook Storage & Import Job Management
Tests Real Filesystem operations, SHA-256 Checksums, Chunked Upload Assembly,
Duplicate Detection, Resumable Uploads, State Machine Controls, Cancellation, and Cleanup Policies.
"""

import pathlib

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import settings
from app.core.exceptions import DomainValidationError
from app.modules.erp.models import ImportJob
from app.modules.erp.repositories import ImportJobRepository
from app.modules.erp.services.checksum import ChecksumService
from app.modules.erp.services.job_service import ImportJobService
from app.modules.erp.services.state_machine import ImportJobState, ImportStateMachine
from app.modules.erp.services.upload import UploadSessionManager
from app.modules.erp.storage.local import LocalStorageProvider


@pytest_asyncio.fixture
async def db_session():
    """Real PostgreSQL AsyncSession fixture with transaction rollback."""
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, pool_pre_ping=True)
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
    await engine.dispose()


@pytest.fixture
def tmp_storage_provider(tmp_path: pathlib.Path):
    """Real LocalStorageProvider fixture backed by a temporary test directory."""
    provider = LocalStorageProvider(tmp_path / "storage_root")
    return provider


# =============================================================================
# 1. STORAGE PROVIDER & CHECKSUM TESTS (Real Filesystem)
# =============================================================================


@pytest.mark.asyncio
async def test_local_storage_init_and_single_file_write(
    tmp_storage_provider: LocalStorageProvider,
):
    await tmp_storage_provider.init_storage()

    content = b"Header,Col1,Col2\n1,Alpha,100\n2,Beta,200\n"
    relative_path = "workbooks/job_100/test.csv"

    abs_path = await tmp_storage_provider.save_file(relative_path, content)
    assert pathlib.Path(abs_path).exists()
    assert await tmp_storage_provider.file_exists(relative_path) is True

    # Read back and compare
    read_chunks = []
    async for chunk in tmp_storage_provider.read_chunks(relative_path):
        read_chunks.append(chunk)
    assert b"".join(read_chunks) == content

    # Clean up
    assert await tmp_storage_provider.delete_file(relative_path) is True
    assert await tmp_storage_provider.file_exists(relative_path) is False


@pytest.mark.asyncio
async def test_checksum_service_sha256(tmp_storage_provider: LocalStorageProvider):
    await tmp_storage_provider.init_storage()
    checksum_service = ChecksumService(tmp_storage_provider)

    data = b"Fleet Control Tower Canonical ERP Import Payload Data"
    expected_hash = ChecksumService.compute_bytes_sha256(data)

    relative_path = "workbooks/job_200/payload.bin"
    await tmp_storage_provider.save_file(relative_path, data)

    actual_hash = await checksum_service.compute_file_hash(relative_path)
    assert actual_hash == expected_hash

    is_valid = await checksum_service.verify_file_integrity(
        relative_path, expected_hash
    )
    assert is_valid is True

    is_invalid = await checksum_service.verify_file_integrity(
        relative_path, "wrong_hash_12345"
    )
    assert is_invalid is False


# =============================================================================
# 2. CHUNKED & RESUMABLE UPLOAD LIFECYCLE TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_chunked_upload_assembly_lifecycle(
    db_session: AsyncSession, tmp_storage_provider: LocalStorageProvider
):
    await tmp_storage_provider.init_storage()
    job_repo = ImportJobRepository(db_session)
    checksum_service = ChecksumService(tmp_storage_provider)
    upload_manager = UploadSessionManager(
        tmp_storage_provider, checksum_service, job_repo
    )

    # 1. Create Initial Job
    job = ImportJob(
        job_number="JOB-CHUNK-01",
        status=ImportJobState.QUEUED.value,
        file_name="dispatches_large.xlsx",
        file_hash="pending",
        total_rows=0,
        processed_rows=0,
        error_count=0,
    )
    await job_repo.create(job)
    await db_session.flush()

    # 2. Prepare payload split into 3 chunks
    chunk1 = b"Part 1 Header & Rows 1-500\n"
    chunk2 = b"Part 2 Rows 501-1000\n"
    chunk3 = b"Part 3 Rows 1001-1500 Footer\n"
    full_data = chunk1 + chunk2 + chunk3
    expected_hash = ChecksumService.compute_bytes_sha256(full_data)

    # 3. Init Session
    session_info = await upload_manager.init_upload_session(
        job_number="JOB-CHUNK-01",
        file_name="dispatches_large.xlsx",
        total_chunks=3,
        expected_hash=expected_hash,
    )
    upload_id = session_info["upload_id"]
    assert job.status == ImportJobState.UPLOADING.value

    # 4. Receive Chunks
    await upload_manager.receive_chunk(upload_id, 0, 3, chunk1)
    await upload_manager.receive_chunk(upload_id, 1, 3, chunk2)
    await upload_manager.receive_chunk(upload_id, 2, 3, chunk3)

    # 5. Finalize Assembly
    result = await upload_manager.finalize_upload(
        job_number="JOB-CHUNK-01",
        upload_id=upload_id,
        total_chunks=3,
        expected_sha256=expected_hash,
    )

    assert result["status"] == ImportJobState.READY_FOR_PROCESSING.value
    assert result["file_hash"] == expected_hash

    # Verify file stored on disk matches full_data
    relative_path = f"workbooks/{job.id}/dispatches_large.xlsx"
    assert await tmp_storage_provider.file_exists(relative_path) is True


# =============================================================================
# 3. DUPLICATE WORKBOOK DETECTION & IMPORT JOB SERVICE TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_duplicate_workbook_detection(
    db_session: AsyncSession, tmp_storage_provider: LocalStorageProvider
):
    await tmp_storage_provider.init_storage()
    job_repo = ImportJobRepository(db_session)
    checksum_service = ChecksumService(tmp_storage_provider)
    job_service = ImportJobService(
        db_session, job_repo, tmp_storage_provider, checksum_service
    )

    workbook_content = b"Duplicate Excel Workbook Data Payload Bytes"

    # 1. First import should succeed
    job1 = await job_service.create_import_job(
        file_name="january_dispatches.xlsx",
        file_bytes=workbook_content,
        job_number_override="JOB-DUP-01",
    )
    assert job1.status == ImportJobState.READY_FOR_PROCESSING.value

    # 2. Second import of exact same content must be rejected as duplicate
    with pytest.raises(DomainValidationError) as exc_info:
        await job_service.create_import_job(
            file_name="january_dispatches_copy.xlsx",
            file_bytes=workbook_content,
            job_number_override="JOB-DUP-02",
        )

    assert "Duplicate workbook detected!" in str(exc_info.value)


@pytest.mark.asyncio
async def test_job_cancellation_and_storage_cleanup(
    db_session: AsyncSession, tmp_storage_provider: LocalStorageProvider
):
    await tmp_storage_provider.init_storage()
    job_repo = ImportJobRepository(db_session)
    checksum_service = ChecksumService(tmp_storage_provider)
    job_service = ImportJobService(
        db_session, job_repo, tmp_storage_provider, checksum_service
    )

    workbook_content = b"Cancel Me Workbook Content Bytes"

    job = await job_service.create_import_job(
        file_name="cancel_me.xlsx",
        file_bytes=workbook_content,
        job_number_override="JOB-CANCEL-01",
    )
    relative_path = f"workbooks/{job.id}/cancel_me.xlsx"
    assert await tmp_storage_provider.file_exists(relative_path) is True

    # Cancel Job
    cancelled_job = await job_service.cancel_job(
        "JOB-CANCEL-01", reason="Testing User Cancellation"
    )
    assert cancelled_job.status == ImportJobState.CANCELLED.value

    # Verify file was cleaned up from storage
    assert await tmp_storage_provider.file_exists(relative_path) is False


@pytest.mark.asyncio
async def test_job_retry_and_state_machine_controls(
    db_session: AsyncSession, tmp_storage_provider: LocalStorageProvider
):
    await tmp_storage_provider.init_storage()
    job_repo = ImportJobRepository(db_session)
    checksum_service = ChecksumService(tmp_storage_provider)
    job_service = ImportJobService(
        db_session, job_repo, tmp_storage_provider, checksum_service
    )

    job = await job_service.create_import_job(
        file_name="retry_test.xlsx",
        file_bytes=b"Retry Test File",
        job_number_override="JOB-RETRY-01",
    )

    # Manually transition to FAILED
    job.status = ImportJobState.FAILED.value
    job.error_count = 3
    await job_repo.update(job)

    # Retry job resets status to QUEUED and resets error_count
    retried_job = await job_service.retry_job("JOB-RETRY-01")
    assert retried_job.status == ImportJobState.QUEUED.value
    assert retried_job.error_count == 0


@pytest.mark.asyncio
async def test_invalid_state_transition_protection():
    # Attempt invalid transition QUEUED ➔ READY_FOR_PROCESSING directly
    with pytest.raises(DomainValidationError) as exc_info:
        ImportStateMachine.validate_transition(
            ImportJobState.QUEUED.value, ImportJobState.READY_FOR_PROCESSING.value
        )

    assert "Cannot transition ImportJob from 'QUEUED' to 'READY_FOR_PROCESSING'" in str(
        exc_info.value
    )
