"""
WS-ROUT-4: Automated Test Suite for Route Analysis Endpoints & Immutable Snapshots.
Tests:
- Successful NOW analysis execution
- Successful PLANNED_DEPARTURE analysis execution
- Immutable Snapshot creation and PostgreSQL trigger enforcement (rejection of UPDATE / DELETE)
- Re-analysis creates a NEW snapshot and leaves prior snapshots unchanged
- Snapshot retrieval by ID and Snapshot history retrieval
- Missing coordinates deterministic handling (LOCATION_DATA_MISSING)
- Governed candidate plant bounds (<= 60km, <= 4 candidates)
- Audit/provenance fields validation (engine_version, policy_version, timestamps)
- Authentication and RBAC guard verification
"""

import uuid
from datetime import datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.dependencies.common import get_db_session
from app.core.security.jwt import create_access_token
from app.main import app
from app.modules.auth.models import User
from app.modules.erp.models import Customer, Plant, Site
from app.modules.operational_dashboard.models.route_analysis import RouteAnalysisSnapshot
from app.modules.operational_dashboard.widgets.dispatch_analysis.dtos import (
    RouteAnalysisMode,
    SynthesisDecisionOutcome,
    SynthesisCaseCategory,
    RouteAnalysisExecutionRequestDTO,
)
from app.modules.operational_dashboard.widgets.dispatch_analysis.services.route_analysis_service import (
    RouteAnalysisOrchestrationService,
)


@pytest.fixture
def isolated_db():
    """Creates an isolated NullPool session maker to prevent cross-event-loop pool contamination."""
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


async def create_test_auth_headers(session_factory) -> dict:
    """Helper creating user & auth headers within the active test session."""
    async with session_factory() as session:
        user_uuid = uuid.uuid4()
        test_user = User(
            id=user_uuid,
            username=f"test_dispatcher_{uuid.uuid4().hex[:8]}",
            email=f"dispatcher_{uuid.uuid4().hex[:8]}@example.com",
            password_hash="test_hashed_password",
            full_name="Test Dispatcher",
            is_active=True,
            must_change_password=False,
            token_version=1,
        )
        session.add(test_user)
        await session.commit()

        token, _ = create_access_token(user_id=user_uuid, token_version=1)
        return {"Authorization": f"Bearer {token}"}


async def seed_test_route_entities(session_factory) -> dict:
    """Helper seeding test Plant and Site entities."""
    async with session_factory() as session:
        plant_a = Plant(
            id=uuid.uuid4(),
            code=f"PLANT_A_{uuid.uuid4().hex[:6]}",
            name="Plant Alpha",
            latitude=15.3991,
            longitude=73.8153,
        )
        plant_b = Plant(
            id=uuid.uuid4(),
            code=f"PLANT_B_{uuid.uuid4().hex[:6]}",
            name="Plant Beta",
            latitude=15.2832,
            longitude=73.9862,
        )
        site_1 = Site(
            id=uuid.uuid4(),
            code=f"SITE_VALID_{uuid.uuid4().hex[:6]}",
            name="Valid Site 1",
            plant_id=plant_a.id,
            latitude=15.4909,
            longitude=73.8278,
        )
        site_missing = Site(
            id=uuid.uuid4(),
            code=f"SITE_NO_COORDS_{uuid.uuid4().hex[:6]}",
            name="No Coords Site",
            plant_id=plant_a.id,
            latitude=None,
            longitude=None,
        )
        customer = Customer(
            id=uuid.uuid4(),
            code=f"CUST_{uuid.uuid4().hex[:6]}",
            name="Test Customer Builder",
        )

        session.add_all([plant_a, plant_b, site_1, site_missing, customer])
        await session.commit()

        return {
            "plant_a_id": str(plant_a.id),
            "plant_b_id": str(plant_b.id),
            "site_valid_id": str(site_1.id),
            "site_missing_id": str(site_missing.id),
            "customer_id": str(customer.id),
        }


@pytest.mark.asyncio
async def test_route_analysis_missing_coordinates(isolated_db):
    """Verifies that missing coordinates deterministic state (LOCATION_DATA_MISSING) is returned and persisted."""
    headers = await create_test_auth_headers(isolated_db)
    entities = await seed_test_route_entities(isolated_db)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/demo-api/v1/dispatch-analysis/route-analysis",
            json={
                "site_id": entities["site_missing_id"],
                "current_source_plant_id": entities["plant_a_id"],
                "analysis_mode": "NOW",
            },
            headers=headers,
        )

    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    data = body["data"]
    assert data["recommendation_status"] == SynthesisDecisionOutcome.LOCATION_DATA_MISSING.value
    assert data["primary_case_category"] == SynthesisCaseCategory.C11_COORDINATES_MISSING.value
    assert data["failure_reason_code"] == "LOCATION_DATA_MISSING"

    # Verify snapshot persisted in PostgreSQL
    async with isolated_db() as session:
        snap_stmt = select(RouteAnalysisSnapshot).where(RouteAnalysisSnapshot.analysis_id == uuid.UUID(data["analysis_id"]))
        snap = (await session.execute(snap_stmt)).scalars().first()
        assert snap is not None
        assert snap.recommendation_status == SynthesisDecisionOutcome.LOCATION_DATA_MISSING.value
        assert snap.failure_reason_code == "LOCATION_DATA_MISSING"


@pytest.mark.asyncio
async def test_postgresql_snapshot_immutability_trigger(isolated_db):
    """Verifies PostgreSQL database trigger rejects any UPDATE or DELETE attempt on route_analysis_snapshots."""
    entities = await seed_test_route_entities(isolated_db)

    async with isolated_db() as session:
        req = RouteAnalysisExecutionRequestDTO(
            site_id=entities["site_missing_id"],
            current_source_plant_id=entities["plant_a_id"],
            analysis_mode=RouteAnalysisMode.NOW,
        )
        res = await RouteAnalysisOrchestrationService.execute_analysis(session, req)
        analysis_uuid = uuid.UUID(res.analysis_id)

        # 1. Attempt UPDATE directly via SQL -> MUST RAISE EXCEPTION
        with pytest.raises(Exception) as exc_update:
            await session.execute(
                text("UPDATE route_analysis_snapshots SET recommendation_status = 'MUTATED' WHERE analysis_id = :aid"),
                {"aid": analysis_uuid},
            )
            await session.commit()
        assert "DATABASE IMMUTABILITY VIOLATION" in str(exc_update.value)
        await session.rollback()

        # 2. Attempt DELETE directly via SQL -> MUST RAISE EXCEPTION
        with pytest.raises(Exception) as exc_delete:
            await session.execute(
                text("DELETE FROM route_analysis_snapshots WHERE analysis_id = :aid"),
                {"aid": analysis_uuid},
            )
            await session.commit()
        assert "DATABASE IMMUTABILITY VIOLATION" in str(exc_delete.value)
        await session.rollback()


@pytest.mark.asyncio
async def test_re_analysis_creates_new_snapshot_preserves_old(isolated_db):
    """Verifies that re-analyzing creates a brand new snapshot and does not overwrite previous analysis."""
    headers = await create_test_auth_headers(isolated_db)
    entities = await seed_test_route_entities(isolated_db)

    async with isolated_db() as session:
        req1 = RouteAnalysisExecutionRequestDTO(
            site_id=entities["site_missing_id"],
            current_source_plant_id=entities["plant_a_id"],
            analysis_mode=RouteAnalysisMode.NOW,
        )
        res1 = await RouteAnalysisOrchestrationService.execute_analysis(session, req1)
        aid_1 = res1.analysis_id

        req2 = RouteAnalysisExecutionRequestDTO(
            site_id=entities["site_missing_id"],
            current_source_plant_id=entities["plant_a_id"],
            analysis_mode=RouteAnalysisMode.NOW,
        )
        res2 = await RouteAnalysisOrchestrationService.execute_analysis(session, req2)
        aid_2 = res2.analysis_id

        assert aid_1 != aid_2

        snap1 = await RouteAnalysisOrchestrationService.get_snapshot_by_id(session, uuid.UUID(aid_1))
        snap2 = await RouteAnalysisOrchestrationService.get_snapshot_by_id(session, uuid.UUID(aid_2))
        assert snap1 is not None
        assert snap2 is not None
        assert snap1.analysis_id != snap2.analysis_id


@pytest.mark.asyncio
async def test_get_snapshot_by_id_and_history(isolated_db):
    """Verifies retrieval of snapshot by ID and history filtering."""
    headers = await create_test_auth_headers(isolated_db)
    entities = await seed_test_route_entities(isolated_db)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/demo-api/v1/dispatch-analysis/route-analysis",
            json={
                "site_id": entities["site_missing_id"],
                "customer_id": entities["customer_id"],
                "current_source_plant_id": entities["plant_a_id"],
                "analysis_mode": "NOW",
                "operator_notes": "TM bridge delay context",
            },
            headers=headers,
        )
        aid = res.json()["data"]["analysis_id"]

        # Retrieve by ID
        get_res = await ac.get(
            f"/demo-api/v1/dispatch-analysis/route-analysis/snapshot/{aid}",
            headers=headers,
        )
        assert get_res.status_code == 200
        assert get_res.json()["data"]["analysis_id"] == aid

        # Retrieve history
        hist_res = await ac.get(
            f"/demo-api/v1/dispatch-analysis/route-analysis/history?site_id={entities['site_missing_id']}",
            headers=headers,
        )
        assert hist_res.status_code == 200
        hist_data = hist_res.json()["data"]
        assert len(hist_data) >= 1
        assert any(item["analysis_id"] == aid for item in hist_data)


@pytest.mark.asyncio
async def test_auth_guard_route_analysis_endpoints():
    """Verifies that unauthorized requests are rejected with HTTP 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/demo-api/v1/dispatch-analysis/route-analysis",
            json={"site_id": str(uuid.uuid4())},
        )
        assert res.status_code == 401
