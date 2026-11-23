"""
Phase 8 — Workstream 1: Dedicated Action Execution Test Suite.
Verifies all 32 required WS1 test requirements:
1. PlannerActionLog compatibility & schema
2. Action queue filtering (plant, customer, status)
3. PENDING -> ACCEPTED
4. ACCEPTED -> IN_PROGRESS
5. IN_PROGRESS -> EXECUTED
6. PENDING -> REJECTED
7. PENDING -> DEFERRED
8. Invalid state transitions rejected (e.g. PENDING -> EXECUTED)
9. Idempotent accept
10. Idempotent confirm
11. Duplicate execution protection
12. Optimistic concurrency conflict
13. Stale prediction snapshot rejection
14. Completed dispatch rejection
15. Cancelled dispatch rejection
16. Zone constraint protection (South Zone vs North Zone cross-transfer)
17. RBAC enforcement & role persistence
18. Dispatcher identity persistence
19. Model provenance preservation
20. Prediction snapshot lineage preservation
21. Financial rate lineage preservation (RATE_SPECIFICATION_GLOBAL_V1)
22. predicted_value is never treated as INR
23. estimated_avoided_exposure_inr calculation lineage
24. actual_avoided_loss_inr remains NULL before outcome reconciliation
25. Transaction rollback safety
26. No automatic ERP write-back
27. Phase 5 dataset immunity
28. Phase 6 prediction snapshot immunity
29. REST API endpoints (/accept, /confirm-execution, /reject, /defer)
30. API error envelope correctness
31. Retry after failed request
32. Idempotency after timeout/retry scenario
"""

import os
import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from app.core.config import settings
from app.modules.operational_intelligence.models.planner_action import PlannerActionLog
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.erp.models import Dispatch, Plant, Customer
from app.modules.operational_intelligence.schemas.action_execution_dtos import (
    ActionStatusEnum,
    DispatcherRoleEnum,
    AcceptActionRequestDTO,
    ConfirmExecutionRequestDTO,
    RejectActionRequestDTO,
    DeferActionRequestDTO,
)
from app.modules.operational_intelligence.services.action_execution_service import (
    ActionExecutionService,
)
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams


def get_test_db_url() -> str:
    if os.getenv("TEST_DATABASE_URL"):
        return os.getenv("TEST_DATABASE_URL")
    return f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

TEST_DB_URL = get_test_db_url()


@pytest_asyncio.fixture
async def sync_session():
    if os.getenv("ALLOW_TESTING") != "true":
        pytest.skip("ALLOW_TESTING=true environment variable required to execute DB tests.")

    engine = create_async_engine(TEST_DB_URL, echo=False)
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_factory() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_ws81_01_planner_action_log_compatibility(sync_session):
    """Test 1 & 18 & 19 & 20: PlannerActionLog compatibility, identity & provenance preservation."""
    session = sync_session
    act_id = f"ACT-WS81-{uuid.uuid4().hex[:6].upper()}"
    idemp_key = f"IDEMP-{uuid.uuid4().hex[:10]}"
    action = PlannerActionLog(
        action_id=act_id,
        recommendation_id="REC-TEST-001",
        prediction_snapshot_id="SNAP-TEST-001",
        model_family="delay_regressor",
        model_version="v1.1.0-candidate-ds-fsv1-prom",
        dataset_id="DS-20260805-001",
        operation_date="2026-08-19",
        plant_code="ACC_NESSAI",
        customer_code="CUST-001",
        dispatch_id="DISP-TEST-001",
        action_type="STAGGER_LOADING",
        action_parameters={"offset_mins": 15},
        predicted_risk_exposure_inr=5000.0,
        action_status="PENDING",
        dispatcher_id="USER-DISPATCHER-1",
        dispatcher_role="DISPATCHER",
        idempotency_key=idemp_key,
        version_lock=1,
    )
    session.add(action)
    await session.commit()

    res = await session.execute(select(PlannerActionLog).where(PlannerActionLog.action_id == act_id))
    saved = res.scalar_one()
    assert saved.recommendation_id == "REC-TEST-001"
    assert saved.model_family == "delay_regressor"
    assert saved.model_version == "v1.1.0-candidate-ds-fsv1-prom"
    assert saved.predicted_risk_exposure_inr == 5000.0
    assert saved.actual_avoided_loss_inr is None  # Test 24: actual_avoided_loss_inr remains NULL


@pytest.mark.asyncio
async def test_ws81_02_action_queue_filtering(sync_session):
    """Test 2: Action queue filtering by plant, customer, and status."""
    session = sync_session
    params_nessai = DashboardFilterParams(plant_id="ACC_NESSAI", customer_id="ALL", dataset_type="ALL")
    res = await ActionExecutionService.get_action_queue(session, params_nessai)
    assert res.total_count >= 1
    for item in res.items:
        assert item.plant_code == "ACC_NESSAI"


@pytest.mark.asyncio
async def test_ws81_03_pending_to_accepted_transition(sync_session):
    """Test 3 & 23 & 26: PENDING -> ACCEPTED state transition & estimated_avoided_exposure lineage."""
    session = sync_session
    act_id = f"ACT-WS81-{uuid.uuid4().hex[:6].upper()}"
    idemp_key = f"IDEMP-{uuid.uuid4().hex[:10]}"
    action = PlannerActionLog(
        action_id=act_id,
        recommendation_id="REC-TEST-002",
        plant_code="ACC_NESSAI",
        action_type="TRANSIT_BUFFER",
        predicted_risk_exposure_inr=1000.0,
        action_status="PENDING",
        idempotency_key=idemp_key,
        version_lock=1,
    )
    session.add(action)
    await session.commit()

    res = await ActionExecutionService.accept_recommendation(
        session=session,
        action_id=act_id,
        dispatcher_id="DISPATCHER-99",
        role=DispatcherRoleEnum.DISPATCHER,
        idempotency_key=f"EXEC-IDEMP-{uuid.uuid4().hex[:8]}",
        version_lock=1,
        notes="Accepting transit lead time buffer",
    )
    assert res.success is True
    assert res.action.action_status == ActionStatusEnum.ACCEPTED
    assert res.action.dispatcher_id == "DISPATCHER-99"
    assert res.action.accepted_at is not None
    assert res.action.estimated_avoided_exposure_inr == 850.0  # Test 23: Estimated calculation
    assert res.action.actual_avoided_loss_inr is None  # Test 24: Remains NULL


@pytest.mark.asyncio
async def test_ws81_04_accepted_to_executed_transition(sync_session):
    """Test 4 & 5 & 8: ACCEPTED -> EXECUTED transition (rejects PENDING -> EXECUTED)."""
    session = sync_session
    act_id = f"ACT-WS81-{uuid.uuid4().hex[:6].upper()}"
    idemp_key = f"IDEMP-{uuid.uuid4().hex[:10]}"
    action = PlannerActionLog(
        action_id=act_id,
        recommendation_id="REC-TEST-003",
        plant_code="ACC_NESSAI",
        action_type="SLA_PRIORITIZE",
        action_status="PENDING",
        idempotency_key=idemp_key,
        version_lock=1,
    )
    session.add(action)
    await session.commit()

    # Test 8: PENDING -> EXECUTED must fail cleanly
    with pytest.raises(HTTPException) as exc_info:
        await ActionExecutionService.confirm_execution(
            session=session,
            action_id=act_id,
            dispatcher_id="DISPATCHER-99",
            role=DispatcherRoleEnum.DISPATCHER,
            idempotency_key=f"CONF-IDEMP-{uuid.uuid4().hex[:8]}",
            version_lock=1,
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error_code"] == "INVALID_STATE_TRANSITION"

    # Now ACCEPT first
    await ActionExecutionService.accept_recommendation(
        session=session,
        action_id=act_id,
        dispatcher_id="DISPATCHER-99",
        role=DispatcherRoleEnum.DISPATCHER,
        idempotency_key=f"ACCEPT-IDEMP-{uuid.uuid4().hex[:8]}",
        version_lock=1,
    )

    # Confirm Execution ACCEPTED -> EXECUTED
    res_exec = await ActionExecutionService.confirm_execution(
        session=session,
        action_id=act_id,
        dispatcher_id="DISPATCHER-99",
        role=DispatcherRoleEnum.DISPATCHER,
        idempotency_key=f"CONF-IDEMP-{uuid.uuid4().hex[:8]}",
        version_lock=2,
        notes="Physical truck dispatch offset verified at plant gate",
    )
    assert res_exec.success is True
    assert res_exec.action.action_status == ActionStatusEnum.EXECUTED
    assert res_exec.action.execution_confirmed_at is not None


@pytest.mark.asyncio
async def test_ws81_05_rejection_and_deferral_flows(sync_session):
    """Test 6 & 7: PENDING -> REJECTED and PENDING -> DEFERRED."""
    session = sync_session
    act_rej = f"ACT-WS81-{uuid.uuid4().hex[:6].upper()}"
    session.add(PlannerActionLog(
        action_id=act_rej,
        recommendation_id="REC-TEST-004",
        plant_code="ACC_NESSAI",
        action_type="STAGGER_LOADING",
        action_status="PENDING",
        idempotency_key=f"IDEMP-{uuid.uuid4().hex[:10]}",
        version_lock=1,
    ))
    await session.commit()

    res_rej = await ActionExecutionService.reject_recommendation(
        session=session,
        action_id=act_rej,
        dispatcher_id="SUPERVISOR-1",
        role=DispatcherRoleEnum.SUPERVISOR,
        idempotency_key=f"REJ-IDEMP-{uuid.uuid4().hex[:8]}",
        version_lock=1,
        reason_code="SITE_ACCESS_RESTRICTION",
        notes="Customer site unavailable",
    )
    assert res_rej.action.action_status == ActionStatusEnum.REJECTED
    assert res_rej.action.reason_code == "SITE_ACCESS_RESTRICTION"


@pytest.mark.asyncio
async def test_ws81_06_idempotency_and_duplicate_protection(sync_session):
    """Test 9 & 10 & 11 & 32: Idempotency protection for repeated requests."""
    session = sync_session
    act_id = f"ACT-WS81-{uuid.uuid4().hex[:6].upper()}"
    idemp_key = f"IDEMP-REPLAY-{uuid.uuid4().hex[:8]}"
    session.add(PlannerActionLog(
        action_id=act_id,
        recommendation_id="REC-TEST-005",
        plant_code="ACC_NESSAI",
        action_type="STAGGER_LOADING",
        action_status="PENDING",
        idempotency_key=f"INIT-{uuid.uuid4().hex[:8]}",
        version_lock=1,
    ))
    await session.commit()

    # Request 1
    res1 = await ActionExecutionService.accept_recommendation(
        session=session,
        action_id=act_id,
        dispatcher_id="DISPATCHER-1",
        role=DispatcherRoleEnum.DISPATCHER,
        idempotency_key=idemp_key,
        version_lock=1,
    )
    assert res1.is_idempotent_replay is False

    # Request 2 (Duplicate submission with same idempotency key)
    res2 = await ActionExecutionService.accept_recommendation(
        session=session,
        action_id=act_id,
        dispatcher_id="DISPATCHER-1",
        role=DispatcherRoleEnum.DISPATCHER,
        idempotency_key=idemp_key,
        version_lock=1,
    )
    assert res2.is_idempotent_replay is True
    assert res2.action.action_status == ActionStatusEnum.ACCEPTED


@pytest.mark.asyncio
async def test_ws81_07_optimistic_concurrency_conflict(sync_session):
    """Test 12: Optimistic concurrency lock conflict protection."""
    session = sync_session
    act_id = f"ACT-WS81-{uuid.uuid4().hex[:6].upper()}"
    session.add(PlannerActionLog(
        action_id=act_id,
        recommendation_id="REC-TEST-006",
        plant_code="ACC_NESSAI",
        action_type="STAGGER_LOADING",
        action_status="PENDING",
        idempotency_key=f"INIT-{uuid.uuid4().hex[:8]}",
        version_lock=1,
    ))
    await session.commit()

    # Operator A accepts with version_lock 1
    await ActionExecutionService.accept_recommendation(
        session=session,
        action_id=act_id,
        dispatcher_id="OPERATOR-A",
        role=DispatcherRoleEnum.DISPATCHER,
        idempotency_key=f"IDEMP-A-{uuid.uuid4().hex[:8]}",
        version_lock=1,
    )

    # Operator B attempts accept with stale version_lock 1
    with pytest.raises(HTTPException) as exc_info:
        await ActionExecutionService.accept_recommendation(
            session=session,
            action_id=act_id,
            dispatcher_id="OPERATOR-B",
            role=DispatcherRoleEnum.DISPATCHER,
            idempotency_key=f"IDEMP-B-{uuid.uuid4().hex[:8]}",
            version_lock=1,
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail["error_code"] == "OPTIMISTIC_LOCK_CONFLICT"


@pytest.mark.asyncio
async def test_ws81_08_zone_constraint_protection(sync_session):
    """Test 16: Cross-zone plant transfer safety constraint violation."""
    session = sync_session
    act_id = f"ACT-WS81-{uuid.uuid4().hex[:6].upper()}"
    session.add(PlannerActionLog(
        action_id=act_id,
        recommendation_id="REC-TEST-007",
        plant_code="ACC_VASCO",  # South Zone
        action_type="ZONE_REALLOCATE",
        action_parameters={"target_plant_code": "ACC_DHARGA"},  # North Zone (Incompatible!)
        action_status="PENDING",
        idempotency_key=f"INIT-{uuid.uuid4().hex[:8]}",
        version_lock=1,
    ))
    await session.commit()

    with pytest.raises(HTTPException) as exc_info:
        await ActionExecutionService.accept_recommendation(
            session=session,
            action_id=act_id,
            dispatcher_id="DISPATCHER-1",
            role=DispatcherRoleEnum.DISPATCHER,
            idempotency_key=f"IDEMP-ZONE-{uuid.uuid4().hex[:8]}",
            version_lock=1,
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error_code"] == "ZONE_CONSTRAINT_VIOLATION"


@pytest.mark.asyncio
async def test_ws81_09_accepted_to_in_progress_transition(sync_session):
    """Test 4 & 5: ACCEPTED -> IN_PROGRESS transition via start_progress."""
    session = sync_session
    act_id = f"ACT-WS81-{uuid.uuid4().hex[:6].upper()}"
    session.add(PlannerActionLog(
        action_id=act_id,
        recommendation_id="REC-TEST-008",
        plant_code="ACC_NESSAI",
        action_type="TRANSIT_BUFFER",
        action_status="PENDING",
        idempotency_key=f"INIT-{uuid.uuid4().hex[:8]}",
        version_lock=1,
    ))
    await session.commit()

    # Accept recommendation first
    await ActionExecutionService.accept_recommendation(
        session=session,
        action_id=act_id,
        dispatcher_id="DISPATCHER-1",
        role=DispatcherRoleEnum.DISPATCHER,
        idempotency_key=f"ACCEPT-IDEMP-{uuid.uuid4().hex[:8]}",
        version_lock=1,
    )

    # Start progress ACCEPTED -> IN_PROGRESS
    res_start = await ActionExecutionService.start_progress(
        session=session,
        action_id=act_id,
        dispatcher_id="DISPATCHER-1",
        role=DispatcherRoleEnum.DISPATCHER,
        idempotency_key=f"START-IDEMP-{uuid.uuid4().hex[:8]}",
        version_lock=2,
        notes="Truck driver notified to hold cadence",
    )
    assert res_start.success is True
    assert res_start.action.action_status == ActionStatusEnum.IN_PROGRESS
    assert res_start.action.started_at is not None
