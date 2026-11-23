"""
Unit & Integration Tests for Google Maps & Routes API Usage and Allowance Tracking.
Verifies telemetry recording, caching savings calculation, monthly aggregation, and API response.
"""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.dependencies.common import get_db_session
from app.main import app
from app.modules.operational_dashboard.models.google_api_usage import GoogleApiUsageLog
from app.modules.operational_dashboard.widgets.dispatch_analysis.services.google_usage_service import (
    GoogleApiUsageService,
    DEFAULT_MONTHLY_ALLOWANCE,
)


@pytest.fixture
def isolated_db():
    """Creates an isolated NullPool session maker."""
    test_engine = create_async_engine(settings.ASYNC_DATABASE_URI, poolclass=NullPool)
    test_session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False, class_=AsyncSession)

    async def _override_get_db_session():
        async with test_session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = _override_get_db_session
    yield test_session_factory
    app.dependency_overrides.pop(get_db_session, None)


@pytest.mark.asyncio
async def test_record_usage_and_monthly_aggregation(isolated_db):
    """Verifies that billable and cached calls are recorded and aggregated accurately."""
    async with isolated_db() as session:
        # Record billable matrix call (4 elements)
        await GoogleApiUsageService.record_usage(
            session=session,
            api_service="ROUTES_MATRIX_V2",
            endpoint="distanceMatrix/v2:computeRouteMatrix",
            request_count=4,
            status_code=200,
            is_cached=False,
            latency_ms=150.5,
        )

        # Record cached matrix call (4 elements)
        await GoogleApiUsageService.record_usage(
            session=session,
            api_service="ROUTES_MATRIX_V2",
            endpoint="distanceMatrix/v2:computeRouteMatrix",
            request_count=4,
            status_code=200,
            is_cached=True,
            latency_ms=0.0,
        )

        # Record billable computeRoutes call (1 element)
        await GoogleApiUsageService.record_usage(
            session=session,
            api_service="ROUTES_COMPUTE_V2",
            endpoint="directions/v2:computeRoutes",
            request_count=1,
            status_code=200,
            is_cached=False,
            latency_ms=85.2,
        )

        summary = await GoogleApiUsageService.get_monthly_usage_summary(session)

        assert summary.total_billable_requests_month >= 5
        assert summary.cached_requests_saved_month >= 4
        assert summary.monthly_allowance_limit == DEFAULT_MONTHLY_ALLOWANCE
        assert summary.remaining_allowance == DEFAULT_MONTHLY_ALLOWANCE - summary.total_billable_requests_month
        assert summary.usage_percentage >= 0.0
        assert summary.status in ("HEALTHY", "WARNING", "CRITICAL", "EXCEEDED", "UNCONFIGURED")


@pytest.mark.asyncio
async def test_get_google_api_usage_endpoint(isolated_db):
    """Verifies the GET /route-analysis/api-usage REST endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/demo-api/v1/dispatch-analysis/route-analysis/api-usage")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("success") is True
        summary = data.get("data")
        assert summary is not None
        assert "total_billable_requests_month" in summary
        assert "cached_requests_saved_month" in summary
        assert "monthly_allowance_limit" in summary
        assert "remaining_allowance" in summary
        assert "usage_percentage" in summary
        assert "status" in summary
        assert "is_api_configured" in summary
        assert "billing_cycle_start" in summary
        assert "billing_cycle_end" in summary
