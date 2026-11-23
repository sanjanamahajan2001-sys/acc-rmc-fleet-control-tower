"""
Global Exception Handlers

Translates platform domain and security exceptions into standard APIResponse[T] envelopes.
"""

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

from app.core.context import RequestContext
from app.core.exceptions import (
    AuthenticationError,
    DatabaseConnectionError,
    DomainValidationError,
    DuplicateKeyError,
    ExpiredTokenError,
    InvalidTokenError,
    OptimisticLockError,
    RecordNotFoundError,
    RevokedTokenError,
    AuthorizationForbiddenError,
)
from app.core.logging import get_logger
from app.schemas.envelope import APIResponse

logger = get_logger("app.exceptions")


def register_exception_handlers(app: FastAPI) -> None:
    """
    Registers platform-wide exception handlers on the FastAPI application instance.
    """

    # Security Exception Handlers (401 Unauthorized)
    @app.exception_handler(AuthenticationError)
    async def auth_error_handler(
        request: Request, exc: AuthenticationError
    ) -> JSONResponse:
        envelope = APIResponse.fail(
            error_code="AUTHENTICATION_REQUIRED",
            message=exc.message,
            correlation_id=RequestContext.get_correlation_id(),
            request_id=RequestContext.get_request_id(),
            duration_ms=RequestContext.get_execution_duration_ms(),
            details=exc.details,
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=envelope.model_dump(),
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(ExpiredTokenError)
    async def expired_token_handler(
        request: Request, exc: ExpiredTokenError
    ) -> JSONResponse:
        envelope = APIResponse.fail(
            error_code="TOKEN_EXPIRED",
            message=exc.message,
            correlation_id=RequestContext.get_correlation_id(),
            request_id=RequestContext.get_request_id(),
            duration_ms=RequestContext.get_execution_duration_ms(),
            details=exc.details,
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=envelope.model_dump(),
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_token", error_description="The token has expired"'
            },
        )

    @app.exception_handler(InvalidTokenError)
    async def invalid_token_handler(
        request: Request, exc: InvalidTokenError
    ) -> JSONResponse:
        envelope = APIResponse.fail(
            error_code="INVALID_TOKEN",
            message=exc.message,
            correlation_id=RequestContext.get_correlation_id(),
            request_id=RequestContext.get_request_id(),
            duration_ms=RequestContext.get_execution_duration_ms(),
            details=exc.details,
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=envelope.model_dump(),
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )

    @app.exception_handler(RevokedTokenError)
    async def revoked_token_handler(
        request: Request, exc: RevokedTokenError
    ) -> JSONResponse:
        envelope = APIResponse.fail(
            error_code="TOKEN_REVOKED",
            message=exc.message,
            correlation_id=RequestContext.get_correlation_id(),
            request_id=RequestContext.get_request_id(),
            duration_ms=RequestContext.get_execution_duration_ms(),
            details=exc.details,
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=envelope.model_dump(),
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_token", error_description="The token has been revoked"'
            },
        )

    @app.exception_handler(AuthorizationForbiddenError)
    async def authorization_forbidden_handler(
        request: Request, exc: AuthorizationForbiddenError
    ) -> JSONResponse:
        envelope = APIResponse.fail(
            error_code="FORBIDDEN",
            message=exc.message,
            correlation_id=RequestContext.get_correlation_id(),
            request_id=RequestContext.get_request_id(),
            duration_ms=RequestContext.get_execution_duration_ms(),
            details=exc.details,
        )
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=envelope.model_dump(),
        )


    # Core Database & Validation Handlers
    @app.exception_handler(RecordNotFoundError)
    async def record_not_found_handler(
        request: Request, exc: RecordNotFoundError
    ) -> JSONResponse:
        envelope = APIResponse.fail(
            error_code="NOT_FOUND",
            message=exc.message,
            correlation_id=RequestContext.get_correlation_id(),
            request_id=RequestContext.get_request_id(),
            duration_ms=RequestContext.get_execution_duration_ms(),
            details=exc.details,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND, content=envelope.model_dump()
        )

    @app.exception_handler(OptimisticLockError)
    async def optimistic_lock_handler(
        request: Request, exc: OptimisticLockError
    ) -> JSONResponse:
        envelope = APIResponse.fail(
            error_code="CONCURRENCY_CONFLICT",
            message=exc.message,
            correlation_id=RequestContext.get_correlation_id(),
            request_id=RequestContext.get_request_id(),
            duration_ms=RequestContext.get_execution_duration_ms(),
            details=exc.details,
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT, content=envelope.model_dump()
        )

    @app.exception_handler(DuplicateKeyError)
    async def duplicate_key_handler(
        request: Request, exc: DuplicateKeyError
    ) -> JSONResponse:
        envelope = APIResponse.fail(
            error_code="DUPLICATE_RESOURCE",
            message=exc.message,
            correlation_id=RequestContext.get_correlation_id(),
            request_id=RequestContext.get_request_id(),
            duration_ms=RequestContext.get_execution_duration_ms(),
            details=exc.details,
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT, content=envelope.model_dump()
        )

    @app.exception_handler(DomainValidationError)
    async def domain_validation_handler(
        request: Request, exc: DomainValidationError
    ) -> JSONResponse:
        envelope = APIResponse.fail(
            error_code="DUPLICATE_WORKBOOK",
            message=exc.message,
            correlation_id=RequestContext.get_correlation_id(),
            request_id=RequestContext.get_request_id(),
            duration_ms=RequestContext.get_execution_duration_ms(),
            details=exc.details,
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT, content=envelope.model_dump()
        )



    @app.exception_handler(DatabaseConnectionError)
    async def db_connection_handler(
        request: Request, exc: DatabaseConnectionError
    ) -> JSONResponse:
        logger.error(
            "Database connection failure", error=exc.message, details=exc.details
        )
        envelope = APIResponse.fail(
            error_code="SERVICE_UNAVAILABLE",
            message="Database connection error",
            correlation_id=RequestContext.get_correlation_id(),
            request_id=RequestContext.get_request_id(),
            duration_ms=RequestContext.get_execution_duration_ms(),
        )
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=envelope.model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details: list[dict[str, Any]] = [
            {
                "loc": [str(loc) for loc in err["loc"]],
                "msg": err["msg"],
                "type": err["type"],
            }
            for err in exc.errors()
        ]
        envelope = APIResponse.fail(
            error_code="VALIDATION_ERROR",
            message="Request validation failed",
            correlation_id=RequestContext.get_correlation_id(),
            request_id=RequestContext.get_request_id(),
            duration_ms=RequestContext.get_execution_duration_ms(),
            details=details,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=envelope.model_dump(),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        envelope = APIResponse.fail(
            error_code=f"HTTP_{exc.status_code}",
            message=str(exc.detail),
            correlation_id=RequestContext.get_correlation_id(),
            request_id=RequestContext.get_request_id(),
            duration_ms=RequestContext.get_execution_duration_ms(),
        )
        return JSONResponse(status_code=exc.status_code, content=envelope.model_dump())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("Unhandled server exception", error=str(exc))
        envelope = APIResponse.fail(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected server error occurred",
            correlation_id=RequestContext.get_correlation_id(),
            request_id=RequestContext.get_request_id(),
            duration_ms=RequestContext.get_execution_duration_ms(),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=envelope.model_dump(),
        )
