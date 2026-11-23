"""
Automated Test Suite for WS1.6 ERP REST APIs & Import Management
Tests upload, job management, SSE progress streaming, statistics, audit logs, explorer endpoints,
authentication, authorization, and APIResponse envelope compliance.
"""

import io

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security.jwt import create_access_token
from app.dependencies.common import get_db_session
from app.main import app


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, pool_pre_ping=True)
    async with engine.connect() as conn:
        trans = await conn.begin()
        async_session_factory = async_sessionmaker(
            bind=conn,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
        async with async_session_factory() as session:
            try:
                yield session
            finally:
                await session.close()
                await trans.rollback()
    await engine.dispose()


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession):
    async def _override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


import uuid
from app.modules.auth.models import User


@pytest_asyncio.fixture
async def auth_headers(db_session: AsyncSession) -> dict[str, str]:
    user_uuid = uuid.uuid4()
    test_user = User(
        id=user_uuid,
        username=f"test_erp_{uuid.uuid4().hex[:8]}",
        email=f"erp_{uuid.uuid4().hex[:8]}@example.com",
        password_hash="test_hashed_password",
        full_name="Test ERP User",
        is_active=True,
        must_change_password=False,
        token_version=1,
    )
    db_session.add(test_user)
    await db_session.flush()

    token, _ = create_access_token(
        user_id=str(user_uuid),
        tenant_id="tenant-01",
        token_version=1,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_upload_workbook_api_success(
    async_client: AsyncClient, auth_headers: dict[str, str]
):
    file_content = (
        b"Ticket No.,Dispatch Date,Plant Name\nTCK-API-01,2026-08-05,Vasco Plant\n"
    )
    files = {"file": ("test_api.csv", io.BytesIO(file_content), "text/csv")}
    response = await async_client.post(
        "/demo-api/v1/erp/workbooks/upload", files=files, headers=auth_headers
    )

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["file_name"] == "test_api.csv"
    assert body["data"]["job_number"].startswith("JOB-")
    assert "meta" in body
    assert body["meta"]["correlation_id"] is not None


@pytest.mark.asyncio
async def test_upload_workbook_api_unauthorized(async_client: AsyncClient):
    files = {"file": ("test.csv", io.BytesIO(b"data"), "text/csv")}
    response = await async_client.post("/demo-api/v1/erp/workbooks/upload", files=files)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_jobs_api(async_client: AsyncClient, auth_headers: dict[str, str]):
    response = await async_client.get("/demo-api/v1/erp/jobs", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "items" in body["data"]
    assert body["data"]["page"] == 1


@pytest.mark.asyncio
async def test_get_statistics_api(
    async_client: AsyncClient, auth_headers: dict[str, str]
):
    response = await async_client.get("/demo-api/v1/erp/statistics", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["average_throughput_rows_per_sec"] > 0


@pytest.mark.asyncio
async def test_list_audit_logs_api(
    async_client: AsyncClient, auth_headers: dict[str, str]
):
    response = await async_client.get("/demo-api/v1/erp/audit-logs", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "items" in body["data"]


@pytest.mark.asyncio
async def test_explorer_endpoints_api(
    async_client: AsyncClient, auth_headers: dict[str, str]
):
    endpoints = [
        "plants",
        "sites",
        "customers",
        "vehicles",
        "drivers",
        "orders",
        "tickets",
        "dispatches",
        "invoices",
        "trips",
    ]
    for ep in endpoints:
        response = await async_client.get(
            f"/demo-api/v1/erp/explorer/{ep}", headers=auth_headers
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "items" in body["data"]


@pytest.mark.asyncio
async def test_progress_sse_stream_api(
    async_client: AsyncClient, auth_headers: dict[str, str]
):
    # First upload to ensure job exists
    files = {
        "file": (
            "sse_test.csv",
            io.BytesIO(
                b"Ticket No.,Dispatch Date,Plant Name\nTCK-SSE-01,2026-08-05,Vasco Plant\n"
            ),
            "text/csv",
        )
    }
    up_res = await async_client.post(
        "/demo-api/v1/erp/workbooks/upload", files=files, headers=auth_headers
    )
    job_number = up_res.json()["data"]["job_number"]

    stream_res = await async_client.get(
        f"/demo-api/v1/erp/jobs/{job_number}/progress", headers=auth_headers
    )
    assert stream_res.status_code == 200
    assert "text/event-stream" in stream_res.headers["content-type"]
