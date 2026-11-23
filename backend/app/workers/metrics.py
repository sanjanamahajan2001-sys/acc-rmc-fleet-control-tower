"""
Worker Operational Metrics Contract DTO

Provides standardized operational metrics container tracking queue depth,
active workers, completed/failed job counts, retry/DLQ counts, and execution latency.
"""

from pydantic import BaseModel, Field


class WorkerMetrics(BaseModel):
    """
    Standardized operational metrics DTO for background workers.
    """

    queue_depth: int = Field(
        default=0, ge=0, description="Total tasks currently queued"
    )
    active_workers: int = Field(
        default=0, ge=0, description="Total active worker processes"
    )
    completed_jobs: int = Field(
        default=0, ge=0, description="Total successfully completed jobs"
    )
    failed_jobs: int = Field(default=0, ge=0, description="Total failed job executions")
    retry_count: int = Field(
        default=0, ge=0, description="Total retried job executions"
    )
    dlq_count: int = Field(
        default=0, ge=0, description="Total jobs routed to Dead Letter Queue"
    )
    avg_execution_time_ms: float = Field(
        default=0.0, ge=0.0, description="Average job execution duration in ms"
    )
