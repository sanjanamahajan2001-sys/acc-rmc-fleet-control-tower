from typing import Tuple
from prometheus_client import Counter, Histogram, Gauge, REGISTRY, generate_latest, CONTENT_TYPE_LATEST


# Bounded Cardinality Label Names: report_id, format, status, error_category
REPORT_REQUESTS_TOTAL = Counter(
    "report_requests_total",
    "Total number of report generation requests submitted",
    ["report_id", "format", "execution_type"]
)

REPORT_GENERATION_COMPLETED_TOTAL = Counter(
    "report_generation_completed_total",
    "Total number of successfully completed report generations",
    ["report_id", "format"]
)

REPORT_GENERATION_NO_DATA_TOTAL = Counter(
    "report_generation_no_data_total",
    "Total number of report generations resulting in NO_DATA state",
    ["report_id", "format"]
)

REPORT_GENERATION_FAILURES_TOTAL = Counter(
    "report_generation_failures_total",
    "Total number of report generation failures",
    ["report_id", "format", "error_category"]
)

REPORT_RATE_LIMIT_EXCEEDED_TOTAL = Counter(
    "report_rate_limit_exceeded_total",
    "Total number of requests throttled by security rate limiter",
    ["endpoint"]
)

REPORT_SECURITY_DENIALS_TOTAL = Counter(
    "report_security_denials_total",
    "Total number of security authorization or token validation denials",
    ["reason"]
)

REPORT_DOWNLOAD_TOTAL = Counter(
    "report_download_total",
    "Total number of artifact download requests",
    ["format", "status"]
)

REPORT_GENERATION_DURATION_SECONDS = Histogram(
    "report_generation_duration_seconds",
    "Total execution duration of report generation in seconds",
    ["report_id", "format"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

REPORT_CANONICAL_ASSEMBLY_DURATION_SECONDS = Histogram(
    "report_canonical_assembly_duration_seconds",
    "Duration of canonical report data assembly in seconds",
    ["report_id"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)

REPORT_RENDER_DURATION_SECONDS = Histogram(
    "report_render_duration_seconds",
    "Duration of multi-format report rendering in seconds",
    ["format"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

REPORT_ACTIVE_EXECUTIONS = Gauge(
    "report_active_executions",
    "Number of report executions currently in PROCESSING state"
)

REPORT_QUEUED_EXECUTIONS = Gauge(
    "report_queued_executions",
    "Number of report executions currently in QUEUED state"
)

ARTIFACT_STORAGE_BYTES = Gauge(
    "artifact_storage_bytes",
    "Total disk storage bytes consumed by report artifacts"
)

ARTIFACT_PURGE_TOTAL = Counter(
    "artifact_purge_total",
    "Total number of expired or orphan artifacts purged",
    ["purge_type"]
)

ARTIFACT_PURGE_FAILURES_TOTAL = Counter(
    "artifact_purge_failures_total",
    "Total number of artifact deletion failures during purge"
)


class ReportingMetricsCollector:
    """
    Centralized Prometheus metrics collector for the reporting subsystem.
    Enforces strictly bounded label cardinality and zero sensitive data leakage.
    """

    @classmethod
    def record_submission(cls, report_id: str, format_str: str, execution_type: str = "sync"):
        REPORT_REQUESTS_TOTAL.labels(
            report_id=report_id or "unknown",
            format=format_str.upper() if format_str else "UNKNOWN",
            execution_type=execution_type
        ).inc()

    @classmethod
    def record_completion(cls, report_id: str, format_str: str, duration_sec: float, record_count: int):
        fmt = format_str.upper() if format_str else "UNKNOWN"
        rid = report_id or "unknown"
        if record_count == 0:
            REPORT_GENERATION_NO_DATA_TOTAL.labels(report_id=rid, format=fmt).inc()
        else:
            REPORT_GENERATION_COMPLETED_TOTAL.labels(report_id=rid, format=fmt).inc()
        REPORT_GENERATION_DURATION_SECONDS.labels(report_id=rid, format=fmt).observe(duration_sec)

    @classmethod
    def record_failure(cls, report_id: str, format_str: str, error_category: str):
        REPORT_GENERATION_FAILURES_TOTAL.labels(
            report_id=report_id or "unknown",
            format=format_str.upper() if format_str else "UNKNOWN",
            error_category=error_category
        ).inc()

    @classmethod
    def record_rate_limit(cls, endpoint: str):
        REPORT_RATE_LIMIT_EXCEEDED_TOTAL.labels(endpoint=endpoint).inc()

    @classmethod
    def record_security_denial(cls, reason: str):
        REPORT_SECURITY_DENIALS_TOTAL.labels(reason=reason).inc()

    @classmethod
    def record_download(cls, format_str: str, status_str: str):
        REPORT_DOWNLOAD_TOTAL.labels(
            format=format_str.upper() if format_str else "UNKNOWN",
            status=status_str
        ).inc()

    @classmethod
    def get_metrics_payload(cls) -> Tuple[bytes, str]:
        return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
