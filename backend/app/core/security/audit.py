"""
Security Audit Logging Hooks

Binds security events (token issuance, refresh, revocation, auth failure)
into structlog preserving request ID and correlation ID.
"""

from typing import Any

from app.core.context import RequestContext
from app.core.logging import get_logger

logger = get_logger("app.security.audit")


def log_security_event(
    event_type: str,
    user_id: str | None = None,
    details: dict[str, Any] | None = None,
    success: bool = True,
) -> None:
    """
    Emits a structured security audit log entry.
    """
    log = logger.bind(
        event_type=event_type,
        user_id=user_id or RequestContext.get_user_id(),
        correlation_id=RequestContext.get_correlation_id(),
        request_id=RequestContext.get_request_id(),
        client_ip=RequestContext.get_client_ip(),
        success=success,
    )

    if success:
        log.info(f"Security Event: {event_type}", details=details or {})
    else:
        log.warning(f"Security Failure: {event_type}", details=details or {})
