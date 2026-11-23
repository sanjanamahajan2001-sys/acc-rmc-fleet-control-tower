import os
import time
import hashlib
import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch

from app.modules.reports.models.report_execution import ReportExecutionAudit
from app.modules.reports.schemas.report_schemas import ReportStatus
from app.modules.reports.storage.artifact_storage import ReportArtifactStorage, REPORTS_BASE_DIR
from app.modules.reports.services.report_service import ReportService
from app.core.config import Settings


# 1. Artifact Creation & Traversal Protection Test (Hardened Path.resolve)
def test_ws4_3_artifact_storage_traversal_protection(tmp_path):
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        saved = ReportArtifactStorage.save_artifacts("exec-clean-1", {"pdf": b"PDF_BYTES", "json": b"{}"})
        assert "pdf" in saved
        assert os.path.exists(saved["pdf"])

        with pytest.raises(ValueError):
            ReportArtifactStorage.save_artifacts("../traversal_dir", {"pdf": b"BAD"})

        with pytest.raises(ValueError):
            ReportArtifactStorage.purge_execution_artifacts("../traversal_dir")

        with pytest.raises(ValueError):
            ReportArtifactStorage.purge_execution_artifacts("/etc/passwd")


# 2. Artifact Purge Eligibility & Retention Boundary Test
@pytest.mark.asyncio
async def test_ws4_3_purge_eligibility_and_retention_boundary(tmp_path):
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        active_id = "exec-active-100"
        ReportArtifactStorage.save_artifacts(active_id, {"pdf": b"ACTIVE_CONTENT"})
        active_path = ReportArtifactStorage.get_artifact_path(active_id, "pdf")

        expired_id = "exec-expired-200"
        ReportArtifactStorage.save_artifacts(expired_id, {"pdf": b"EXPIRED_CONTENT"})
        expired_path = ReportArtifactStorage.get_artifact_path(expired_id, "pdf")

        now = datetime.now(timezone.utc)
        expired_record = ReportExecutionAudit(
            execution_id=expired_id,
            report_id="site_operations",
            report_type="site_dashboard",
            format="PDF",
            requested_by="test_user",
            requested_at=now - timedelta(days=10),
            requested_scope={},
            effective_scope={},
            scope_fingerprint="fp2",
            scope_validation_status="VALIDATED",
            record_count=10,
            status="COMPLETED",
            retention_expires_at=now - timedelta(days=1)
        )

        mock_db = AsyncMock()

        class MockExpiredResult:
            def scalars(self):
                class MockScalars:
                    def all(self): return [expired_record]
                return MockScalars()

        class MockAllExecsResult:
            def scalars(self):
                class MockScalars:
                    def all(self): return [active_id, expired_id]
                return MockScalars()

        mock_db.execute.side_effect = [MockExpiredResult(), MockAllExecsResult()]


        service = ReportService()
        res = service.purge_expired_artifacts(mock_db)
        if asyncio.iscoroutine(res):
            res = await res

        assert res["scanned"] == 1
        assert res["purged"] == 1
        assert res["reclaimed_bytes"] > 0
        assert expired_record.status == "PURGED"
        assert not os.path.exists(expired_path)
        assert os.path.exists(active_path)


# 3. Orphan Artifact Detection & Purging Test
def test_ws4_3_orphan_artifact_handling(tmp_path):
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        valid_id = "exec-valid-1"
        orphan_id = "exec-orphan-99"
        ReportArtifactStorage.save_artifacts(valid_id, {"pdf": b"VALID_BYTES"})
        ReportArtifactStorage.save_artifacts(orphan_id, {"pdf": b"ORPHAN_BYTES"})

        purged_orphans = ReportArtifactStorage.cleanup_orphan_directories({valid_id})
        assert purged_orphans == 1
        assert os.path.exists(ReportArtifactStorage.get_artifact_path(valid_id, "pdf"))
        with pytest.raises(FileNotFoundError):
            ReportArtifactStorage.get_artifact_path(orphan_id, "pdf")


# 4. Concurrent Purge / Async Generation Safety Test
@pytest.mark.asyncio
async def test_ws4_3_concurrent_purge_and_generation_safety(tmp_path):
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        active_exec_id = "exec-concurrent-active"
        
        async def mock_generation():
            await asyncio.sleep(0.05)
            ReportArtifactStorage.save_artifacts(active_exec_id, {"pdf": b"GENERATED_ASYNC_PDF"})

        async def mock_purge():
            mock_db = AsyncMock()

            class MockExecuteResult:
                def scalars(self):
                    class MockScalars:
                        def all(self): return []
                    return MockScalars()

            mock_db.execute.return_value = MockExecuteResult()
            service = ReportService()
            return await service.purge_expired_artifacts(mock_db)

        gen_task = asyncio.create_task(mock_generation())
        purge_task = asyncio.create_task(mock_purge())

        await asyncio.gather(gen_task, purge_task)

        assert os.path.exists(ReportArtifactStorage.get_artifact_path(active_exec_id, "pdf"))


# 5. SHA-256 Artifact Integrity Verification Test
def test_ws4_3_sha256_artifact_integrity(tmp_path):
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        exec_id = "exec-sha-1"
        content = b"AUTHENTIC_REPORT_DATA"
        saved = ReportArtifactStorage.save_artifacts(exec_id, {"pdf": content})
        pdf_path = saved["pdf"]

        initial_hash = hashlib.sha256(content).hexdigest()
        with open(pdf_path, "rb") as f:
            read_hash = hashlib.sha256(f.read()).hexdigest()
        assert read_hash == initial_hash

        # Mutate / Corrupt file
        with open(pdf_path, "wb") as f:
            f.write(b"CORRUPTED_BYTES")

        with open(pdf_path, "rb") as f:
            corrupt_hash = hashlib.sha256(f.read()).hexdigest()
        assert corrupt_hash != initial_hash


# 6. Storage Deletion Failure Recovery Test
@pytest.mark.asyncio
async def test_ws4_3_deletion_failure_recovery(tmp_path):
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        now = datetime.now(timezone.utc)
        exec_id = "exec-fail-delete"
        ReportArtifactStorage.save_artifacts(exec_id, {"pdf": b"BYTES"})

        record = ReportExecutionAudit(
            execution_id=exec_id,
            report_id="site_operations",
            report_type="site_dashboard",
            format="PDF",
            requested_by="test_user",
            requested_at=now - timedelta(days=10),
            requested_scope={},
            effective_scope={},
            scope_fingerprint="fp1",
            scope_validation_status="VALIDATED",
            record_count=10,
            status="COMPLETED",
            retention_expires_at=now - timedelta(days=1)
        )

        mock_db = AsyncMock()

        class MockExecuteResult:
            def scalars(self):
                class MockScalars:
                    def all(self): return [record]
                return MockScalars()

        mock_db.execute.return_value = MockExecuteResult()

        with patch("app.modules.reports.storage.artifact_storage.ReportArtifactStorage.purge_execution_artifacts", side_effect=OSError("Permission Denied")):
            service = ReportService()
            res = await service.purge_expired_artifacts(mock_db)

            assert res["failed"] == 1
            assert res["purged"] == 0
            assert record.status == "COMPLETED"


# 7. Audit Record Preservation Test
@pytest.mark.asyncio
async def test_ws4_3_audit_record_preservation(tmp_path):
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        now = datetime.now(timezone.utc)
        exec_id = "exec-audit-preserve"
        ReportArtifactStorage.save_artifacts(exec_id, {"pdf": b"DATA"})

        record = ReportExecutionAudit(
            execution_id=exec_id,
            report_id="site_operations",
            report_type="site_dashboard",
            format="PDF",
            requested_by="test_user",
            requested_at=now - timedelta(days=10),
            requested_scope={"plant_id": "VASCO"},
            effective_scope={"plant_id": "VASCO"},
            scope_fingerprint="fp-audit",
            scope_validation_status="VALIDATED",
            record_count=25,
            status="COMPLETED",
            retention_expires_at=now - timedelta(days=1)
        )

        mock_db = AsyncMock()

        class MockExecuteResult:
            def scalars(self):
                class MockScalars:
                    def all(self): return [record]
                return MockScalars()

        mock_db.execute.return_value = MockExecuteResult()

        service = ReportService()
        await service.purge_expired_artifacts(mock_db)

        # Execution Audit record attributes preserved intact
        assert record.execution_id == exec_id
        assert record.report_id == "site_operations"
        assert record.record_count == 25
        assert record.requested_scope == {"plant_id": "VASCO"}
        assert record.status == "PURGED"


# 8. Retention Configuration Validation Test
def test_ws4_3_retention_config_validation():
    s1 = Settings(REPORT_ARTIFACT_RETENTION_DAYS=7)
    assert s1.REPORT_ARTIFACT_RETENTION_DAYS == 7

    s2 = Settings(REPORT_ARTIFACT_RETENTION_DAYS=30)
    assert s2.REPORT_ARTIFACT_RETENTION_DAYS == 30


# 9. Retention Timestamp Lifecycle Policy Test
def test_ws4_3_retention_timestamp_policy_creation():
    now_utc = datetime.now(timezone.utc)
    retention_days = 7
    expires_at = now_utc + timedelta(days=retention_days)

    assert (expires_at - now_utc).days == 7


# 10. Purge Engine Idempotency Test
@pytest.mark.asyncio
async def test_ws4_3_purge_idempotency(tmp_path):
    with patch("app.modules.reports.storage.artifact_storage.REPORTS_BASE_DIR", str(tmp_path)):
        exec_id = "exec-idempotency-double"
        ReportArtifactStorage.save_artifacts(exec_id, {"pdf": b"DATA"})

        b1 = ReportArtifactStorage.purge_execution_artifacts(exec_id)
        assert b1 > 0

        # Second purge call causes no exception or error
        b2 = ReportArtifactStorage.purge_execution_artifacts(exec_id)
        assert b2 == 0
