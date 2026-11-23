"""
Standardized API Response Envelope DTOs

Defines APIResponse[T], APIErrorDetail, and ResponseMeta according to
Master Architecture Blueprint Section 9.
"""

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ResponseMeta(BaseModel):
    """
    Metadata container attached to every API response envelope.
    """

    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of response creation",
    )
    correlation_id: str = Field(
        description="Unique correlation ID for distributed tracing"
    )
    request_id: str = Field(description="Unique request ID for log tracking")
    api_version: str = Field(default="v1", description="API version identifier")
    request_duration_ms: float = Field(
        ge=0.0, description="Total server processing duration in milliseconds"
    )


class APIErrorDetail(BaseModel):
    """
    Structured error container for failed API requests.
    """

    code: str = Field(
        description="Platform standard error code string (e.g., NOT_FOUND)"
    )
    message: str = Field(description="Human-readable error summary")
    details: dict[str, Any] | list[Any] | None = Field(
        default=None, description="Optional field-level or contextual error details"
    )


class APIResponse(BaseModel, Generic[T]):
    """
    Standardized API response envelope for all REST endpoints.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    success: bool = Field(description="Boolean status indicator")
    data: T | None = Field(
        default=None, description="Response payload data when success=True"
    )
    error: APIErrorDetail | None = Field(
        default=None, description="Error detail object when success=False"
    )
    meta: ResponseMeta = Field(description="Standardized response metadata")

    @classmethod
    def ok(
        cls,
        data: T,
        correlation_id: str,
        request_id: str,
        duration_ms: float,
        api_version: str = "v1",
    ) -> "APIResponse[T]":
        """Factory helper constructing a successful API response envelope."""
        meta = ResponseMeta(
            correlation_id=correlation_id,
            request_id=request_id,
            api_version=api_version,
            request_duration_ms=duration_ms,
        )
        return cls(success=True, data=data, error=None, meta=meta)

    @classmethod
    def fail(
        cls,
        error_code: str,
        message: str,
        correlation_id: str,
        request_id: str,
        duration_ms: float,
        details: dict[str, Any] | list[Any] | None = None,
        api_version: str = "v1",
    ) -> "APIResponse[Any]":
        """Factory helper constructing a failed API response envelope."""
        meta = ResponseMeta(
            correlation_id=correlation_id,
            request_id=request_id,
            api_version=api_version,
            request_duration_ms=duration_ms,
        )
        error_detail = APIErrorDetail(code=error_code, message=message, details=details)
        return cls(success=False, data=None, error=error_detail, meta=meta)
