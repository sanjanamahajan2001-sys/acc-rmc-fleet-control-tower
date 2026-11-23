"""
FastAPI Authentication REST Router Endpoints
Workstream X.2 Production Endpoints
"""

import datetime
import uuid
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, func

from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession


from app.dependencies.common import get_db_session
from app.dependencies.auth import get_current_user_claims, require_authenticated_user

from app.modules.erp.api.dependencies import TimedEnvelope
from app.modules.auth.models import User, UserPreference, AuditLog, Role
from app.modules.auth.schemas import (
    AuthStage,
    ChangePasswordRequestDTO,
    LoginRequest,
    LoginResponseDTO,
    SessionResponseDTO,
    UserDTO,
    UserPreferenceDTO,
    resolve_user_section_permissions,
)
from app.core.security.password import hash_password, verify_password
from app.core.security.jwt import create_access_token, decode_and_validate_token
from app.schemas.auth import TokenPayload
from app.schemas.envelope import APIResponse


router = APIRouter(prefix="/auth", tags=["Authentication & Access Control"])


@router.post("/login", response_model=APIResponse[LoginResponseDTO])
async def login(
    login_req: LoginRequest,
    response: Response,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[LoginResponseDTO]:
    # Query user by username or email (case-insensitive)
    input_identifier = login_req.username.strip().lower()
    stmt = select(User).options(selectinload(User.roles)).where(
        (func.lower(User.username) == input_identifier) | (func.lower(User.email) == input_identifier)
    )
    user = (await session.execute(stmt)).scalars().first()


    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Check lock status
    if user.locked_until and user.locked_until > datetime.datetime.now(datetime.timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked due to failed login attempts. Please try again later.",
        )

    # Verify disabled status
    if not user.is_active or user.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Verify password
    clean_password = login_req.password.strip()
    is_match = verify_password(clean_password, user.password_hash)
    if not is_match:
        from app.core.logging import get_logger
        get_logger("auth.login").warning(
            f"[LOGIN DEBUG] Failed password match for user '{user.username}'. "
            f"Provided password len={len(clean_password)}, hash={user.password_hash[:25]}..."
        )
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=15)
        await session.commit()

        # Audit log failed login
        audit = AuditLog(
            user_id=user.id,
            action="USER_LOGIN_FAILED",
            resource="auth",
            details={"username": login_req.username, "reason": "invalid_password"},
            ip_address=request.client.host if request.client else "127.0.0.1",
        )
        session.add(audit)
        await session.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )


    # Successful login: Reset lock & counters
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.datetime.now(datetime.timezone.utc)

    # Fetch user preferences & roles
    pref_stmt = select(UserPreference).where(UserPreference.user_id == user.id)
    pref = (await session.execute(pref_stmt)).scalars().first()

    if not pref:
        pref = UserPreference(user_id=user.id)
        session.add(pref)

    audit = AuditLog(
        user_id=user.id,
        action="USER_LOGIN_SUCCESS",
        resource="auth",
        details={"username": user.username},
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    session.add(audit)
    await session.commit()

    # Determine Auth Stage & Issue JWT Access Token
    auth_stage = AuthStage.PASSWORD_CHANGE_REQUIRED if user.must_change_password else AuthStage.NORMAL
    token_expiry = 86400 if login_req.remember_me else 3600
    token_str, jti = create_access_token(
        user_id=str(user.id),
        token_version=user.token_version,
        auth_stage=auth_stage,
        expires_delta_seconds=token_expiry,
    )

    # Set HTTP-Only Secure Cookie
    response.set_cookie(
        key="access_token",
        value=token_str,
        httponly=True,
        samesite="lax",
        secure=False,  # Set True in production HTTPS
        max_age=token_expiry,
    )

    roles_list = [role.name for role in getattr(user, "roles", [])]
    if user.is_superuser and "Administrator" not in roles_list:
        roles_list.append("Administrator")

    pref_settings = pref.ui_settings.get("section_permissions") if (pref and getattr(pref, "ui_settings", None)) else None
    resolved_perms = resolve_user_section_permissions(user.is_superuser, pref_settings)

    user_dto = UserDTO(
        id=str(user.id),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        must_change_password=user.must_change_password,
        auth_stage=auth_stage.value,
        roles=roles_list if roles_list else ["Operator"],
        section_permissions=resolved_perms,
        preferences=UserPreferenceDTO.model_validate(pref),
        last_login_at=user.last_login_at,
    )


    dto = LoginResponseDTO(
        access_token=token_str,
        token_type="bearer",
        expires_in=token_expiry,
        auth_stage=auth_stage.value,
        user=user_dto,
    )
    return envelope.success(dto)


@router.post("/change-password", response_model=APIResponse[LoginResponseDTO])
async def change_password(
    req_body: ChangePasswordRequestDTO,
    response: Response,
    request: Request,
    claims: TokenPayload = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[LoginResponseDTO]:
    if req_body.new_password != req_body.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password confirmation does not match",
        )

    if len(req_body.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters in length",
        )

    user_uuid = uuid.UUID(claims.sub)
    user = (await session.execute(select(User).options(selectinload(User.roles)).where(User.id == user_uuid))).scalars().first()

    if not user or not user.is_active or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User account inactive or not found")

    # Update Password Hash using Argon2id
    user.password_hash = hash_password(req_body.new_password)
    user.must_change_password = False
    user.is_password_temporary = False
    user.password_changed_at = datetime.datetime.now(datetime.timezone.utc)
    
    # Increment token_version to invalidate old restricted token immediately
    user.token_version += 1
    await session.commit()

    # Log audit event (Zero plaintext passwords!)
    audit = AuditLog(
        user_id=user.id,
        action="USER_PASSWORD_CHANGED",
        resource="auth",
        details={"username": user.username},
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    session.add(audit)
    await session.commit()

    # Issue FRESH NORMAL Access Token with updated token_version
    fresh_token_str, jti = create_access_token(
        user_id=str(user.id),
        token_version=user.token_version,
        auth_stage=AuthStage.NORMAL,
        expires_delta_seconds=3600,
    )

    response.set_cookie(
        key="access_token",
        value=fresh_token_str,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=3600,
    )

    pref = (await session.execute(select(UserPreference).where(UserPreference.user_id == user.id))).scalars().first()

    roles_list = [role.name for role in getattr(user, "roles", [])]
    if user.is_superuser and "Administrator" not in roles_list:
        roles_list.append("Administrator")

    pref_settings = pref.ui_settings.get("section_permissions") if (pref and getattr(pref, "ui_settings", None)) else None
    resolved_perms = resolve_user_section_permissions(user.is_superuser, pref_settings)

    user_dto = UserDTO(
        id=str(user.id),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        must_change_password=False,
        auth_stage=AuthStage.NORMAL.value,
        roles=roles_list if roles_list else ["Operator"],
        section_permissions=resolved_perms,
        preferences=UserPreferenceDTO.model_validate(pref) if pref else None,
        last_login_at=user.last_login_at,
    )


    dto = LoginResponseDTO(
        access_token=fresh_token_str,
        token_type="bearer",
        expires_in=3600,
        auth_stage=AuthStage.NORMAL.value,
        user=user_dto,
    )
    return envelope.success(dto)


@router.post("/logout", response_model=APIResponse[dict[str, str]])
async def logout(
    response: Response,
    request: Request,
    claims: Optional[TokenPayload] = Depends(get_current_user_claims),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[dict[str, str]]:
    if claims and claims.sub:
        try:
            u_uuid = uuid.UUID(claims.sub)
            audit = AuditLog(
                user_id=u_uuid,
                action="USER_LOGOUT",
                resource="auth",
                details={"auth_stage": claims.auth_stage.value if hasattr(claims.auth_stage, "value") else str(claims.auth_stage)},
                ip_address=request.client.host if request.client else "127.0.0.1",
            )
            session.add(audit)
            await session.commit()
        except Exception:
            pass

    response.delete_cookie(key="access_token")
    return envelope.success({"message": "Successfully logged out"})



@router.get("/me", response_model=APIResponse[UserDTO])
async def get_current_user(
    claims: TokenPayload = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[UserDTO]:
    user_uuid = uuid.UUID(claims.sub)
    user = (await session.execute(select(User).where(User.id == user_uuid))).scalars().first()

    if not user or not user.is_active or user.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    pref = (await session.execute(select(UserPreference).where(UserPreference.user_id == user.id))).scalars().first()

    pref_settings = pref.ui_settings.get("section_permissions") if (pref and getattr(pref, "ui_settings", None)) else None
    resolved_perms = resolve_user_section_permissions(user.is_superuser, pref_settings)

    user_dto = UserDTO(
        id=str(user.id),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        must_change_password=user.must_change_password,
        auth_stage=claims.auth_stage.value if isinstance(claims.auth_stage, AuthStage) else str(claims.auth_stage),
        roles=["Administrator"] if user.is_superuser else ["Operator"],
        section_permissions=resolved_perms,
        preferences=UserPreferenceDTO.model_validate(pref) if pref else None,
        last_login_at=user.last_login_at,
    )
    return envelope.success(user_dto)

