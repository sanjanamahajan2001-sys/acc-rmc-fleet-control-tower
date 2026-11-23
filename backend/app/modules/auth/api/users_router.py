"""
FastAPI Admin User Management & RBAC REST Router
Endpoints under /fleet-api/v1/users
"""

import datetime
import secrets
import string
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AuthorizationForbiddenError
from app.core.security.password import hash_password
from app.dependencies.auth import require_admin, require_section_permission
from app.dependencies.common import get_db_session
from app.modules.auth.models import AuditLog, Role, User, UserPreference, user_plant_scopes, user_roles
from sqlalchemy.orm.attributes import flag_modified
from app.modules.auth.schemas import (
    AdminUserCreateRequestDTO,
    AdminUserCreateResponseDTO,
    AdminUserDetailDTO,
    AdminUserUpdateRequestDTO,
    PlantScopeDTO,
    UserListResponseDTO,
    resolve_user_section_permissions,
)
from app.modules.erp.api.dependencies import TimedEnvelope
from app.modules.erp.models import Plant
from app.schemas.auth import TokenPayload
from app.schemas.envelope import APIResponse

users_router = APIRouter(prefix="/users", tags=["Admin User Management & RBAC"])


def generate_temp_password(length: int = 12) -> str:
    """Generates a clean, 100% web-safe, alphanumeric temporary password without confusing special characters."""
    alphabet = string.ascii_letters + string.digits
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and any(c.isdigit() for c in password)):
            return password




def to_user_detail_dto(user: User) -> AdminUserDetailDTO:
    roles_list = [role.name for role in user.roles]
    scopes_list = [
        PlantScopeDTO(id=str(p.id), code=p.code, name=p.name)
        for p in getattr(user, "plant_scopes", [])
    ]

    pref_settings = {}
    user_pref = getattr(user, "preferences", None)
    if user_pref and getattr(user_pref, "ui_settings", None):
        pref_settings = user_pref.ui_settings.get("section_permissions", {})
    resolved_perms = resolve_user_section_permissions(user.is_superuser, pref_settings)

    return AdminUserDetailDTO(
        id=str(user.id),
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        must_change_password=user.must_change_password,
        auth_stage="PASSWORD_CHANGE_REQUIRED" if user.must_change_password else "NORMAL",
        is_password_temporary=user.is_password_temporary,
        password_changed_at=user.password_changed_at,
        deleted_at=user.deleted_at,
        deleted_by=str(user.deleted_by) if user.deleted_by else None,
        roles=roles_list,
        section_permissions=resolved_perms,
        plant_scopes=scopes_list,
        last_login_at=user.last_login_at,
    )


@users_router.get("", response_model=APIResponse[UserListResponseDTO])
@users_router.get("/", response_model=APIResponse[UserListResponseDTO])
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    must_change_password: Optional[bool] = Query(None),
    admin_claims: TokenPayload = Depends(require_section_permission("user_management", "edit")),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[UserListResponseDTO]:
    query = select(User).options(
        selectinload(User.roles),
        selectinload(User.plant_scopes),
        selectinload(User.preferences),
    ).where(User.deleted_at.is_(None))

    if search:
        s = f"%{search}%"
        query = query.where((User.username.ilike(s)) | (User.email.ilike(s)) | (User.full_name.ilike(s)))

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    if must_change_password is not None:
        query = query.where(User.must_change_password == must_change_password)

    if role:
        query = query.join(User.roles).where(Role.name == role)

    # Count total
    count_stmt = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    # Pagination
    offset = (page - 1) * size
    query = query.order_by(User.created_at.desc()).offset(offset).limit(size)
    users = (await session.execute(query)).scalars().all()

    items = [to_user_detail_dto(u) for u in users]
    pages = (total + size - 1) // size if total > 0 else 1

    return envelope.success(
        UserListResponseDTO(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=pages,
        )
    )


@users_router.get("/{user_id}", response_model=APIResponse[AdminUserDetailDTO])
async def get_user_detail(
    user_id: str,
    admin_claims: TokenPayload = Depends(require_section_permission("user_management", "edit")),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[AdminUserDetailDTO]:
    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    stmt = select(User).options(
        selectinload(User.roles),
        selectinload(User.plant_scopes),
        selectinload(User.preferences),
    ).where(User.id == user_uuid, User.deleted_at.is_(None))

    user = (await session.execute(stmt)).scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return envelope.success(to_user_detail_dto(user))


@users_router.post("", response_model=APIResponse[AdminUserCreateResponseDTO])
@users_router.post("/", response_model=APIResponse[AdminUserCreateResponseDTO])
async def create_user(
    req: AdminUserCreateRequestDTO,
    request: Request,
    admin_claims: TokenPayload = Depends(require_section_permission("user_management", "edit")),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[AdminUserCreateResponseDTO]:
    # Uniqueness check
    clean_username = req.username.strip()
    normalized_email = req.email.strip().lower()
    dup_stmt = select(User).where((User.email == normalized_email) | (User.username == clean_username))
    if (await session.execute(dup_stmt)).scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or Email already exists")

    temp_password = generate_temp_password()
    password_h = hash_password(temp_password)

    # Pre-resolve Roles before user instantiation to prevent async lazy-load MissingGreenlet errors
    assigned_roles = []
    if req.role_ids:
        for r_id in req.role_ids:
            try:
                r_uuid = uuid.UUID(r_id)
                role = (await session.execute(select(Role).where(Role.id == r_uuid))).scalars().first()
            except ValueError:
                role = (await session.execute(select(Role).where(Role.name == r_id))).scalars().first()
            if role:
                assigned_roles.append(role)

    # Pre-resolve Plant Scopes before user instantiation
    assigned_plants = []
    if req.plant_ids:
        for p_id in req.plant_ids:
            try:
                p_uuid = uuid.UUID(p_id)
                plant = (await session.execute(select(Plant).where(Plant.id == p_uuid))).scalars().first()
            except ValueError:
                plant = (await session.execute(select(Plant).where(Plant.code == p_id))).scalars().first()
            if plant:
                assigned_plants.append(plant)

    user = User(
        username=clean_username,
        email=normalized_email,
        full_name=req.full_name,
        password_hash=password_h,
        must_change_password=True,
        is_password_temporary=True,
        password_changed_at=None,
        token_version=1,
        is_active=True,
        deleted_at=None,
        deleted_by=None,
        roles=assigned_roles,
        plant_scopes=assigned_plants,
    )
    session.add(user)
    await session.flush()

    # Initialize UserPreference with canonical section permissions
    init_perms = resolve_user_section_permissions(user.is_superuser, req.section_permissions)
    pref = UserPreference(
        user_id=user.id,
        ui_settings={"section_permissions": init_perms},
    )
    session.add(pref)

    await session.commit()
    
    # Eagerly load roles, plant_scopes, and preferences to prevent async lazy load issues
    reloaded_user = (await session.execute(
        select(User).options(
            selectinload(User.roles),
            selectinload(User.plant_scopes),
            selectinload(User.preferences),
        ).where(User.id == user.id)
    )).scalars().first()

    # Audit log (Zero plaintext passwords!)
    audit = AuditLog(
        user_id=uuid.UUID(admin_claims.sub),
        action="USER_CREATED",
        resource="users",
        details={"created_user_id": str(user.id), "username": user.username, "email": user.email},
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    session.add(audit)
    await session.commit()

    dto = AdminUserCreateResponseDTO(
        user=to_user_detail_dto(reloaded_user),
        temporary_password=temp_password,
    )
    return envelope.success(dto)



@users_router.patch("/{user_id}", response_model=APIResponse[AdminUserDetailDTO])
async def update_user(
    user_id: str,
    req: AdminUserUpdateRequestDTO,
    request: Request,
    admin_claims: TokenPayload = Depends(require_section_permission("user_management", "edit")),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[AdminUserDetailDTO]:
    try:
        target_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    stmt = select(User).options(
        selectinload(User.roles),
        selectinload(User.plant_scopes),
        selectinload(User.preferences),
    ).where(User.id == target_uuid, User.deleted_at.is_(None))

    user = (await session.execute(stmt)).scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    current_admin_uuid = uuid.UUID(admin_claims.sub)

    # Self & Last Admin Protection Guards
    if req.is_active is False:
        if user.id == current_admin_uuid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot disable your own administrative account")

        # Check last admin guard
        if user.is_superuser or any(r.name in ["Administrator", "admin"] for r in user.roles):
            admin_count_stmt = select(func.count(User.id)).where(User.is_active == True, User.deleted_at.is_(None))
            active_admins = (await session.execute(admin_count_stmt)).scalar_one()
            if active_admins <= 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot disable the sole remaining active Administrator account")

    security_state_changed = False

    if req.full_name is not None:
        user.full_name = req.full_name

    if req.email is not None:
        normalized_email = req.email.lower()
        if normalized_email != user.email:
            dup_stmt = select(User).where(User.email == normalized_email, User.id != user.id)
            if (await session.execute(dup_stmt)).scalars().first():
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
            user.email = normalized_email

    # Track granular audit events
    audit_events_to_emit = []

    if req.is_active is not None and req.is_active != user.is_active:
        user.is_active = req.is_active
        security_state_changed = True
        act = "USER_ENABLED" if req.is_active else "USER_DISABLED"
        audit_events_to_emit.append((act, {"target_user_id": str(user.id)}))

    # Role Changes
    if req.role_ids is not None:
        new_roles = []
        for r_id in req.role_ids:
            try:
                r_uuid = uuid.UUID(r_id)
                role = (await session.execute(select(Role).where(Role.id == r_uuid))).scalars().first()
            except ValueError:
                role = (await session.execute(select(Role).where(Role.name == r_id))).scalars().first()
            if role:
                new_roles.append(role)

        current_role_ids = {r.id for r in user.roles}
        new_role_ids = {r.id for r in new_roles}
        if current_role_ids != new_role_ids:
            old_role_names = [r.name for r in user.roles]
            user.roles = new_roles
            security_state_changed = True
            audit_events_to_emit.append((
                "USER_ROLE_CHANGED",
                {
                    "target_user_id": str(user.id),
                    "old_roles": old_role_names,
                    "new_roles": [r.name for r in new_roles],
                }
            ))

    # Plant Scope Changes
    if req.plant_ids is not None:
        new_plants = []
        for p_id in req.plant_ids:
            try:
                p_uuid = uuid.UUID(p_id)
                plant = (await session.execute(select(Plant).where(Plant.id == p_uuid))).scalars().first()
            except ValueError:
                plant = (await session.execute(select(Plant).where(Plant.code == p_id))).scalars().first()
            if plant:
                new_plants.append(plant)

        current_plant_ids = {p.id for p in user.plant_scopes}
        new_plant_ids = {p.id for p in new_plants}
        if current_plant_ids != new_plant_ids:
            old_plant_codes = [p.code for p in user.plant_scopes]
            user.plant_scopes = new_plants
            security_state_changed = True
            audit_events_to_emit.append((
                "USER_PLANT_SCOPE_CHANGED",
                {
                    "target_user_id": str(user.id),
                    "old_scopes": old_plant_codes,
                    "new_scopes": [p.code for p in new_plants],
                }
            ))

    # Section Permissions Changes
    if req.section_permissions is not None:
        user_pref = getattr(user, "preferences", None)
        if not user_pref:
            pref_stmt = select(UserPreference).where(UserPreference.user_id == user.id)
            user_pref = (await session.execute(pref_stmt)).scalars().first()
            if not user_pref:
                user_pref = UserPreference(user_id=user.id, ui_settings={})
                session.add(user_pref)
                user.preferences = user_pref

        current_ui_settings = dict(user_pref.ui_settings or {})
        old_perms = current_ui_settings.get("section_permissions", {})
        new_perms = resolve_user_section_permissions(user.is_superuser, req.section_permissions)

        if old_perms != new_perms:
            current_ui_settings["section_permissions"] = new_perms
            user_pref.ui_settings = current_ui_settings
            flag_modified(user_pref, "ui_settings")
            security_state_changed = True
            audit_events_to_emit.append((
                "USER_SECTION_PERMISSIONS_CHANGED",
                {
                    "target_user_id": str(user.id),
                    "old_permissions": old_perms,
                    "new_permissions": new_perms,
                }
            ))

    # Increment token_version IF AND ONLY IF security/authorization state changed!
    if security_state_changed:
        user.token_version += 1

    await session.commit()
    reloaded_user = (await session.execute(
        select(User).options(
            selectinload(User.roles),
            selectinload(User.plant_scopes),
            selectinload(User.preferences),
        ).where(User.id == user.id)
    )).scalars().first()

    # Emit primary update audit event
    audit = AuditLog(
        user_id=current_admin_uuid,
        action="USER_UPDATED",
        resource="users",
        details={"updated_user_id": str(user.id), "token_version_incremented": security_state_changed},
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    session.add(audit)

    # Emit granular sub-events
    for act, det in audit_events_to_emit:
        session.add(AuditLog(
            user_id=current_admin_uuid,
            action=act,
            resource="users",
            details=det,
            ip_address=request.client.host if request.client else "127.0.0.1",
        ))

    await session.commit()


    return envelope.success(to_user_detail_dto(reloaded_user))


@users_router.post("/{user_id}/reset-password", response_model=APIResponse[AdminUserCreateResponseDTO])
async def reset_user_password(
    user_id: str,
    request: Request,
    admin_claims: TokenPayload = Depends(require_section_permission("user_management", "edit")),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[AdminUserCreateResponseDTO]:
    try:
        target_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    stmt = select(User).options(
        selectinload(User.roles),
        selectinload(User.plant_scopes),
        selectinload(User.preferences),
    ).where(User.id == target_uuid, User.deleted_at.is_(None))

    user = (await session.execute(stmt)).scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    temp_password = generate_temp_password()
    user.password_hash = hash_password(temp_password)
    user.must_change_password = True
    user.is_password_temporary = True
    user.password_changed_at = None
    
    # Increment token_version to invalidate all active sessions immediately
    user.token_version += 1
    await session.commit()

    reloaded_user = (await session.execute(
        select(User).options(
            selectinload(User.roles),
            selectinload(User.plant_scopes),
            selectinload(User.preferences),
        ).where(User.id == user.id)
    )).scalars().first()

    audit = AuditLog(
        user_id=uuid.UUID(admin_claims.sub),
        action="USER_PASSWORD_RESET",
        resource="users",
        details={"target_user_id": str(user.id)},
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    session.add(audit)
    await session.commit()

    dto = AdminUserCreateResponseDTO(
        user=to_user_detail_dto(reloaded_user),
        temporary_password=temp_password,
    )
    return envelope.success(dto)



@users_router.delete("/{user_id}", response_model=APIResponse[dict[str, str]])
async def deactivate_user(
    user_id: str,
    request: Request,
    admin_claims: TokenPayload = Depends(require_section_permission("user_management", "edit")),
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[dict[str, str]]:
    try:
        target_uuid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    current_admin_uuid = uuid.UUID(admin_claims.sub)

    # Self-deactivation protection guard
    if target_uuid == current_admin_uuid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate your own administrative account")

    stmt = select(User).options(selectinload(User.roles)).where(User.id == target_uuid, User.deleted_at.is_(None))
    user = (await session.execute(stmt)).scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Last Administrator protection guard
    if user.is_superuser or any(r.name in ["Administrator", "admin"] for r in user.roles):

        admin_count_stmt = select(func.count(User.id)).where(User.is_active == True, User.deleted_at.is_(None))
        active_admins = (await session.execute(admin_count_stmt)).scalar_one()
        if active_admins <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate the sole remaining active Administrator account")

    user.is_active = False
    user.deleted_at = datetime.datetime.now(datetime.timezone.utc)
    user.deleted_by = current_admin_uuid
    user.token_version += 1
    await session.commit()

    audit = AuditLog(
        user_id=current_admin_uuid,
        action="USER_DEACTIVATED",
        resource="users",
        details={"deactivated_user_id": str(user.id)},
        ip_address=request.client.host if request.client else "127.0.0.1",
    )
    session.add(audit)
    await session.commit()

    return envelope.success({"message": "User successfully deactivated"})
