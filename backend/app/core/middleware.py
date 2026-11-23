"""
Platform Global Middleware Pipeline

Execution Order:
Incoming Request
  │
  ├── 1. RequestID / CorrelationID Middleware  (Extracts/generates X-Request-ID & X-Correlation-ID)
  │
  ├── 2. RequestContext Middleware            (Initializes ContextVars with IP, User-Agent & timer)
  │
  ├── 3. Structured Request Logging Middleware (Logs request entry & exit with execution_duration_ms)
  │
  └── CORS Middleware & Router Execution
"""

import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.context import RequestContext
from app.core.logging import get_logger

logger = get_logger("app.middleware")


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Extracts or generates X-Request-ID and X-Correlation-ID HTTP headers.
    Ensures headers are propagated into response headers and RequestContext.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        correlation_id = request.headers.get("X-Correlation-ID") or request_id

        # Extract context fields
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        user_id = request.headers.get("X-User-ID")
        tenant_id = request.headers.get("X-Tenant-ID")
        plant_id = request.headers.get("X-Plant-ID")

        # Initialize thread/async-safe RequestContext
        RequestContext.init(
            request_id=request_id,
            correlation_id=correlation_id,
            user_id=user_id,
            tenant_id=tenant_id,
            plant_id=plant_id,
            client_ip=client_ip,
            user_agent=user_agent,
        )

        response: Response = await call_next(request)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs structured request entry, completion status, and execution duration.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        method = request.method

        # Skip noisy health check logs
        if path.startswith("/health"):
            return await call_next(request)

        log = logger.bind(
            request_id=RequestContext.get_request_id(),
            correlation_id=RequestContext.get_correlation_id(),
            method=method,
            path=path,
            client_ip=RequestContext.get_client_ip(),
        )

        log.info("HTTP Request Received")
        response: Response = await call_next(request)
        duration_ms = RequestContext.get_execution_duration_ms()

        log.info(
            "HTTP Request Completed",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response


class ForcedPasswordChangeMiddleware(BaseHTTPMiddleware):
    """
    Middleware validating JWT Bearer tokens on incoming requests.
    If the authenticated user has auth_stage == "PASSWORD_CHANGE_REQUIRED",
    blocks access to all operational endpoints except permitted auth routes with 403 Forbidden.
    """

    PERMITTED_ROUTES = {
        "/fleet-api/v1/auth/change-password",
        "/fleet-api/v1/auth/logout",
        "/fleet-api/v1/auth/me",
        "/auth/change-password",
        "/auth/logout",
        "/auth/me",
        "/health",
        "/fleet-api/v1/health",
        "/docs",
        "/openapi.json",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if path in self.PERMITTED_ROUTES or path.startswith("/fleet-api/v1/auth/login") or path.startswith("/auth/login"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        raw_token = None
        if auth_header and auth_header.startswith("Bearer "):
            raw_token = auth_header.split(" ")[1]
        elif "access_token" in request.cookies:
            raw_token = request.cookies.get("access_token")

        if raw_token:
            try:
                from app.core.security.jwt import decode_and_validate_token
                payload = decode_and_validate_token(raw_token, expected_type="access")
                if payload.auth_stage == "PASSWORD_CHANGE_REQUIRED" or payload.auth_stage.value == "PASSWORD_CHANGE_REQUIRED":
                    from fastapi.responses import JSONResponse
                    from app.schemas.envelope import APIResponse
                    envelope = APIResponse.fail(
                        error_code="FORBIDDEN",
                        message="Must complete mandatory password change before accessing operational endpoints",
                        correlation_id=RequestContext.get_correlation_id(),
                        request_id=RequestContext.get_request_id(),
                        duration_ms=RequestContext.get_execution_duration_ms(),
                        details={"auth_stage": "PASSWORD_CHANGE_REQUIRED", "path": path},
                    )
                    return JSONResponse(
                        status_code=403,
                        content=envelope.model_dump(),
                    )
            except Exception:
                pass  # Let standard route dependencies handle invalid/expired tokens

        return await call_next(request)

