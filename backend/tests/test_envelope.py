"""
Unit tests for API Response Envelope DTOs
"""

from app.schemas.envelope import APIResponse


def test_api_response_success_factory():
    res = APIResponse.ok(
        data={"key": "value"},
        correlation_id="corr-123",
        request_id="req-456",
        duration_ms=12.5,
    )
    assert res.success is True
    assert res.data == {"key": "value"}
    assert res.error is None
    assert res.meta.correlation_id == "corr-123"
    assert res.meta.request_id == "req-456"
    assert res.meta.request_duration_ms == 12.5
    assert res.meta.api_version == "v1"


def test_api_response_failure_factory():
    res = APIResponse.fail(
        error_code="VALIDATION_ERROR",
        message="Invalid payload",
        correlation_id="corr-123",
        request_id="req-456",
        duration_ms=5.0,
        details={"field": "name missing"},
    )
    assert res.success is False
    assert res.data is None
    assert res.error is not None
    assert res.error.code == "VALIDATION_ERROR"
    assert res.error.message == "Invalid payload"
    assert res.error.details == {"field": "name missing"}
