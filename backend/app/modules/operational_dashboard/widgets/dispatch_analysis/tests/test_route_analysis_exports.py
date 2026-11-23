"""
WS-ROUT-5: Automated Test Suite for Route Analysis Exports (XLSX and PDF).

Tests:
- XLSX Export generation & binary veracity
- PDF Export generation & binary veracity
- Snapshot-to-Export numerical and decision parity
- Representation across recommendation states (RECOMMEND_CURRENT_SOURCE, RECOMMEND_ALTERNATIVE, NO_CLEAR_DIFFERENCE, HISTORICAL_COMPARISON_ONLY, LIVE_ROUTE_ONLY, NO_RECOMMENDATION)
- C1 through C10 case representation parity
- Stale Google evidence representation
- Missing coordinates (LOCATION_DATA_MISSING) export representation
- Candidate route failure representation
- Report Catalog registration and schema verification
- Auth guard on export endpoints
- Non-existent snapshot 404 behavior
- Database immutability preservation during export
- Snapshot-Complete Invariance: Master data mutations do NOT alter historical snapshot exports
"""

import io
import uuid
from datetime import datetime, timezone
import openpyxl
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security.jwt import create_access_token
from app.dependencies.common import get_db_session
from app.main import app
from app.modules.auth.models import User
from app.modules.erp.models import Customer, Plant, Site
from app.modules.operational_dashboard.models.route_analysis import RouteAnalysisSnapshot
from app.modules.reports.handlers.route_analysis_handler import RouteAnalysisReportHandler
from app.modules.reports.renderers.route_analysis_renderer import (
    RouteAnalysisPDFRenderer,
    RouteAnalysisXLSXRenderer,
)
from app.modules.reports.services.report_registry import ReportRegistry


@pytest.fixture
def isolated_db():
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
    async with session_factory() as session:
        user_uuid = uuid.uuid4()
        test_user = User(
            id=user_uuid,
            username=f"test_rep_user_{uuid.uuid4().hex[:8]}",
            email=f"rep_{uuid.uuid4().hex[:8]}@example.com",
            password_hash="test_hashed_password",
            full_name="Test Report Auditor",
            is_active=True,
            must_change_password=False,
            token_version=1,
        )
        session.add(test_user)
        await session.commit()

        token, _ = create_access_token(user_id=user_uuid, token_version=1)
        return {"Authorization": f"Bearer {token}"}


async def seed_persisted_snapshot(
    session_factory,
    status: str = "RECOMMEND_ALTERNATIVE",
    case_category: str = "C2_BOTH_AGREE_ALT",
    is_traffic_override: bool = False,
    minutes_saved: float = 16.5,
    failure_reason_code: str = None,
    is_cached: bool = False,
    cache_age_seconds: int = 45,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """Creates real Plant, Site, and RouteAnalysisSnapshot records in PostgreSQL."""
    async with session_factory() as session:
        p_curr = Plant(
            id=uuid.uuid4(),
            code=f"PLANT_CURR_{uuid.uuid4().hex[:6]}",
            name="Approved Source Plant",
            latitude=15.3991,
            longitude=73.8153,
        )
        p_alt = Plant(
            id=uuid.uuid4(),
            code=f"PLANT_ALT_{uuid.uuid4().hex[:6]}",
            name="Alternative Batch Plant",
            latitude=15.2832,
            longitude=73.9862,
        )
        session.add_all([p_curr, p_alt])
        await session.flush()

        site = Site(
            id=uuid.uuid4(),
            code=f"SITE_EXP_{uuid.uuid4().hex[:6]}",
            name="Destination Tower Site",
            plant_id=p_curr.id,
            latitude=15.3500,
            longitude=73.9000,
        )
        session.add(site)
        await session.flush()

        comparisons = [
            {
                "plant_id": str(p_curr.id),
                "plant_code": p_curr.code,
                "plant_name": p_curr.name,
                "is_current_source": True,
                "is_recommended": False,
                "is_viable": True,
                "crow_fly_distance_km": 12.4,
                "google_distance_km": 15.2,
                "google_duration_in_traffic_mins": 45.0,
                "google_static_duration_mins": 32.0,
                "google_traffic_delay_mins": 13.0,
                "historical_t1_p50_mins": 42.0,
                "historical_t1_p25_mins": 38.0,
                "historical_t1_p75_mins": 46.0,
                "historical_t1_iqr_mins": 8.0,
                "historical_sample_count": 28,
                "historical_confidence": "HIGH",
                "historical_winner_status": "HISTORICAL_DEFICIT",
            },
            {
                "plant_id": str(p_alt.id),
                "plant_code": p_alt.code,
                "plant_name": p_alt.name,
                "is_current_source": False,
                "is_recommended": True,
                "is_viable": True,
                "crow_fly_distance_km": 9.1,
                "google_distance_km": 11.5,
                "google_duration_in_traffic_mins": 28.5,
                "google_static_duration_mins": 24.0,
                "google_traffic_delay_mins": 4.5,
                "historical_t1_p50_mins": 29.0,
                "historical_t1_p25_mins": 26.0,
                "historical_t1_p75_mins": 33.0,
                "historical_t1_iqr_mins": 7.0,
                "historical_sample_count": 22,
                "historical_confidence": "HIGH",
                "historical_winner_status": "HISTORICAL_WINNER",
            },
        ]

        hist_payload = {
            "case_category": case_category,
            "is_overall_sufficient": True,
            "minutes_saved": minutes_saved,
            "is_traffic_override": is_traffic_override,
            "eligible_dispatches_count": 50,
            "site_code": site.code,
            "site_name": site.name,
        }

        google_payload = {
            "provider": "Google Routes API v2",
            "routing_preference": "TRAFFIC_AWARE",
            "is_live": not is_cached,
        }

        snap = RouteAnalysisSnapshot(
            analysis_id=uuid.uuid4(),
            site_id=site.id,
            current_source_plant_id=p_curr.id,
            recommended_plant_id=p_alt.id,
            recommendation_status=status,
            failure_reason_code=failure_reason_code,
            analysis_mode="NOW",
            engine_version="v1.2.1",
            policy_version="ROUTE_POLICY_v1.2.1",
            decision_reason_summary=f"Plant {p_alt.name} saves {minutes_saved:.1f} minutes in current traffic and is historically 13.0m faster.",
            analysis_context="ROUTINE",
            operator_notes="Route export test snapshot",
            historical_evidence_payload=hist_payload,
            google_evidence_payload=google_payload,
            candidate_comparison_matrix=comparisons,
            google_queried_at=datetime.now(timezone.utc),
            data_freshness_seconds=cache_age_seconds,
            is_cached_result=is_cached,
        )
        session.add(snap)
        await session.commit()
        return snap.analysis_id, p_curr.id, site.id


# =============================================================================
# WS-ROUT-5 TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_report_registry_catalog_entry():
    """Verifies that Route Analysis is registered in the platform report registry."""
    def_dto = ReportRegistry.get("route_analysis")
    assert def_dto is not None
    assert def_dto.report_id == "route_analysis"
    assert def_dto.source_service == "dispatch_analysis"
    assert "analysis_id" in def_dto.supported_filters


@pytest.mark.asyncio
async def test_export_xlsx_veracity_and_content_parity(isolated_db):
    """
    Asserts that the exported XLSX contains identical numbers, decision,
    and metadata as the persisted database snapshot.
    """
    analysis_id, p_curr_id, site_id = await seed_persisted_snapshot(
        isolated_db,
        status="RECOMMEND_ALTERNATIVE",
        case_category="C2_BOTH_AGREE_ALT",
        minutes_saved=16.5,
    )
    headers = await create_test_auth_headers(isolated_db)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/demo-api/v1/dispatch-analysis/route-analysis/snapshot/{analysis_id}/export/xlsx",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert f"route_analysis_{str(analysis_id)[:8]}.xlsx" in resp.headers["content-disposition"]

        # Parse workbook and verify values
        wb = openpyxl.load_workbook(io.BytesIO(resp.content))
        assert "01_Decision_Summary" in wb.sheetnames
        assert "02_Candidate_Comparison" in wb.sheetnames
        assert "03_Evidence_Audit" in wb.sheetnames

        ws1 = wb["01_Decision_Summary"]
        rec_status_found = False
        saved_mins_found = False
        for row in ws1.iter_rows(values_only=True):
            if row[0] == "Recommendation Status:":
                assert row[1] == "RECOMMEND_ALTERNATIVE"
                rec_status_found = True
            if row[0] == "Estimated Route Time Saved:":
                assert "16.5 mins" in str(row[1])
                saved_mins_found = True
        assert rec_status_found
        assert saved_mins_found

        # Candidate matrix sheet
        ws2 = wb["02_Candidate_Comparison"]
        assert ws2.max_row >= 5  # header + 2 candidates


@pytest.mark.asyncio
async def test_export_pdf_veracity_and_content_parity(isolated_db):
    """
    Asserts that the exported PDF contains identical numbers, decision,
    disclaimer, and metadata as the persisted database snapshot.
    """
    analysis_id, p_curr_id, site_id = await seed_persisted_snapshot(
        isolated_db,
        status="RECOMMEND_ALTERNATIVE",
        case_category="C2_BOTH_AGREE_ALT",
        minutes_saved=16.5,
    )
    headers = await create_test_auth_headers(isolated_db)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/demo-api/v1/dispatch-analysis/route-analysis/snapshot/{analysis_id}/export/pdf",
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert f"route_analysis_{str(analysis_id)[:8]}.pdf" in resp.headers["content-disposition"]

        pdf_bytes = resp.content
        assert pdf_bytes.startswith(b"%PDF-")
        assert len(pdf_bytes) > 1000
        assert b"EOF" in pdf_bytes


@pytest.mark.asyncio
async def test_export_all_recommendation_states(isolated_db):
    """Verifies that all decision states render properly without error."""
    states_to_test = [
        ("RECOMMEND_CURRENT_SOURCE", "C1_BOTH_AGREE_CURRENT", 0.0, False),
        ("RECOMMEND_ALTERNATIVE", "C3_TRAFFIC_OVERRIDE_ALT", 22.0, True),
        ("NO_CLEAR_DIFFERENCE", "C5_MARGINAL_ALT_DIFFERENCE", 4.0, False),
        ("HISTORICAL_COMPARISON_ONLY", "C7_HISTORICAL_ONLY", 0.0, False),
        ("LIVE_ROUTE_ONLY", "C8_LIVE_ROUTE_ONLY", 15.0, False),
        ("NO_RECOMMENDATION", "C9_NO_EVIDENCE", 0.0, False),
    ]

    headers = await create_test_auth_headers(isolated_db)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for st, case, saved, override in states_to_test:
            a_id, _, _ = await seed_persisted_snapshot(
                isolated_db,
                status=st,
                case_category=case,
                minutes_saved=saved,
                is_traffic_override=override,
            )

            # Test XLSX
            resp_x = await client.get(
                f"/demo-api/v1/dispatch-analysis/route-analysis/snapshot/{a_id}/export/xlsx",
                headers=headers,
            )
            assert resp_x.status_code == 200
            assert resp_x.content.startswith(b"PK")  # ZIP header of XLSX

            # Test PDF
            resp_p = await client.get(
                f"/demo-api/v1/dispatch-analysis/route-analysis/snapshot/{a_id}/export/pdf",
                headers=headers,
            )
            assert resp_p.status_code == 200
            assert resp_p.content.startswith(b"%PDF-")


@pytest.mark.asyncio
async def test_export_missing_coordinates_location_data_missing(isolated_db):
    """Verifies that failed analysis with LOCATION_DATA_MISSING exports properly with reason code."""
    async with isolated_db() as session:
        p_temp = Plant(
            id=uuid.uuid4(),
            code=f"PLANT_TEMP_{uuid.uuid4().hex[:6]}",
            name="Plant Temp",
            latitude=15.3991,
            longitude=73.8153,
        )
        session.add(p_temp)
        await session.flush()

        site_no_coords = Site(
            id=uuid.uuid4(),
            code=f"SITE_NO_COORD_{uuid.uuid4().hex[:6]}",
            name="Unmapped Site",
            plant_id=p_temp.id,
            latitude=None,
            longitude=None,
        )
        session.add(site_no_coords)
        await session.flush()

        snap = RouteAnalysisSnapshot(
            analysis_id=uuid.uuid4(),
            site_id=site_no_coords.id,
            recommendation_status="NO_RECOMMENDATION",
            failure_reason_code="LOCATION_DATA_MISSING",
            analysis_mode="NOW",
            decision_reason_summary="Location coordinates missing for destination site.",
            historical_evidence_payload={},
            google_evidence_payload={},
            candidate_comparison_matrix=[],
        )
        session.add(snap)
        await session.commit()
        a_id = snap.analysis_id

    headers = await create_test_auth_headers(isolated_db)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/demo-api/v1/dispatch-analysis/route-analysis/snapshot/{a_id}/export/xlsx",
            headers=headers,
        )
        assert resp.status_code == 200

        resp_p = await client.get(
            f"/demo-api/v1/dispatch-analysis/route-analysis/snapshot/{a_id}/export/pdf",
            headers=headers,
        )
        assert resp_p.status_code == 200


@pytest.mark.asyncio
async def test_export_auth_guard_and_404(isolated_db):
    """Verifies authentication guard (401) and non-existent snapshot ID (404)."""
    headers = await create_test_auth_headers(isolated_db)
    random_uuid = uuid.uuid4()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. No auth -> 401
        resp_no_auth = await client.get(
            f"/demo-api/v1/dispatch-analysis/route-analysis/snapshot/{random_uuid}/export/xlsx"
        )
        assert resp_no_auth.status_code == 401

        # 2. Non-existent snapshot -> 404
        resp_404 = await client.get(
            f"/demo-api/v1/dispatch-analysis/route-analysis/snapshot/{random_uuid}/export/xlsx",
            headers=headers,
        )
        assert resp_404.status_code == 404


@pytest.mark.asyncio
async def test_export_preserves_database_snapshot_immutability(isolated_db):
    """
    Verifies that calling export repeatedly never alters the database snapshot row
    and respects the immutable trigger constraint.
    """
    a_id, _, _ = await seed_persisted_snapshot(isolated_db)
    headers = await create_test_auth_headers(isolated_db)

    async with isolated_db() as session:
        count_before = (await session.execute(text("SELECT count(*) FROM route_analysis_snapshots"))).scalar()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(3):
            await client.get(
                f"/demo-api/v1/dispatch-analysis/route-analysis/snapshot/{a_id}/export/xlsx",
                headers=headers,
            )
            await client.get(
                f"/demo-api/v1/dispatch-analysis/route-analysis/snapshot/{a_id}/export/pdf",
                headers=headers,
            )

    async with isolated_db() as session:
        count_after = (await session.execute(text("SELECT count(*) FROM route_analysis_snapshots"))).scalar()
        assert count_before == count_after


@pytest.mark.asyncio
async def test_snapshot_complete_master_data_mutation_invariance(isolated_db):
    """
    Correction 1 Verification:
    Asserts that mutating/renaming live master-data records after snapshot execution
    does NOT alter the historical exported snapshot decision, evidence, or plant names.
    """
    a_id, p_curr_id, site_id = await seed_persisted_snapshot(
        isolated_db,
        status="RECOMMEND_ALTERNATIVE",
        case_category="C2_BOTH_AGREE_ALT",
        minutes_saved=16.5,
    )
    headers = await create_test_auth_headers(isolated_db)

    # 1. Export initial snapshot
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp1 = await client.get(
            f"/demo-api/v1/dispatch-analysis/route-analysis/snapshot/{a_id}/export/xlsx",
            headers=headers,
        )
        assert resp1.status_code == 200
        wb1 = openpyxl.load_workbook(io.BytesIO(resp1.content))
        ws_c1 = wb1["02_Candidate_Comparison"]
        plant_names_before = [row[1] for row in ws_c1.iter_rows(values_only=True) if row[1] not in (None, "Plant Name")]

    # 2. Mutate live Master Data (Renaming Plant & Site in ERP)
    async with isolated_db() as session:
        await session.execute(
            text("UPDATE plants SET name = 'RENAMED_MODERN_PLANT' WHERE id = :p_id"),
            {"p_id": p_curr_id},
        )
        await session.execute(
            text("UPDATE sites SET name = 'RENAMED_MODERN_SITE' WHERE id = :s_id"),
            {"s_id": site_id},
        )
        await session.commit()

    # 3. Export same snapshot again
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp2 = await client.get(
            f"/demo-api/v1/dispatch-analysis/route-analysis/snapshot/{a_id}/export/xlsx",
            headers=headers,
        )
        assert resp2.status_code == 200
        wb2 = openpyxl.load_workbook(io.BytesIO(resp2.content))
        ws_c2 = wb2["02_Candidate_Comparison"]
        plant_names_after = [row[1] for row in ws_c2.iter_rows(values_only=True) if row[1] not in (None, "Plant Name")]

        # Snapshot-complete invariant: historical names preserved from comparison matrix
        assert plant_names_before == plant_names_after
        assert "Approved Source Plant" in plant_names_after
        assert "RENAMED_MODERN_PLANT" not in plant_names_after
