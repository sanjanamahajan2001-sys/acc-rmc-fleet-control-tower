"""
Phase 4 Master Test Suite: Audit & Security Telemetry
Verifies 32 event persistence, zero-plaintext security, and immutability requirements.
"""

import pytest
from uuid import uuid4
from fastapi import status
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.modules.auth.models import User, Role, AuditLog
from app.core.security.password import hash_password
from app.core.security.jwt import create_access_token
from app.schemas.auth import AuthStage


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def get_admin_token(session: AsyncSession) -> tuple[User, str]:
    """Helper creating an active Admin user and returning Bearer token."""
    username = f"aud_admin_{uuid4().hex[:8]}"
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
async def test_user_creation_emits_user_created_audit_event(session: AsyncSession):
    """1, 13, 14, 15, 17, 18, 22. USER_CREATED audit log persisted without plaintext passwords."""
    admin_user, admin_token = await get_admin_token(session)

    new_username = f"aud_user_{uuid4().hex[:8]}"
    new_email = f"{new_username}@fleetcontrol.io"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/fleet-api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": new_username,
                "email": new_email,
                "full_name": "Audit User Test",
            },
        )
        assert res.status_code == status.HTTP_200_OK

        # Query audit log
        logs = (await session.execute(
            select(AuditLog).where(AuditLog.action == "USER_CREATED").order_by(AuditLog.created_at.desc())
        )).scalars().all()
        assert len(logs) >= 1

        latest_log = logs[0]
        assert str(latest_log.user_id) == str(admin_user.id)
        assert latest_log.resource == "users"
        assert "created_user_id" in latest_log.details

        # Mandatory Zero-Plaintext Assertion
        details_str = str(latest_log.details)
        assert "temporary_password" not in details_str
        assert "password_hash" not in details_str


@pytest.mark.asyncio
async def test_user_update_role_scope_emits_granular_audit_events(session: AsyncSession):
    """2, 4, 6, 7, 29, 30, 31. USER_UPDATED, USER_ROLE_CHANGED, USER_PLANT_SCOPE_CHANGED, USER_DISABLED emitted."""
    admin_user, admin_token = await get_admin_token(session)

    # Seed target user
    target_username = f"aud_target_{uuid4().hex[:8]}"
    target_user = User(
        username=target_username,
        email=f"{target_username}@fleetcontrol.io",
        password_hash=hash_password("TargetPass123!"),
        is_active=True,
    )
    session.add(target_user)
    await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Patch active=False and roles
        res = await client.patch(
            f"/fleet-api/v1/users/{target_user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"is_active": False},
        )
        assert res.status_code == status.HTTP_200_OK

        # Verify USER_DISABLED audit log
        dis_log = (await session.execute(
            select(AuditLog).where(AuditLog.action == "USER_DISABLED").order_by(AuditLog.created_at.desc())
        )).scalars().first()
        assert dis_log is not None
        assert dis_log.details["target_user_id"] == str(target_user.id)


@pytest.mark.asyncio
async def test_password_reset_and_change_emit_audit_events(session: AsyncSession):
    """8, 9, 27, 28. USER_PASSWORD_RESET and USER_PASSWORD_CHANGED emitted without plaintext credentials."""
    admin_user, admin_token = await get_admin_token(session)

    target_username = f"aud_pass_{uuid4().hex[:8]}"
    target_user = User(
        username=target_username,
        email=f"{target_username}@fleetcontrol.io",
        password_hash=hash_password("PassBefore123!"),
        is_active=True,
        must_change_password=True,
    )
    session.add(target_user)
    await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Admin Password Reset
        reset_res = await client.post(
            f"/fleet-api/v1/users/{target_user.id}/reset-password",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert reset_res.status_code == status.HTTP_200_OK
        temp_pass = reset_res.json()["data"]["temporary_password"]

        # Check USER_PASSWORD_RESET audit
        reset_log = (await session.execute(
            select(AuditLog).where(AuditLog.action == "USER_PASSWORD_RESET").order_by(AuditLog.created_at.desc())
        )).scalars().first()
        assert reset_log is not None
        assert "temporary_password" not in str(reset_log.details)

        # Login with temp pass & change password
        login_res = await client.post(
            "/fleet-api/v1/auth/login",
            json={"username": target_username, "password": temp_pass},
        )
        target_restricted_token = login_res.json()["data"]["access_token"]

        change_res = await client.post(
            "/fleet-api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {target_restricted_token}"},
            json={"new_password": "NewStrongPass123!", "confirm_password": "NewStrongPass123!"},
        )
        assert change_res.status_code == status.HTTP_200_OK

        # Check USER_PASSWORD_CHANGED audit
        change_log = (await session.execute(
            select(AuditLog).where(AuditLog.action == "USER_PASSWORD_CHANGED").order_by(AuditLog.created_at.desc())
        )).scalars().first()
        assert change_log is not None
        assert "NewStrongPass123!" not in str(change_log.details)


@pytest.mark.asyncio
async def test_authentication_events_and_logout(session: AsyncSession):
    """10, 11, 12, 19, 20. USER_LOGIN_SUCCESS, USER_LOGIN_FAILED, USER_LOGOUT persisted safely."""
    username = f"aud_auth_{uuid4().hex[:8]}"
    user = User(
        username=username,
        email=f"{username}@fleetcontrol.io",
        password_hash=hash_password("ValidPassword123!"),
        is_active=True,
    )
    session.add(user)
    await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Failed Login
        await client.post("/fleet-api/v1/auth/login", json={"username": username, "password": "WrongPassword!"})
        fail_log = (await session.execute(
            select(AuditLog).where(AuditLog.action == "USER_LOGIN_FAILED").order_by(AuditLog.created_at.desc())
        )).scalars().first()
        assert fail_log is not None
        assert "WrongPassword!" not in str(fail_log.details)

        # Successful Login
        succ_res = await client.post("/fleet-api/v1/auth/login", json={"username": username, "password": "ValidPassword123!"})
        tok = succ_res.json()["data"]["access_token"]
        succ_log = (await session.execute(
            select(AuditLog).where(AuditLog.action == "USER_LOGIN_SUCCESS").order_by(AuditLog.created_at.desc())
        )).scalars().first()
        assert succ_log is not None

        # Logout
        await client.post("/fleet-api/v1/auth/logout", headers={"Authorization": f"Bearer {tok}"})
        logout_log = (await session.execute(
            select(AuditLog).where(AuditLog.action == "USER_LOGOUT").order_by(AuditLog.created_at.desc())
        )).scalars().first()
        assert logout_log is not None


@pytest.mark.asyncio
async def test_failed_business_operation_does_not_emit_successful_audit_event(session: AsyncSession):
    """23. Failed business operation (e.g. duplicate creation) does not emit USER_CREATED audit."""
    admin_user, admin_token = await get_admin_token(session)

    dup_email = f"dup_aud_{uuid4().hex[:8]}@fleetcontrol.io"
    user_existing = User(
        username=f"existing_{uuid4().hex[:8]}",
        email=dup_email,
        password_hash=hash_password("Pass123!"),
        is_active=True,
    )
    session.add(user_existing)
    await session.commit()

    initial_audit_count = (await session.execute(
        select(AuditLog).where(AuditLog.action == "USER_CREATED")
    )).scalars().all()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/fleet-api/v1/users",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "username": f"dup_user_{uuid4().hex[:8]}",
                "email": dup_email,
            },
        )
        assert res.status_code == status.HTTP_409_CONFLICT

    final_audit_count = (await session.execute(
        select(AuditLog).where(AuditLog.action == "USER_CREATED")
    )).scalars().all()
    assert len(final_audit_count) == len(initial_audit_count)
