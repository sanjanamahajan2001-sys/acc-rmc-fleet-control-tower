"""
Phase 1 Unit & Integration Test Suite: Canonical Section-Based Permission Matrix
Tests schema contracts, resolution rules, admin user management API endpoints, and token version invalidation.
"""

import pytest
from uuid import uuid4
from fastapi import status
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.modules.auth.models import User, Role, AuditLog
from app.modules.auth.schemas import (
    PLATFORM_SECTIONS,
    get_full_admin_permissions,
    get_default_operator_permissions,
    resolve_user_section_permissions,
)
from app.core.security.password import hash_password
from app.core.security.jwt import create_access_token
from app.schemas.auth import AuthStage


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def get_admin_token(session: AsyncSession) -> tuple[User, str]:
    """Helper creating an active Admin user and returning Bearer token."""
    username = f"admin_{uuid4().hex[:8]}"
    admin_role = (await session.execute(select(Role).where(Role.name == "Administrator"))).scalars().first()
    if not admin_role:
        admin_role = Role(name="Administrator", description="System Administrator")
        session.add(admin_role)
        await session.commit()

    admin_user = User(
        username=username,
        email=f"{username}@fleetcontrol.io",
        password_hash=hash_password("AdminPass123!"),
        is_superuser=True,
        is_active=True,
        must_change_password=False,
        token_version=1,
    )
    admin_user.roles.append(admin_role)
    session.add(admin_user)
    await session.commit()

    token, _ = create_access_token(user_id=str(admin_user.id), token_version=1, auth_stage=AuthStage.NORMAL)
    return admin_user, token


@pytest.mark.asyncio
async def test_canonical_catalog_and_default_resolution():
    """Verify 14 canonical sections, full admin edit perms, and default operator perms."""
    assert len(PLATFORM_SECTIONS) == 14
    assert "platform_home" in PLATFORM_SECTIONS
    assert "site_dashboard" in PLATFORM_SECTIONS
    assert "overall_dashboard" in PLATFORM_SECTIONS
    assert "dispatch_analysis" in PLATFORM_SECTIONS
    assert "dispatch_optimization" in PLATFORM_SECTIONS
    assert "operational_intelligence" in PLATFORM_SECTIONS
    assert "predictive_intelligence" in PLATFORM_SECTIONS
    assert "control_tower_actions" in PLATFORM_SECTIONS
    assert "alerts" in PLATFORM_SECTIONS
    assert "reports" in PLATFORM_SECTIONS
    assert "erp_import" in PLATFORM_SECTIONS
    assert "erp_explorer" in PLATFORM_SECTIONS
    assert "settings" in PLATFORM_SECTIONS
    assert "user_management" in PLATFORM_SECTIONS

    admin_perms = get_full_admin_permissions()
    assert len(admin_perms) == 14
    for sec in PLATFORM_SECTIONS:
        assert admin_perms[sec] == "edit"

    op_perms = get_default_operator_permissions()
    assert len(op_perms) == 14
    assert op_perms["platform_home"] == "view"
    assert op_perms["dispatch_analysis"] == "view"
    assert op_perms["settings"] == "none"
    assert op_perms["user_management"] == "none"


@pytest.mark.asyncio
async def test_resolve_user_section_permissions_invariants():
    """Verify superuser bypass invariant and custom non-admin resolution."""
    # Superuser must ALWAYS receive edit across all sections regardless of input
    malicious_input = {sec: "none" for sec in PLATFORM_SECTIONS}
    superuser_perms = resolve_user_section_permissions(is_superuser=True, stored_perms=malicious_input)
    for sec in PLATFORM_SECTIONS:
        assert superuser_perms[sec] == "edit"

    # Non-admin without stored perms gets safe operator defaults
    default_res = resolve_user_section_permissions(is_superuser=False, stored_perms=None)
    assert default_res["platform_home"] == "view"
    assert default_res["settings"] == "none"
    assert default_res["user_management"] == "none"

    # Non-admin with explicit custom perms
    custom_input = {
        "erp_import": "edit",
        "reports": "edit",
        "invalid_section": "edit",  # should be ignored
        "platform_home": "invalid_level",  # should fall back to default
    }
    custom_res = resolve_user_section_permissions(is_superuser=False, stored_perms=custom_input)
    assert custom_res["erp_import"] == "edit"
    assert custom_res["reports"] == "edit"
    assert "invalid_section" not in custom_res
    assert custom_res["platform_home"] == "view"  # fell back to safe default
    assert custom_res["settings"] == "none"


@pytest.mark.asyncio
async def test_create_user_with_section_permissions(session: AsyncSession):
    """Admin creates a user passing custom section_permissions; persists and returns correctly."""
    _, admin_token = await get_admin_token(session)

    new_username = f"demo_user_{uuid4().hex[:8]}"
    new_email = f"{new_username}@fleetcontrol.io"
    custom_perms = {
        "platform_home": "view",
        "site_dashboard": "view",
        "overall_dashboard": "view",
        "dispatch_analysis": "view",
        "dispatch_optimization": "view",
        "operational_intelligence": "view",
        "predictive_intelligence": "view",
        "control_tower_actions": "view",
        "alerts": "view",
        "reports": "view",
        "erp_import": "none",
        "erp_explorer": "view",
        "settings": "none",
        "user_management": "none",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/fleet-api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": new_username,
                "email": new_email,
                "full_name": "Demo Operational Viewer",
                "section_permissions": custom_perms,
            },
        )
        assert res.status_code == status.HTTP_200_OK
        data = res.json()["data"]
        user_detail = data["user"]
        assert user_detail["username"] == new_username
        assert "section_permissions" in user_detail
        assert user_detail["section_permissions"]["erp_import"] == "none"
        assert user_detail["section_permissions"]["settings"] == "none"
        assert user_detail["section_permissions"]["dispatch_analysis"] == "view"

        # Verify querying user detail endpoint returns the same section_permissions
        get_res = await client.get(
            f"/fleet-api/v1/users/{user_detail['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert get_res.status_code == status.HTTP_200_OK
        detail_data = get_res.json()["data"]
        assert detail_data["section_permissions"] == user_detail["section_permissions"]


@pytest.mark.asyncio
async def test_update_user_section_permissions_invalidates_tokens(session: AsyncSession):
    """Updating section permissions increments token_version and invalidates old user tokens."""
    _, admin_token = await get_admin_token(session)

    target_user = User(
        username=f"target_{uuid4().hex[:8]}",
        email=f"target_{uuid4().hex[:8]}@fleetcontrol.io",
        password_hash=hash_password("Pass123!"),
        is_superuser=False,
        is_active=True,
        token_version=1,
    )
    session.add(target_user)
    await session.commit()
    target_id = str(target_user.id)
    target_token, _ = create_access_token(user_id=target_id, token_version=1, auth_stage=AuthStage.NORMAL)

    updated_perms = {
        "erp_import": "edit",
        "reports": "edit",
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Target user's session works initially
        me_res1 = await client.get("/fleet-api/v1/auth/me", headers={"Authorization": f"Bearer {target_token}"})
        assert me_res1.status_code == status.HTTP_200_OK

        # Admin updates section permissions
        patch_res = await client.patch(
            f"/fleet-api/v1/users/{target_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "section_permissions": updated_perms,
            },
        )
        assert patch_res.status_code == status.HTTP_200_OK
        data = patch_res.json()["data"]
        assert data["section_permissions"]["erp_import"] == "edit"
        assert data["section_permissions"]["reports"] == "edit"

        # Verify old target user token is now invalidated (401 due to token_version increment)
        me_res2 = await client.get("/fleet-api/v1/auth/me", headers={"Authorization": f"Bearer {target_token}"})
        assert me_res2.status_code == status.HTTP_401_UNAUTHORIZED

    # Verify granular audit log was written
    audit_stmt = (
        select(AuditLog)
        .where(
            AuditLog.action == "USER_SECTION_PERMISSIONS_CHANGED",
            AuditLog.resource == "users",
        )
        .order_by(AuditLog.created_at.desc())
    )
    audit = (await session.execute(audit_stmt)).scalars().first()
    assert audit is not None
    assert audit.details["target_user_id"] == target_id
    assert audit.details["new_permissions"]["erp_import"] == "edit"
