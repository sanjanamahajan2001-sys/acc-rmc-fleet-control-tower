"""
ERP API Dependencies
Provides reusable FastAPI route dependencies for ERP REST API endpoints.
"""

import time
from typing import Annotated, Any

from fastapi import Depends

from app.core.context import RequestContext
from app.dependencies.auth import require_authenticated_user
from app.schemas.auth import TokenPayload
from app.schemas.envelope import APIResponse


class EnvelopeHelper:
    """
    Utility class for constructing APIResponse envelopes with execution duration timing.
    """

    def __init__(self, start_time: float):
        self.start_time = start_time

    def success(self, data: Any) -> APIResponse[Any]:
        duration = (time.time() - self.start_time) * 1000.0
        return APIResponse.ok(
            data=data,
            correlation_id=RequestContext.get_correlation_id(),
            request_id=RequestContext.get_request_id(),
            duration_ms=round(duration, 2),
        )

    def error(self, code: str, message: str, details: Any = None) -> APIResponse[Any]:
        duration = (time.time() - self.start_time) * 1000.0
        return APIResponse.fail(
            error_code=code,
            message=message,
            correlation_id=RequestContext.get_correlation_id(),
            request_id=RequestContext.get_request_id(),
            duration_ms=round(duration, 2),
            details=details,
        )


def get_envelope_helper() -> EnvelopeHelper:
    """
    FastAPI dependency injecting timed EnvelopeHelper.
    """
    return EnvelopeHelper(start_time=time.time())


AuthenticatedUser = Annotated[TokenPayload, Depends(require_authenticated_user)]
TimedEnvelope = Annotated[EnvelopeHelper, Depends(get_envelope_helper)]
