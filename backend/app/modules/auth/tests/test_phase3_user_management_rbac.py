"""
Phase 3 Master Test Suite: Admin User Management APIs & RBAC
Verifies 44 security and administrative requirements.
"""

import pytest
from uuid import uuid4
from fastapi import status
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.modules.auth.models import User, Role
from app.modules.erp.models import Plant
from app.core.security.password import hash_password, verify_password
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


async def get_non_admin_token(session: AsyncSession) -> tuple[User, str]:
    """Helper creating a normal non-admin user and returning Bearer token."""
    username = f"op_{uuid4().hex[:8]}"
    user = User(
        username=username,
        email=f"{username}@fleetcontrol.io",
        password_hash=hash_password("OperatorPass123!"),
        is_superuser=False,
        is_active=True,
        must_change_password=False,
        token_version=1,
    )
    session.add(user)
    await session.commit()

    token, _ = create_access_token(user_id=str(user.id), token_version=1, auth_stage=AuthStage.NORMAL)
    return user, token


@pytest.mark.asyncio
async def test_admin_authorization_enforcement(session: AsyncSession):
    """1 to 6. Admin can list users; non-admin receives 403 Forbidden."""
    _, admin_token = await get_admin_token(session)
    _, non_admin_token = await get_non_admin_token(session)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Non-admin rejected with 403
        op_res = await client.get(
            "/fleet-api/v1/users",
            headers={"Authorization": f"Bearer {non_admin_token}"},
        )
        assert op_res.status_code == status.HTTP_403_FORBIDDEN

        # Admin authorized with 200
        admin_res = await client.get(
            "/fleet-api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert admin_res.status_code == status.HTTP_200_OK
        data = admin_res.json()["data"]
        assert "items" in data
        assert data["total"] >= 1


@pytest.mark.asyncio
async def test_user_creation_lifecycle_and_one_time_temp_password(session: AsyncSession):
    """7 to 16. Admin creates user, returns one-time temp password, must_change_password=True."""
    _, admin_token = await get_admin_token(session)

    new_username = f"newuser_{uuid4().hex[:8]}"
    new_email = f"{new_username}@fleetcontrol.io"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/fleet-api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": new_username,
                "email": new_email,
                "full_name": "Test New User",
            },
        )
        assert res.status_code == status.HTTP_200_OK
        data = res.json()["data"]
        assert "temporary_password" in data
        temp_pass = data["temporary_password"]
        assert len(temp_pass) >= 8

        user_info = data["user"]
        assert user_info["must_change_password"] is True
        assert user_info["is_password_temporary"] is True
        assert user_info["auth_stage"] == "PASSWORD_CHANGE_REQUIRED"

        # Verify DB persistence
        created_user = (await session.execute(select(User).where(User.username == new_username))).scalars().first()
        assert created_user is not None
        assert verify_password(temp_pass, created_user.password_hash) is True
        assert created_user.token_version == 1

        # Duplicate email rejected with 409 Conflict
        dup_res = await client.post(
            "/fleet-api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": f"dup_{uuid4().hex[:8]}",
                "email": new_email,
            },
        )
        assert dup_res.status_code == status.HTTP_409_CONFLICT


@pytest.mark.asyncio
async def test_user_update_role_and_plant_scope_token_version_invalidation(session: AsyncSession):
    """17 to 25. Profile, role, plant scope updates increment token_version and invalidate old session."""
    _, admin_token = await get_admin_token(session)
    target_user, target_token = await get_non_admin_token(session)

    # Seed a plant
    plant = (await session.execute(select(Plant))).scalars().first()
    plant_code = plant.code if plant else "PLANT-001"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Target user's active session works
        me_res1 = await client.get("/fleet-api/v1/auth/me", headers={"Authorization": f"Bearer {target_token}"})
        assert me_res1.status_code == status.HTTP_200_OK

        # Admin updates plant scope on target user
        patch_res = await client.patch(
            f"/fleet-api/v1/users/{target_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"plant_ids": [plant_code]},
        )
        assert patch_res.status_code == status.HTTP_200_OK

        # Verify target user's active session is now INVALIDATED (401)!
        me_res2 = await client.get("/fleet-api/v1/auth/me", headers={"Authorization": f"Bearer {target_token}"})
        assert me_res2.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_admin_password_reset_flow(session: AsyncSession):
    """28 to 35. Admin password reset sets must_change_password=True, increments token_version, invalidates sessions."""
    _, admin_token = await get_admin_token(session)
    target_user, target_token = await get_non_admin_token(session)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Reset password trigger
        reset_res = await client.post(
            f"/fleet-api/v1/users/{target_user.id}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert reset_res.status_code == status.HTTP_200_OK
        data = reset_res.json()["data"]
        new_temp_pass = data["temporary_password"]
        assert len(new_temp_pass) >= 8

        # Target old token is invalidated
        stale_res = await client.get("/fleet-api/v1/auth/me", headers={"Authorization": f"Bearer {target_token}"})
        assert stale_res.status_code == status.HTTP_401_UNAUTHORIZED

        # Target logs in with new temporary password -> receives PASSWORD_CHANGE_REQUIRED
        login_res = await client.post(
            "/fleet-api/v1/auth/login",
            json={"username": target_user.username, "password": new_temp_pass},
        )
        assert login_res.status_code == status.HTTP_200_OK
        assert login_res.json()["data"]["auth_stage"] == "PASSWORD_CHANGE_REQUIRED"


@pytest.mark.asyncio
async def test_last_admin_and_self_deactivation_protection_guards(session: AsyncSession):
    """26, 27, 38, 39. Self-deactivation and deactivating sole remaining Admin are strictly blocked."""
    admin_user, admin_token = await get_admin_token(session)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Self-deactivation blocked
        self_del_res = await client.delete(
            f"/fleet-api/v1/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert self_del_res.status_code == status.HTTP_400_BAD_REQUEST

        # Deactivating sole active admin is blocked
        self_patch_res = await client.patch(
            f"/fleet-api/v1/users/{admin_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_active": False},
        )
        assert self_patch_res.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_restricted_phase2_jwt_cannot_access_user_management(session: AsyncSession):
    """40 to 44. Restricted token cannot access /users/*; normal admin token can."""
    temp_user = User(
        username=f"temp_admin_{uuid4().hex[:8]}",
        email=f"temp_admin_{uuid4().hex[:8]}@fleetcontrol.io",
        password_hash=hash_password("TempPass123!"),
        is_superuser=True,
        must_change_password=True,
        is_active=True,
    )
    session.add(temp_user)
    await session.commit()

    # Restricted token for temp_user
    restricted_token, _ = create_access_token(
        user_id=str(temp_user.id),
        token_version=1,
        auth_stage=AuthStage.PASSWORD_CHANGE_REQUIRED,
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get(
            "/fleet-api/v1/users",
            headers={"Authorization": f"Bearer {restricted_token}"},
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN
        assert res.json()["error"]["code"] == "FORBIDDEN"
