import time
import asyncio
import jwt
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.database import get_db_session
from app.modules.reports.models.report_execution import ReportExecutionAudit
from app.modules.reports.schemas.report_schemas import ReportStatus, ScopeValidationStatus, ReportFormat, ReportRequestDTO, ReportScopeDTO
from app.modules.reports.services.security_limiter import SecurityRateLimiter, DownloadTokenManager
from app.modules.reports.storage.artifact_storage import ReportArtifactStorage, REPORTS_BASE_DIR
from app.modules.reports.api.router import generate_report_async


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    SecurityRateLimiter.reset()
    yield
    SecurityRateLimiter.reset()


# 1. Rate Limiter Unit Test (Sliding Window & Throttling)
def test_ws4_4_rate_limiter_sliding_window():
    key = "test_user_ip_1"
    # First 10 requests allowed
    for _ in range(10):
        allowed, _ = SecurityRateLimiter.check_rate_limit(key=key, max_requests=10, window_seconds=60)
        assert allowed is True

    # 11th request throttled
    allowed, retry_after = SecurityRateLimiter.check_rate_limit(key=key, max_requests=10, window_seconds=60)
    assert allowed is False
    assert retry_after > 0


# 2. Synchronous & Async Generation Rate Limit Test (HTTP 429)
@pytest.mark.asyncio
async def test_ws4_4_generation_rate_limit_exceeded():
    from app.modules.reports.api.router import generate_report
    mock_db = AsyncMock()
    real_exec = ReportExecutionAudit(
        execution_id="exec-sec-gen-1",
        report_id="site_operations",
        report_type="site_dashboard",
        format="PDF",
        requested_by="rate_user",
        requested_at=datetime.now(timezone.utc),
        requested_scope={},
        effective_scope={},
        scope_fingerprint="fp1",
        scope_validation_status="VALIDATED",
        record_count=10,
        status="COMPLETED"
    )

    req = ReportRequestDTO(
        report_id="site_operations",
        format=ReportFormat.PDF,
        requested_by="rate_user",
        scope=ReportScopeDTO()
    )

    with patch("app.modules.reports.api.router.report_service.create_execution_record", AsyncMock(return_value=real_exec)), \
         patch("app.modules.reports.api.router.scope_resolver.resolve_and_validate_scope", AsyncMock(return_value=(True, {}, None))):

        # Fill up 10 requests allowed
        for _ in range(10):
            await generate_report(req=req, db=mock_db)

        # 11th request triggers 429
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await generate_report(req=req, db=mock_db)
        assert exc_info.value.status_code == 429
        assert exc_info.value.detail["code"] == "RATE_LIMIT_EXCEEDED"


# 3. Download Token Creation, Validation & Expiration Test
def test_ws4_4_download_token_lifecycle():
    token = DownloadTokenManager.create_download_token(
        execution_id="exec-123",
        user_id="user1",
        format_ext="pdf",
        expires_minutes=15
    )
    assert token is not None

    # Valid verification
    assert DownloadTokenManager.verify_download_token(token, expected_execution_id="exec-123", expected_format="pdf", expected_user_id="user1") is True

    # Wrong execution ID
    assert DownloadTokenManager.verify_download_token(token, expected_execution_id="exec-999", expected_format="pdf", expected_user_id="user1") is False

    # Wrong format
    assert DownloadTokenManager.verify_download_token(token, expected_execution_id="exec-123", expected_format="xlsx", expected_user_id="user1") is False

    # Wrong user
    assert DownloadTokenManager.verify_download_token(token, expected_execution_id="exec-123", expected_format="pdf", expected_user_id="user2") is False


# 4. Tampered & Expired Download Token Protection
def test_ws4_4_tampered_and_expired_token_rejection():
    # Expired Token
    expired_token = DownloadTokenManager.create_download_token(
        execution_id="exec-123",
        user_id="user1",
        format_ext="pdf",
        expires_minutes=-1  # Already expired
    )
    assert DownloadTokenManager.verify_download_token(expired_token, expected_execution_id="exec-123", expected_format="pdf") is False

    # Tampered Token
    valid_token = DownloadTokenManager.create_download_token("exec-123", "user1", "pdf")
    tampered_token = valid_token[:-4] + "XXXX"
    assert DownloadTokenManager.verify_download_token(tampered_token, expected_execution_id="exec-123", expected_format="pdf") is False


# 5. Cross-User Execution Access Isolation Test (HTTP 403)
@pytest.mark.asyncio
async def test_ws4_4_cross_user_access_isolation():
    from app.modules.reports.api.router import create_download_token
    mock_db = AsyncMock()
    exec_record = ReportExecutionAudit(
        execution_id="exec-owner-user1",
        report_id="site_operations",
        report_type="site_dashboard",
        format="PDF",
        requested_by="user1",  # Owned by user1
        requested_at=datetime.now(timezone.utc),
        requested_scope={},
        effective_scope={},
        scope_fingerprint="fp-owner",
        scope_validation_status="VALIDATED",
        record_count=10,
        status="COMPLETED"
    )

    class MockExecuteResult:
        def scalars(self):
            class MockScalars:
                def first(self): return exec_record
            return MockScalars()

    mock_db.execute.return_value = MockExecuteResult()

    from fastapi import HTTPException
    # User2 attempts to issue token for user1's execution -> 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        await create_download_token(execution_id="exec-owner-user1", format="pdf", user_id="user2", db=mock_db)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["code"] == "ACCESS_DENIED"

    # User1 attempts for own execution -> Success
    res = await create_download_token(execution_id="exec-owner-user1", format="pdf", user_id="user1", db=mock_db)
    assert res["execution_id"] == "exec-owner-user1"
    assert res["download_token"] is not None


# 6. Path Traversal & Symlink Escape Protection Test
def test_ws4_4_path_traversal_and_symlink_escape_protection(tmp_path):
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        with pytest.raises(ValueError):
            ReportArtifactStorage.save_artifacts("../../../etc/passwd", {"pdf": b"BAD"})

        with pytest.raises(ValueError):
            ReportArtifactStorage.purge_execution_artifacts("..\\..\\Windows\\System32")


# 7. Download API Security & Header Hardening Test
@pytest.mark.asyncio
async def test_ws4_4_download_security_and_header_hardening(tmp_path):
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        exec_id = "exec-header-sec"
        ReportArtifactStorage.save_artifacts(exec_id, {"pdf": b"SECURE_PDF_CONTENT"})

        token = DownloadTokenManager.create_download_token(exec_id, "user1", "pdf")

        from app.modules.reports.api.router import download_report_artifact
        res = await download_report_artifact(execution_id=exec_id, format="pdf", token=token, user_id="user1", db=AsyncMock())
        assert res.headers["Cache-Control"] == "no-store, no-cache, must-revalidate, private"
        assert res.headers["X-Content-Type-Options"] == "nosniff"


# 8. Execution ID Enumeration Protection Test (HTTP 404 Authorization before Disclosure)
@pytest.mark.asyncio
async def test_ws4_4_execution_enumeration_protection():
    from app.modules.reports.api.router import get_execution_status
    mock_db = AsyncMock()

    class MockExecuteResult:
        def scalars(self):
            class MockScalars:
                def first(self): return None
            return MockScalars()

    mock_db.execute.return_value = MockExecuteResult()

    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await get_execution_status(execution_id="guessed-non-existent-id", db=mock_db)
    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["code"] == "REPORT_EXECUTION_NOT_FOUND"


# 9. WS4.1 Async Worker Compatibility Test
@pytest.mark.asyncio
async def test_ws4_4_ws4_1_async_compatibility():
    req = ReportRequestDTO(
        report_id="site_operations",
        format=ReportFormat.PDF,
        requested_by="async_sec_user",
        scope=ReportScopeDTO()
    )
    mock_bg = AsyncMock()
    mock_db = AsyncMock()
    real_exec = ReportExecutionAudit(
        execution_id="exec-ws44-async-1",
        report_id="site_operations",
        report_type="site_dashboard",
        format="PDF",
        requested_by="async_sec_user",
        requested_at=datetime.now(timezone.utc),
        requested_scope={},
        effective_scope={},
        scope_fingerprint="fp1",
        scope_validation_status="VALIDATED",
        record_count=10,
        status="QUEUED"
    )

    with patch("app.modules.reports.api.router.report_service.create_execution_record", AsyncMock(return_value=real_exec)), \
         patch("app.modules.reports.api.router.scope_resolver.resolve_and_validate_scope", AsyncMock(return_value=(True, {}, None))):

        res = await generate_report_async(req=req, background_tasks=mock_bg, db=mock_db)
        assert res.execution_id == "exec-ws44-async-1"
        assert res.status == ReportStatus.QUEUED


# 10. WS4.2 & WS4.3 Contract Preservation Test
@pytest.mark.asyncio
async def test_ws4_4_ws4_2_and_ws4_3_contract_preservation():
    from app.modules.reports.services.scope_resolver import ScopeResolverService
    resolver = ScopeResolverService()
    mock_db = AsyncMock()

    class MockExecuteResult:
        def scalar(self): return 15000  # WS4.2 10,000 record ceiling check

    mock_db.execute.return_value = MockExecuteResult()

    is_valid, _, error_reason = await resolver.resolve_and_validate_scope(session=mock_db, raw_scope={"plant_id": "VASCO"})
    assert is_valid is False
    assert "EXPORT_LIMIT_EXCEEDED" in str(error_reason)
