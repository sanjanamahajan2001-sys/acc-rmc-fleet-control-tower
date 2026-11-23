import time
import enum
import asyncio
from typing import Callable, Any, Dict, Tuple
from app.modules.reports.services.telemetry import (
    ReportingMetricsCollector
)
from prometheus_client import Counter, Gauge

REPORT_RESILIENCE_RETRIES_TOTAL = Counter(
    "report_resilience_retries_total",
    "Total number of retry attempts executed for transient errors",
    ["operation"]
)

REPORT_RESILIENCE_FAILURES_TOTAL = Counter(
    "report_resilience_failures_total",
    "Total number of unrecoverable resiliency failures",
    ["operation", "failure_category"]
)

REPORT_CIRCUIT_BREAKER_OPEN_TOTAL = Counter(
    "report_circuit_breaker_open_total",
    "Total number of times circuit breaker transitioned to OPEN state",
    ["dependency"]
)

REPORT_CIRCUIT_BREAKER_REJECTIONS_TOTAL = Counter(
    "report_circuit_breaker_rejections_total",
    "Total number of requests rejected while circuit breaker is in OPEN state",
    ["dependency"]
)

REPORT_CIRCUIT_BREAKER_STATE = Gauge(
    "report_circuit_breaker_state",
    "Current state of circuit breaker (0=CLOSED, 1=HALF_OPEN, 2=OPEN)",
    ["dependency"]
)


class CircuitState(enum.Enum):
    CLOSED = 0
    HALF_OPEN = 1
    OPEN = 2


class ReportCircuitBreaker:
    """
    Lightweight, production-safe Circuit Breaker for upstream database and dependency resilience.
    Transitions: CLOSED ➔ (failure threshold) ➔ OPEN ➔ (cooldown) ➔ HALF_OPEN ➔ (success/probe) ➔ CLOSED.
    """

    def __init__(self, dependency_name: str, failure_threshold: int = 3, cooldown_seconds: float = 10.0):
        self.dependency_name = dependency_name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_state_change = time.time()
        REPORT_CIRCUIT_BREAKER_STATE.labels(dependency=self.dependency_name).set(CircuitState.CLOSED.value)

    def allow_execution(self) -> bool:
        now = time.time()
        if self.state == CircuitState.OPEN:
            if now - self.last_state_change >= self.cooldown_seconds:
                self._transition_to(CircuitState.HALF_OPEN)
                return True
            else:
                REPORT_CIRCUIT_BREAKER_REJECTIONS_TOTAL.labels(dependency=self.dependency_name).inc()
                return False
        return True

    def record_success(self):
        self.failure_count = 0
        if self.state != CircuitState.CLOSED:
            self._transition_to(CircuitState.CLOSED)

    def record_failure(self):
        self.failure_count += 1
        if self.state == CircuitState.HALF_OPEN or self.failure_count >= self.failure_threshold:
            self._transition_to(CircuitState.OPEN)

    def _transition_to(self, new_state: CircuitState):
        self.state = new_state
        self.last_state_change = time.time()
        REPORT_CIRCUIT_BREAKER_STATE.labels(dependency=self.dependency_name).set(new_state.value)
        if new_state == CircuitState.OPEN:
            REPORT_CIRCUIT_BREAKER_OPEN_TOTAL.labels(dependency=self.dependency_name).inc()

    def reset(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_state_change = time.time()
        REPORT_CIRCUIT_BREAKER_STATE.labels(dependency=self.dependency_name).set(CircuitState.CLOSED.value)


# Global Circuit Breaker for Database Operations
db_circuit_breaker = ReportCircuitBreaker(dependency_name="postgresql", failure_threshold=3, cooldown_seconds=5.0)


async def execute_with_resilience(
    coro_func: Callable[[], Any],
    operation_name: str = "db_query",
    max_retries: int = 2,
    initial_delay_sec: float = 0.05
) -> Any:
    """
    Executes an async operation with circuit breaking, bounded retries, and exponential backoff.
    Safe against non-retryable validation or auth errors.
    """
    if not db_circuit_breaker.allow_execution():
        REPORT_RESILIENCE_FAILURES_TOTAL.labels(operation=operation_name, failure_category="CIRCUIT_OPEN").inc()
        raise RuntimeError(f"Circuit breaker for {db_circuit_breaker.dependency_name} is OPEN. Operation aborted.")

    attempt = 0
    delay = initial_delay_sec

    while True:
        try:
            res = await coro_func()
            db_circuit_breaker.record_success()
            return res
        except (ValueError, TypeError, KeyError) as non_retryable_exc:
            # Do NOT retry validation / semantic logic errors
            raise non_retryable_exc
        except Exception as exc:
            attempt += 1
            db_circuit_breaker.record_failure()

            if attempt > max_retries:
                REPORT_RESILIENCE_FAILURES_TOTAL.labels(operation=operation_name, failure_category="RETRY_EXHAUSTED").inc()
                raise exc

            REPORT_RESILIENCE_RETRIES_TOTAL.labels(operation=operation_name).inc()
            await asyncio.sleep(delay)
            delay *= 2.0
