"""
Unit tests for Security Audit Logging Hooks
"""

from app.core.context import RequestContext
from app.core.security.audit import log_security_event


def test_log_security_event():
    RequestContext.init(request_id="req-audit-1", correlation_id="corr-audit-1")
    log_security_event(
        event_type="TOKEN_ISSUED",
        user_id="U123",
        details={"token_type": "access"},
        success=True,
    )
    log_security_event(
        event_type="AUTH_FAILURE",
        user_id="U123",
        details={"reason": "invalid password"},
        success=False,
    )
