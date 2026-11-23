"""
Authentication Middleware

Extracts and validates HTTP Bearer tokens from the Authorization header.
Populates authenticated RequestContext claims.
"""

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.context import RequestContext
from app.core.exceptions import ExpiredTokenError, InvalidTokenError, RevokedTokenError
from app.core.security.audit import log_security_event
from app.core.security.jwt import decode_and_validate_token
from app.core.security.revocation import revocation_store


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Extracts Bearer token if present and populates RequestContext.
    Does not enforce mandatory auth on public endpoints (handled by route dependencies).
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = decode_and_validate_token(token, expected_type="access")
                if await revocation_store.is_jti_revoked(payload.jti):
                    log_security_event(
                        "REVOKED_TOKEN_PRESENTED", user_id=payload.sub, success=False
                    )
                    raise RevokedTokenError("Token has been revoked")

                # Populate RequestContext with validated user identity
                RequestContext.init(
                    request_id=RequestContext.get_request_id(),
                    correlation_id=RequestContext.get_correlation_id(),
                    user_id=payload.sub,
                    tenant_id=payload.tenant_id,
                    plant_id=payload.plant_id,
                    client_ip=RequestContext.get_client_ip(),
                    user_agent=RequestContext.get_user_agent(),
                )
            except (ExpiredTokenError, InvalidTokenError, RevokedTokenError):
                pass  # Dependency layer handles strict HTTP 401 response

        return await call_next(request)
