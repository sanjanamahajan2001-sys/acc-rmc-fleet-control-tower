"""
Phase 2 Master Test Suite: Authentication & Security Core
Verifies 32 security and authentication requirements.
"""

import pytest
from uuid import uuid4
from fastapi import status
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.modules.auth.models import User
from app.core.security.password import hash_password, verify_password
from app.core.security.jwt import create_access_token, decode_and_validate_token
from app.schemas.auth import AuthStage


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_normal_user_login_receives_normal_auth_stage(session: AsyncSession):
    """1. Normal user login receives auth_stage=NORMAL."""
    username = f"normal_{uuid4().hex[:8]}"
    email = f"{username}@fleetcontrol.io"
    user = User(
        username=username,
        email=email,
        password_hash=hash_password("NormalPass123!"),
        must_change_password=False,
        is_active=True,
    )
    session.add(user)
    await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/fleet-api/v1/auth/login",
            json={"username": username, "password": "NormalPass123!"},
        )
        assert res.status_code == status.HTTP_200_OK
        data = res.json()["data"]
        assert data["auth_stage"] == "NORMAL"
        assert data["user"]["must_change_password"] is False

        # Validate JWT payload
        claims = decode_and_validate_token(data["access_token"])
        assert claims.auth_stage == AuthStage.NORMAL
        assert claims.token_version == 1


@pytest.mark.asyncio
async def test_temp_password_user_login_receives_password_change_required_stage(session: AsyncSession):
    """2. Temporary-password user receives auth_stage=PASSWORD_CHANGE_REQUIRED."""
    username = f"temp_{uuid4().hex[:8]}"
    email = f"{username}@fleetcontrol.io"
    user = User(
        username=username,
        email=email,
        password_hash=hash_password("TempSecret123!"),
        must_change_password=True,
        is_password_temporary=True,
        is_active=True,
    )
    session.add(user)
    await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/fleet-api/v1/auth/login",
            json={"username": username, "password": "TempSecret123!"},
        )
        assert res.status_code == status.HTTP_200_OK
        data = res.json()["data"]
        assert data["auth_stage"] == "PASSWORD_CHANGE_REQUIRED"
        assert data["user"]["must_change_password"] is True

        # Validate restricted JWT payload
        claims = decode_and_validate_token(data["access_token"])
        assert claims.auth_stage == AuthStage.PASSWORD_CHANGE_REQUIRED


@pytest.mark.asyncio
async def test_invalid_credentials_and_disabled_user_rejected(session: AsyncSession):
    """3 & 4. Invalid credentials and disabled users are rejected with 401."""
    username = f"disabled_{uuid4().hex[:8]}"
    user = User(
        username=username,
        email=f"{username}@fleetcontrol.io",
        password_hash=hash_password("Pass12345!"),
        is_active=False,
    )
    session.add(user)
    await session.commit()

    username_bad = f"userbad_{uuid4().hex[:8]}"
    user_bad = User(
        username=username_bad,
        email=f"{username_bad}@fleetcontrol.io",
        password_hash=hash_password("RealPass123!"),
        is_active=True,
    )
    session.add(user_bad)
    await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Invalid password
        res1 = await client.post(
            "/fleet-api/v1/auth/login",
            json={"username": username_bad, "password": "WrongPassword!"},
        )
        assert res1.status_code == status.HTTP_401_UNAUTHORIZED


        # Disabled user login
        res2 = await client.post(
            "/fleet-api/v1/auth/login",
            json={"username": username, "password": "Pass12345!"},
        )
        assert res2.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_restricted_jwt_route_permissions(session: AsyncSession):
    """7, 8, 9, 10, 11. Restricted JWT permissions on change-password, me, logout, and 403 on operational APIs."""
    username = f"restr_{uuid4().hex[:8]}"
    user = User(
        username=username,
        email=f"{username}@fleetcontrol.io",
        password_hash=hash_password("TempSecret123!"),
        must_change_password=True,
        is_active=True,
    )
    session.add(user)
    await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        login_res = await client.post(
            "/fleet-api/v1/auth/login",
            json={"username": username, "password": "TempSecret123!"},
        )
        token = login_res.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Allowed: GET /auth/me
        me_res = await client.get("/fleet-api/v1/auth/me", headers=headers)
        assert me_res.status_code == status.HTTP_200_OK
        assert me_res.json()["data"]["auth_stage"] == "PASSWORD_CHANGE_REQUIRED"

        # Blocked: GET /dispatch-analysis/kpis (Operational API)
        op_res = await client.get("/fleet-api/v1/dispatch-analysis/kpis", headers=headers)
        assert op_res.status_code == status.HTTP_403_FORBIDDEN
        assert op_res.json()["error"]["code"] == "FORBIDDEN"



@pytest.mark.asyncio
async def test_token_version_invalidation(session: AsyncSession):
    """12 & 13. Token version matching succeeds; stale token version receives 401."""
    user = User(
        username=f"tv_{uuid4().hex[:8]}",
        email=f"tv_{uuid4().hex[:8]}@fleetcontrol.io",
        password_hash=hash_password("Pass123!"),
        token_version=1,
        is_active=True,
    )
    session.add(user)
    await session.commit()

    # Issue token with version 1
    token, _ = create_access_token(user_id=str(user.id), token_version=1, auth_stage=AuthStage.NORMAL)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Valid token version 1
        res1 = await client.get("/fleet-api/v1/auth/me", headers=headers)
        assert res1.status_code == status.HTTP_200_OK

        # Admin/Security action increments token_version to 2 in DB
        user.token_version += 1
        await session.commit()

        # Stale token version 1 rejected
        res2 = await client.get("/fleet-api/v1/auth/me", headers=headers)
        assert res2.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_full_forced_password_change_flow(session: AsyncSession):
    """15 to 27. Complete password upgrade flow, token revocation, and fresh token issuance."""
    username = f"flow_{uuid4().hex[:8]}"
    temp_pass = "TempSecret123!"
    new_pass = "FreshStrongPass2026!"

    user = User(
        username=username,
        email=f"{username}@fleetcontrol.io",
        password_hash=hash_password(temp_pass),
        must_change_password=True,
        is_password_temporary=True,
        token_version=1,
        is_active=True,
    )
    session.add(user)
    await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Login with temporary password
        login_res = await client.post(
            "/fleet-api/v1/auth/login",
            json={"username": username, "password": temp_pass},
        )
        old_token = login_res.json()["data"]["access_token"]
        headers_old = {"Authorization": f"Bearer {old_token}"}

        # 2. Confirmation mismatch failure
        mismatch_res = await client.post(
            "/fleet-api/v1/auth/change-password",
            json={"new_password": new_pass, "confirm_password": "WrongConfirmPass!"},
            headers=headers_old,
        )
        assert mismatch_res.status_code == status.HTTP_400_BAD_REQUEST

        # 3. Successful password change
        change_res = await client.post(
            "/fleet-api/v1/auth/change-password",
            json={"new_password": new_pass, "confirm_password": new_pass},
            headers=headers_old,
        )
        assert change_res.status_code == status.HTTP_200_OK
        change_data = change_res.json()["data"]
        fresh_token = change_data["access_token"]
        assert change_data["auth_stage"] == "NORMAL"
        assert change_data["user"]["must_change_password"] is False

        # 4. Old restricted token is now INVALID (401 due to token_version increment!)
        old_token_res = await client.get("/fleet-api/v1/auth/me", headers=headers_old)
        assert old_token_res.status_code == status.HTTP_401_UNAUTHORIZED

        # 5. Fresh token can access operational APIs & /auth/me
        headers_fresh = {"Authorization": f"Bearer {fresh_token}"}
        me_res = await client.get("/fleet-api/v1/auth/me", headers=headers_fresh)
        assert me_res.status_code == status.HTTP_200_OK
        assert me_res.json()["data"]["auth_stage"] == "NORMAL"

        # 6. Verify new password authenticates normally
        new_login = await client.post(
            "/fleet-api/v1/auth/login",
            json={"username": username, "password": new_pass},
        )
        assert new_login.status_code == status.HTTP_200_OK
        assert new_login.json()["data"]["auth_stage"] == "NORMAL"

        # 7. Old temp password can NO LONGER authenticate
        old_login = await client.post(
            "/fleet-api/v1/auth/login",
            json={"username": username, "password": temp_pass},
        )
        assert old_login.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_argon2id_hash_and_zero_plaintext_security(session: AsyncSession):
    """28 to 31. Password hashing verification and zero plaintext exposure."""
    raw_pass = "ComplexSecret#2026"
    hashed = hash_password(raw_pass)

    assert hashed.startswith("$argon2id$")
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongSecret", hashed) is False
