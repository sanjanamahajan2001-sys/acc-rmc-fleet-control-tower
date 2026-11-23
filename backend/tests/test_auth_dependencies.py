"""
Unit tests for FastAPI Security Dependencies & Route Protection
"""

import uuid

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.handlers import register_exception_handlers
from app.core.middleware import CorrelationIDMiddleware
from app.core.security.jwt import create_access_token
from app.core.security.revocation import revocation_store
from app.dependencies.auth import require_authenticated_user
from app.schemas.auth import TokenPayload

app = FastAPI()
app.add_middleware(CorrelationIDMiddleware)
register_exception_handlers(app)


@app.get("/protected")
def protected_route(
    claims: TokenPayload = Depends(require_authenticated_user),  # noqa: B008
):
    return {"user_id": claims.sub, "tenant_id": claims.tenant_id}


client = TestClient(app)


def test_protected_route_missing_auth_header():
    response = client.get("/protected")
    assert response.status_code == 401
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_protected_route_valid_token():
    user_id = str(uuid.uuid4())
    token, _ = create_access_token(user_id=user_id, tenant_id="TENANT-123")
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == user_id
    assert data["tenant_id"] == "TENANT-123"


@pytest.mark.asyncio
async def test_protected_route_revoked_token():
    user_id = str(uuid.uuid4())
    token, jti = create_access_token(user_id=user_id)
    await revocation_store.revoke_jti(jti, 3600)

    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "TOKEN_REVOKED"
