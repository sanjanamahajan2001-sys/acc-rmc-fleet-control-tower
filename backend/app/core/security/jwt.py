"""
Dual-Token JWT Issuance & Validation Engine

Generates and validates short-lived access tokens and long-lived refresh tokens.
Supports HS256 algorithm with future RS256 compatibility.
"""

import time
import uuid

import jwt

from app.core.config import settings
from app.core.exceptions import ExpiredTokenError, InvalidTokenError
from app.schemas.auth import AuthStage, TokenPayload


def create_access_token(
    user_id: uuid.UUID | str,
    tenant_id: str | None = None,
    plant_id: str | None = None,
    token_version: int = 1,
    auth_stage: AuthStage | str = AuthStage.NORMAL,
    expires_delta_seconds: int = 900,  # Default 15 mins
) -> tuple[str, str]:
    """
    Generates a short-lived access token.
    Returns tuple of (encoded_jwt_string, jti).
    """
    now = int(time.time())
    jti = str(uuid.uuid4())
    stage_val = auth_stage.value if isinstance(auth_stage, AuthStage) else str(auth_stage)
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "type": "access",
        "tenant_id": tenant_id,
        "plant_id": plant_id,
        "token_version": token_version,
        "auth_stage": stage_val,
        "iat": now,
        "exp": now + expires_delta_seconds,
    }
    encoded = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")
    return encoded, jti



def create_refresh_token(
    user_id: uuid.UUID | str, expires_delta_seconds: int = 604800  # Default 7 days
) -> tuple[str, str]:
    """
    Generates a long-lived refresh token.
    Returns tuple of (encoded_jwt_string, jti).
    """
    now = int(time.time())
    jti = str(uuid.uuid4())
    payload = {
        "sub": str(user_id),
        "jti": jti,
        "type": "refresh",
        "iat": now,
        "exp": now + expires_delta_seconds,
    }
    encoded = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")
    return encoded, jti


def decode_and_validate_token(
    token: str, expected_type: str | None = None
) -> TokenPayload:
    """
    Decodes and strictly validates a JWT token's signature, expiration, and claims.
    Raises ExpiredTokenError or InvalidTokenError on failure.
    """
    try:
        raw_payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=["HS256"],
            options={"verify_exp": True, "verify_iat": True},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ExpiredTokenError("Token has expired") from exc
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(f"Invalid token signature or payload: {exc!s}") from exc

    try:
        payload = TokenPayload(**raw_payload)
    except Exception as exc:
        raise InvalidTokenError("Token claims schema validation failed") from exc

    if expected_type and payload.type != expected_type:
        raise InvalidTokenError(
            f"Invalid token type: expected '{expected_type}', got '{payload.type}'"
        )

    return payload
