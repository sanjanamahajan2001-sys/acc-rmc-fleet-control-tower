import pytest
import time
import asyncio
from sqlalchemy import text
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import AsyncSessionFactory, engine
from app.dependencies.auth import get_current_user_claims
from app.schemas.auth import TokenPayload

def get_admin_id():
    async def _lookup():
        async with AsyncSessionFactory() as session:
            res = await session.execute(text("SELECT id FROM users WHERE username = 'admin'"))
            row = res.first()
            admin_id = str(row[0]) if row else None
        await engine.dispose()
        return admin_id
    return asyncio.run(_lookup())

def test_revert_unauthorized():
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        res = client.post("/demo-api/v1/erp/admin/revert-dataset", json={"period_key": "NON_EXISTENT"})
        assert res.status_code == 401

def test_revert_non_existent_dataset():
    admin_id = get_admin_id()
    assert admin_id is not None, "Admin user must exist in the database"
    now = int(time.time())
    app.dependency_overrides[get_current_user_claims] = lambda: TokenPayload(
        sub=admin_id,
        username="admin",
        email="admin@fleet.local",
        is_superuser=True,
        token_version=1,
        type="access",
        iat=now,
        exp=now + 3600,
        jti="test-jti"
    )
    try:
        with TestClient(app) as client:
            res = client.post(
                "/demo-api/v1/erp/admin/revert-dataset",
                json={"period_key": "NON_EXISTENT_PERIOD_9999"}
            )
            assert res.status_code == 404
            data = res.json()
            error_msg = str(data)
            assert "No import jobs found matching target dataset" in error_msg
    finally:
        app.dependency_overrides.clear()

def test_filter_metadata_endpoint():
    with TestClient(app) as client:
        res = client.get("/demo-api/v1/site-dashboard/filters")
        assert res.status_code == 200
        data = res.json().get("data", {})
        assert "dataset_info" in data
        info = data["dataset_info"]
        assert info["dataset_id"].startswith("DS-")
        assert info["operational_date"] is not None
        assert info["total_dispatches"] > 0
