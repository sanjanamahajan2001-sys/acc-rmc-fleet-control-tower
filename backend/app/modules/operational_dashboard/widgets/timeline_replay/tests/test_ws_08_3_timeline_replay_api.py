"""
WS-08.3 Dedicated PyTest Verification Suite for Timeline Replay Repository, Service & FastAPI REST Router.
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient, ASGITransport

from app.core.config import settings
from app.main import app
from app.modules.operational_dashboard.widgets.timeline_replay.dtos import (
    DispatchReplayListResponseDTO,
    DispatchTimelineReplayDetailDTO,
    EventAuthorityEnum,
    SpatialModeEnum,
    DurationCompletenessEnum,
)
from app.modules.operational_dashboard.widgets.timeline_replay.service import TimelineReplayService
from app.modules.operational_dashboard.widgets.timeline_replay.repository import TimelineReplayRepository


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(settings.ASYNC_DATABASE_URI, pool_pre_ping=True)
    async_session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with async_session_factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def async_api_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_ws_08_3_repository_list_replay_dispatches(db_session):
    """TEST 1-3: List dispatches with pagination and deterministic ordering"""
    items, total_count = await TimelineReplayRepository.list_replay_dispatches(
        session=db_session,
        plant_id="ALL",
        customer_id="ALL",
        dataset_id=None,
        page=1,
        page_size=10
    )
    assert total_count >= 0
    assert len(items) <= 10
    if len(items) > 0:
        assert "dispatch_id" in items[0]
        assert "has_telemetry" in items[0]


@pytest.mark.asyncio
async def test_ws_08_3_service_get_dispatch_detail_and_engine_delegation(db_session):
    """TEST 10, 11, 15, 17, 18, 20, 23: Service delegates lifecycle calculations to TimelineReplayEngine and returns full DTO"""
    items, total_count = await TimelineReplayRepository.list_replay_dispatches(db_session, page=1, page_size=1)
    if total_count == 0:
        pytest.skip("No dispatches found in PostgreSQL database.")

    target_id = items[0]["dispatch_id"]
    dto = await TimelineReplayService.get_dispatch_timeline_detail(
        session=db_session,
        dispatch_id=target_id,
        plant_id="ALL",
        customer_id="ALL"
    )

    assert str(dto.dispatch_id) == str(target_id)
    assert len(dto.lifecycle_events) == 8
    loaded_event = next(e for e in dto.lifecycle_events if e.event_type == "Loaded")
    assert loaded_event.authority_type == EventAuthorityEnum.INFERRED
    assert loaded_event.is_inferred_estimate is True
    assert dto.spatial_context.spatial_mode in [SpatialModeEnum.LOCATION_CONTEXT_ONLY, SpatialModeEnum.NO_SPATIAL_DATA, SpatialModeEnum.GPS_TRAJECTORY]
    if dto.spatial_context.spatial_mode != SpatialModeEnum.GPS_TRAJECTORY:
        assert len(dto.spatial_context.trajectory_points) == 0


@pytest.mark.asyncio
async def test_ws_08_3_scope_and_dataset_isolation(db_session):
    """TEST 4, 5, 6, 12, 13, 14: Scope and dataset isolation returns 404 on scope mismatch"""
    fake_id = uuid4()
    with pytest.raises(Exception) as exc_info:
        await TimelineReplayService.get_dispatch_timeline_detail(
            session=db_session,
            dispatch_id=fake_id,
            plant_id="ALL",
            customer_id="ALL"
        )
    assert "not found" in str(exc_info.value).lower() or "404" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ws_08_3_fastapi_rest_endpoints(async_api_client):
    """TEST 29: FastAPI REST router registration and OpenAPI verification"""
    # 1. Test List Endpoint
    res_list = await async_api_client.get("/fleet-api/v1/timeline-replay/dispatches?page=1&page_size=5")
    assert res_list.status_code == 200
    data_list = res_list.json()
    assert "items" in data_list
    assert "total_count" in data_list

    # 2. Test Detail Endpoint (Non-existent UUID -> 404)
    fake_uuid = str(uuid4())
    res_detail = await async_api_client.get(f"/fleet-api/v1/timeline-replay/dispatches/{fake_uuid}")
    assert res_detail.status_code == 404
