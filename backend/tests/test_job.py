"""
Unit tests for Job Status & Execution Context DTOs
"""

from app.workers.job import JobExecutionContext, JobMetadata, JobStatus


def test_job_status_enum_values():
    assert JobStatus.QUEUED.value == "QUEUED"
    assert JobStatus.RUNNING.value == "RUNNING"
    assert JobStatus.COMPLETED.value == "COMPLETED"
    assert JobStatus.FAILED.value == "FAILED"
    assert JobStatus.RETRYING.value == "RETRYING"
    assert JobStatus.DLQ.value == "DLQ"


def test_job_execution_context_creation():
    meta = JobMetadata(
        task_name="system.cleanup",
        correlation_id="corr-job-1",
        request_id="req-job-1",
    )
    ctx = JobExecutionContext(metadata=meta, payload={"key": "val"})

    assert ctx.metadata.status == JobStatus.QUEUED
    assert ctx.metadata.attempts == 0
    assert ctx.payload == {"key": "val"}
