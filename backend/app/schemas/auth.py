"""
Auth Schemas & Data Transfer Objects

Defines TokenPayload, TokenResponse, and RefreshTokenRequest DTOs.
"""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class AuthStage(str, Enum):
    NORMAL = "NORMAL"
    PASSWORD_CHANGE_REQUIRED = "PASSWORD_CHANGE_REQUIRED"


class TokenPayload(BaseModel):
    """
    Standardized payload claims contained within a validated JWT.
    """

    sub: str = Field(description="User ID (Subject)")
    jti: str = Field(description="Unique JWT ID for revocation tracking")
    type: Literal["access", "refresh"] = Field(description="Token type discriminator")
    tenant_id: str | None = Field(default=None, description="Optional tenant ID")
    plant_id: str | None = Field(default=None, description="Optional plant ID")
    token_version: int = Field(default=1, description="Database token version for session invalidation")
    auth_stage: AuthStage = Field(default=AuthStage.NORMAL, description="Current authentication stage")
    exp: int = Field(description="Expiration epoch timestamp")
    iat: int = Field(description="Issued-at epoch timestamp")



class TokenResponse(BaseModel):
    """
    Standard dual-token response DTO.
    """

    access_token: str = Field(description="Short-lived JWT Access Token")
    refresh_token: str = Field(description="Long-lived JWT Refresh Token")
    token_type: str = Field(default="Bearer", description="Token authentication scheme")
    expires_in: int = Field(description="Access token lifespan in seconds")


class RefreshTokenRequest(BaseModel):
    """
    DTO for requesting a token refresh.
    """

    refresh_token: str = Field(description="Active Refresh Token")
