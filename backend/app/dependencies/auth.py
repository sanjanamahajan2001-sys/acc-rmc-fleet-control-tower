import uuid
from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthenticationError, AuthorizationForbiddenError, InvalidTokenError, RevokedTokenError
from app.core.security.jwt import decode_and_validate_token
from app.core.security.revocation import revocation_store
from app.dependencies.common import get_db_session
from app.modules.auth.models import User
from app.schemas.auth import AuthStage, TokenPayload

# Explicitly allowed endpoints when auth_stage is PASSWORD_CHANGE_REQUIRED
PERMITTED_PASSWORD_CHANGE_ROUTES = {
    "/fleet-api/v1/auth/change-password",
    "/fleet-api/v1/auth/logout",
    "/fleet-api/v1/auth/me",
    "/auth/change-password",
    "/auth/logout",
    "/auth/me",
}


async def get_current_user_claims(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    token: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> TokenPayload:
    """
    Dependency extracting Bearer token, validating against DB authoritative state:
    1. Signature & expiration check
    2. User exists in DB
    3. User is_active == True and deleted_at is None
    4. JWT token_version == DB user.token_version
    5. auth_stage route permission guard (blocks operational APIs when PASSWORD_CHANGE_REQUIRED)
    """
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split(" ")[1]
    elif token:
        raw_token = token

    if not raw_token:
        raise AuthenticationError(
            "Missing or invalid Authorization header or token query param"
        )

    payload = decode_and_validate_token(raw_token, expected_type="access")

    if await revocation_store.is_jti_revoked(payload.jti):
        raise RevokedTokenError("Token has been revoked")

    # Authoritative DB user check
    try:
        user_uuid = uuid.UUID(payload.sub)
    except ValueError as exc:
        raise InvalidTokenError("Invalid user ID in token subject") from exc

    stmt = select(User).where(User.id == user_uuid)
    user = (await session.execute(stmt)).scalars().first()

    if not user:
        raise AuthenticationError("User account no longer exists")

    if not user.is_active or user.deleted_at is not None:
        raise AuthenticationError("User account is disabled or deactivated")

    # Session Invalidation Check: JWT token_version vs DB token_version
    if payload.token_version != user.token_version:
        raise AuthenticationError("Session has been invalidated due to a security update or password reset")

    # Authoritative Auth Stage Check
    effective_stage = AuthStage.PASSWORD_CHANGE_REQUIRED if user.must_change_password else AuthStage.NORMAL

    # Route Protection for PASSWORD_CHANGE_REQUIRED
    if effective_stage == AuthStage.PASSWORD_CHANGE_REQUIRED:
        req_path = request.url.path
        if req_path not in PERMITTED_PASSWORD_CHANGE_ROUTES:
            raise AuthorizationForbiddenError(
                "Must complete mandatory password change before accessing operational endpoints",
                details={"auth_stage": effective_stage.value, "path": req_path}
            )

    # Attach live auth_stage to payload
    payload.auth_stage = effective_stage
    return payload


async def get_optional_user_claims(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    token: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> TokenPayload | None:
    """
    Optional token extractor: returns TokenPayload if valid token supplied, else None without raising 401.
    """
    raw_token = None
    if authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split(" ")[1]
    elif token:
        raw_token = token

    if not raw_token:
        return None

    try:
        return await get_current_user_claims(request, authorization, token, session)
    except Exception:
        return None


async def require_authenticated_user(
    claims: TokenPayload = Depends(get_current_user_claims),  # noqa: B008
) -> TokenPayload:
    """
    Reusable FastAPI route dependency enforcing mandatory authenticated user access.
    Returns validated TokenPayload claims.
    """
    return claims


async def require_admin(
    claims: TokenPayload = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db_session),
) -> TokenPayload:
    """
    Reusable FastAPI route dependency enforcing mandatory Administrator access.
    Queries live DB user and roles authoritatively.
    Raises AuthorizationForbiddenError if user is not a superuser or does not hold Administrator role.
    """
    user_uuid = uuid.UUID(claims.sub)
    stmt = select(User).options(selectinload(User.roles)).where(User.id == user_uuid)
    user = (await session.execute(stmt)).scalars().first()

    if not user or not user.is_active or user.deleted_at is not None:
        raise AuthorizationForbiddenError("Administrator authorization required")

    if user.is_superuser:
        return claims

    # Check assigned roles
    role_names = [role.name for role in user.roles]
    if "Administrator" in role_names or "admin" in role_names:
        return claims

    raise AuthorizationForbiddenError("Administrator authorization required")


def require_section_permission(section: str, level: str = "edit"):
    """
    Reusable FastAPI route dependency factory enforcing granular section permissions.
    - Superusers and users with Administrator/admin roles have universal bypass.
    - Other users must have at least the required level ('view' or 'edit') in their section_permissions.
    - Raises AuthorizationForbiddenError (403) if authorization fails.
    """
    async def _dependency(
        claims: TokenPayload = Depends(get_current_user_claims),
        session: AsyncSession = Depends(get_db_session),
    ) -> TokenPayload:
        user_uuid = uuid.UUID(claims.sub)
        stmt = select(User).options(
            selectinload(User.roles),
            selectinload(User.preferences),
        ).where(User.id == user_uuid)
        user = (await session.execute(stmt)).scalars().first()

        if not user or not user.is_active or user.deleted_at is not None:
            raise AuthorizationForbiddenError(f"Authorization required for section '{section}'")

        if user.is_superuser:
            return claims

        role_names = [role.name for role in (user.roles or [])]
        if "Administrator" in role_names or "admin" in role_names:
            return claims

        pref = user.preferences
        pref_settings = pref.ui_settings.get("section_permissions") if (pref and getattr(pref, "ui_settings", None)) else None
        from app.modules.auth.schemas import resolve_user_section_permissions
        resolved_perms = resolve_user_section_permissions(user.is_superuser, pref_settings)

        user_level = resolved_perms.get(section, "none")
        if user_level == "none":
            raise AuthorizationForbiddenError(
                f"Access denied: Account lacks permissions for section '{section}'",
                details={"section": section, "required_level": level, "current_level": user_level}
            )

        if level == "edit" and user_level != "edit":
            raise AuthorizationForbiddenError(
                f"Write access denied: Section '{section}' is configured as view-only for your account",
                details={"section": section, "required_level": level, "current_level": user_level}
            )

        return claims

    return _dependency
