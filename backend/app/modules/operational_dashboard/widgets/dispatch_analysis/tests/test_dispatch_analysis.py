import pytest
from app.modules.operational_dashboard.widgets.dispatch_analysis.services.cadence_engine import DispatchCadenceEngine
from app.modules.operational_dashboard.widgets.dispatch_analysis.dtos import OperationalIntelligenceStatusEnum
from app.core.database import AsyncSessionFactory


@pytest.mark.asyncio
async def test_get_dispatch_analysis_all_endpoints():
    async with AsyncSessionFactory() as session:
        filters = {"plant_id": None, "customer_id": None, "dataset_type": "REAL_ONLY"}

        # 1. KPIs
        res_kpi = await DispatchCadenceEngine.get_kpis(session, filters)
        assert res_kpi.success is True
        assert res_kpi.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_kpi.data.total_dispatches > 0
        assert res_kpi.data.completed_dispatches >= 0

        # 2. Cadence Table
        res_cadence = await DispatchCadenceEngine.get_cadence_table(session, filters)
        assert res_cadence.success is True
        assert res_cadence.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert len(res_cadence.data) > 0

        # 3. Delay Analytics
        res_delay = await DispatchCadenceEngine.get_delay_analytics(session, filters)
        assert res_delay.success is True
        assert res_delay.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_delay.data.total_delay_hours >= 0.0

        # 4. Operational Insights
        res_insights = await DispatchCadenceEngine.get_operational_insights(session, filters)
        assert res_insights.success is True
        assert res_insights.status == OperationalIntelligenceStatusEnum.AVAILABLE
        assert res_insights.data.total_insights > 0
        assert res_insights.data.target_departure_interval_mins > 0.0
        assert len(res_insights.data.insights) > 0
        first_insight = res_insights.data.insights[0]
        assert first_insight.id.startswith("INSIGHT-")
        assert first_insight.impact_level in ["HIGH", "MEDIUM", "LOW"]


# =============================================================================
# WS-ROUT-1: ERP T1 TRANSIT STATISTICS ENGINE TEST SUITE (FROZEN BLUEPRINT v1.2.1)
# =============================================================================

from datetime import datetime, timezone, timedelta
from uuid import uuid4
from app.modules.operational_dashboard.widgets.dispatch_analysis.services import (
    HistoricalCleansingPipeline,
    HistoricalRouteEvidenceService,
)
from app.modules.operational_dashboard.widgets.dispatch_analysis.dtos import (
    HistoricalConfidenceLevel,
    HistoricalWinnerOutcome,
)


def test_t1_calc_completed_only():
    """Stage 1 Cleansing: Excludes dispatches where status != 'COMPLETED'."""
    now = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
    w_start = now - timedelta(days=90)
    w_end = now

    raw_rows = [
        {
            "dispatch_id": uuid4(),
            "dispatch_number": "DISP-1",
            "status": "COMPLETED",
            "plant_id": uuid4(),
            "site_id": uuid4(),
            "dispatch_date": now,
            "time_out": "10:00:00",
            "time_in": "10:45:00",
            "t1_transit_mins": 45.0,
            "distance_km": 20.0,
        },
        {
            "dispatch_id": uuid4(),
            "dispatch_number": "DISP-2",
            "status": "DISPATCHED",  # Incomplete / In-transit
            "plant_id": uuid4(),
            "site_id": uuid4(),
            "dispatch_date": now,
            "time_out": "10:00:00",
            "time_in": "10:45:00",
            "t1_transit_mins": 45.0,
            "distance_km": 20.0,
        },
        {
            "dispatch_id": uuid4(),
            "dispatch_number": "DISP-3",
            "status": "CANCELLED",  # Cancelled
            "plant_id": uuid4(),
            "site_id": uuid4(),
            "dispatch_date": now,
            "time_out": "10:00:00",
            "time_in": "10:45:00",
            "t1_transit_mins": 45.0,
            "distance_km": 20.0,
        },
    ]

    cleansed = HistoricalCleansingPipeline.cleanse_and_filter_records(raw_rows, w_start, w_end)
    assert len(cleansed) == 1
    assert cleansed[0].dispatch_number == "DISP-1"


def test_t1_calc_valid_bounds():
    """Stage 5 Cleansing: Excludes T1 < 5.0m and T1 > 300.0m."""
    now = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
    w_start = now - timedelta(days=90)
    w_end = now
    pid = uuid4()
    sid = uuid4()

    raw_rows = [
        # Normal 45m -> Keep
        {
            "dispatch_id": uuid4(),
            "dispatch_number": "DISP-VALID",
            "status": "COMPLETED",
            "plant_id": pid,
            "site_id": sid,
            "dispatch_date": now,
            "time_out": "10:00:00",
            "time_in": "10:45:00",
            "t1_transit_mins": 45.0,
            "distance_km": 20.0,
        },
        # Impossible 2m -> Exclude (< 5.0m)
        {
            "dispatch_id": uuid4(),
            "dispatch_number": "DISP-TOO-FAST",
            "status": "COMPLETED",
            "plant_id": pid,
            "site_id": sid,
            "dispatch_date": now,
            "time_out": "10:00:00",
            "time_in": "10:02:00",
            "t1_transit_mins": 2.0,
            "distance_km": 20.0,
        },
        # Extreme breakdown 340m -> Exclude (> 300.0m)
        {
            "dispatch_id": uuid4(),
            "dispatch_number": "DISP-BREAKDOWN",
            "status": "COMPLETED",
            "plant_id": pid,
            "site_id": sid,
            "dispatch_date": now,
            "time_out": "10:00:00",
            "time_in": "15:40:00",
            "t1_transit_mins": 340.0,
            "distance_km": 20.0,
        },
    ]

    cleansed = HistoricalCleansingPipeline.cleanse_and_filter_records(raw_rows, w_start, w_end)
    assert len(cleansed) == 1
    assert cleansed[0].dispatch_number == "DISP-VALID"
    assert cleansed[0].t1_transit_mins == 45.0


def test_t1_calc_distance_bounds():
    """Stage 6 Cleansing: Excludes distance < 0.5 km and > 150.0 km."""
    now = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
    w_start = now - timedelta(days=90)
    w_end = now
    pid = uuid4()
    sid = uuid4()

    raw_rows = [
        # Valid 25km -> Keep
        {
            "dispatch_id": uuid4(),
            "dispatch_number": "DISP-NORMAL-DIST",
            "status": "COMPLETED",
            "plant_id": pid,
            "site_id": sid,
            "dispatch_date": now,
            "time_out": "10:00:00",
            "time_in": "10:45:00",
            "t1_transit_mins": 45.0,
            "distance_km": 25.0,
        },
        # Zero/negative distance 0.1km -> Exclude
        {
            "dispatch_id": uuid4(),
            "dispatch_number": "DISP-ZERO-DIST",
            "status": "COMPLETED",
            "plant_id": pid,
            "site_id": sid,
            "dispatch_date": now,
            "time_out": "10:00:00",
            "time_in": "10:45:00",
            "t1_transit_mins": 45.0,
            "distance_km": 0.1,
        },
        # Outlier 220km -> Exclude (> 150.0km)
        {
            "dispatch_id": uuid4(),
            "dispatch_number": "DISP-HUGE-DIST",
            "status": "COMPLETED",
            "plant_id": pid,
            "site_id": sid,
            "dispatch_date": now,
            "time_out": "10:00:00",
            "time_in": "10:45:00",
            "t1_transit_mins": 45.0,
            "distance_km": 220.0,
        },
    ]

    cleansed = HistoricalCleansingPipeline.cleanse_and_filter_records(raw_rows, w_start, w_end)
    assert len(cleansed) == 1
    assert cleansed[0].dispatch_number == "DISP-NORMAL-DIST"


def test_t1_calc_dedup_tickets():
    """Stage 7 Cleansing: Deduplicates duplicate trip numbers across the same plant/site pair."""
    now = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
    w_start = now - timedelta(days=90)
    w_end = now
    pid = uuid4()
    sid = uuid4()

    raw_rows = [
        {
            "dispatch_id": uuid4(),
            "dispatch_number": "DISP-DUP-1",
            "trip_number": "TRIP-100",
            "status": "COMPLETED",
            "plant_id": pid,
            "site_id": sid,
            "dispatch_date": now,
            "time_out": "10:00:00",
            "time_in": "10:45:00",
            "t1_transit_mins": 45.0,
            "distance_km": 20.0,
        },
        # Duplicate row with same plant, site, and trip_number
        {
            "dispatch_id": uuid4(),
            "dispatch_number": "DISP-DUP-2",
            "trip_number": "TRIP-100",
            "status": "COMPLETED",
            "plant_id": pid,
            "site_id": sid,
            "dispatch_date": now,
            "time_out": "10:00:00",
            "time_in": "10:45:00",
            "t1_transit_mins": 45.0,
            "distance_km": 20.0,
        },
    ]

    cleansed = HistoricalCleansingPipeline.cleanse_and_filter_records(raw_rows, w_start, w_end)
    assert len(cleansed) == 1
    assert cleansed[0].trip_number == "TRIP-100"


def test_t1_calc_90d_window():
    """Stage 8 Cleansing: Excludes trips outside the rolling 90-day window."""
    now = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
    w_start = now - timedelta(days=90)  # 2026-05-03
    w_end = now
    pid = uuid4()
    sid = uuid4()

    raw_rows = [
        # Inside window (2026-07-15) -> Keep
        {
            "dispatch_id": uuid4(),
            "dispatch_number": "DISP-INSIDE",
            "status": "COMPLETED",
            "plant_id": pid,
            "site_id": sid,
            "dispatch_date": datetime(2026, 7, 15, 10, 0, 0, tzinfo=timezone.utc),
            "time_out": "10:00:00",
            "time_in": "10:45:00",
            "t1_transit_mins": 45.0,
            "distance_km": 20.0,
        },
        # Outside window (2026-01-10) -> Exclude (> 90 days ago)
        {
            "dispatch_id": uuid4(),
            "dispatch_number": "DISP-TOO-OLD",
            "status": "COMPLETED",
            "plant_id": pid,
            "site_id": sid,
            "dispatch_date": datetime(2026, 1, 10, 10, 0, 0, tzinfo=timezone.utc),
            "time_out": "10:00:00",
            "time_in": "10:45:00",
            "t1_transit_mins": 45.0,
            "distance_km": 20.0,
        },
    ]

    cleansed = HistoricalCleansingPipeline.cleanse_and_filter_records(raw_rows, w_start, w_end)
    assert len(cleansed) == 1
    assert cleansed[0].dispatch_number == "DISP-INSIDE"


def test_t1_percentile_math():
    """Percentile Math: Validates exact p25, p50 (median), p75, and IQR on continuous distributions."""
    # Test on a known 5-element dataset: [30, 40, 50, 60, 70]
    data_5 = [30.0, 40.0, 50.0, 60.0, 70.0]
    p25, p50, p75, iqr = HistoricalRouteEvidenceService.calculate_percentiles(data_5)
    assert p50 == 50.0
    assert p25 == 40.0
    assert p75 == 60.0
    assert iqr == 20.0

    # Test on single element
    p25_1, p50_1, p75_1, iqr_1 = HistoricalRouteEvidenceService.calculate_percentiles([45.0])
    assert p50_1 == 45.0
    assert iqr_1 == 0.0

    # Test on empty list
    assert HistoricalRouteEvidenceService.calculate_percentiles([]) == (0.0, 0.0, 0.0, 0.0)


def test_t1_timezone_utc_parse():
    """Timezone & Timestamp Parsing: Anchors time-of-day strings to date in UTC."""
    disp_date = datetime(2026, 8, 15, 0, 0, 0, tzinfo=timezone.utc)
    t_out = HistoricalCleansingPipeline.parse_time_component(disp_date, "09:30:00")
    t_in = HistoricalCleansingPipeline.parse_time_component(disp_date, "10:15:00")

    assert t_out is not None
    assert t_in is not None
    assert t_out.hour == 9 and t_out.minute == 30 and t_out.tzinfo == timezone.utc
    assert t_in.hour == 10 and t_in.minute == 15 and t_in.tzinfo == timezone.utc

    t1 = HistoricalCleansingPipeline.calculate_t1_minutes(None, t_out, t_in)
    assert t1 == 45.0


def test_historical_tie_threshold_rule():
    """Historical Winner Tie Rule: Sub-2.0 min differences output NO_MEANINGFUL_HISTORICAL_DIFFERENCE."""
    # Scenario 1: Marginal difference 0.8 min (|Δ| = 0.8 < 2.0) -> TIE
    outcome, delta, expl = HistoricalRouteEvidenceService.evaluate_winner(
        current_p50=45.0,
        current_sample_count=20,
        candidate_p50=44.2,
        candidate_sample_count=18,
        tie_threshold=2.0,
    )
    assert outcome == HistoricalWinnerOutcome.NO_MEANINGFUL_HISTORICAL_DIFFERENCE
    assert delta == 0.8
    assert "No meaningful historical difference" in expl

    # Scenario 2: Current plant faster by 6.0 mins (Δ = -6.0 <= -2.0) -> CURRENT_PLANT_FASTER
    outcome_c, delta_c, _ = HistoricalRouteEvidenceService.evaluate_winner(
        current_p50=40.0,
        current_sample_count=20,
        candidate_p50=46.0,
        candidate_sample_count=18,
        tie_threshold=2.0,
    )
    assert outcome_c == HistoricalWinnerOutcome.CURRENT_PLANT_FASTER
    assert delta_c == -6.0

    # Scenario 3: Candidate plant faster by 12.0 mins (Δ = +12.0 >= +2.0) -> CANDIDATE_PLANT_FASTER
    outcome_a, delta_a, _ = HistoricalRouteEvidenceService.evaluate_winner(
        current_p50=55.0,
        current_sample_count=20,
        candidate_p50=43.0,
        candidate_sample_count=18,
        tie_threshold=2.0,
    )
    assert outcome_a == HistoricalWinnerOutcome.CANDIDATE_PLANT_FASTER
    assert delta_a == 12.0

    # Scenario 4: Insufficient sample count (N = 3 < 5) -> INSUFFICIENT_EVIDENCE
    outcome_insuff, _, _ = HistoricalRouteEvidenceService.evaluate_winner(
        current_p50=40.0,
        current_sample_count=3,
        candidate_p50=46.0,
        candidate_sample_count=18,
        tie_threshold=2.0,
    )
    assert outcome_insuff == HistoricalWinnerOutcome.INSUFFICIENT_EVIDENCE


def test_historical_confidence_classification():
    """Confidence Classification: High (N>=15, IQR<=20m), Moderate (5<=N<15), Low (1<=N<5), None (N=0)."""
    # High: N=20, IQR=12.0m
    assert HistoricalRouteEvidenceService.classify_confidence(20, 12.0) == HistoricalConfidenceLevel.HIGH
    # Moderate because IQR is too wide (25.0m > 20.0m)
    assert HistoricalRouteEvidenceService.classify_confidence(20, 25.0) == HistoricalConfidenceLevel.MODERATE
    # Moderate: N=8, IQR=10.0m
    assert HistoricalRouteEvidenceService.classify_confidence(8, 10.0) == HistoricalConfidenceLevel.MODERATE
    # Low: N=3
    assert HistoricalRouteEvidenceService.classify_confidence(3, 8.0) == HistoricalConfidenceLevel.LOW
    # None: N=0
    assert HistoricalRouteEvidenceService.classify_confidence(0, 0.0) == HistoricalConfidenceLevel.NONE


@pytest.mark.asyncio
async def test_historical_transit_evidence_end_to_end_service():
    """Integration: Tests HistoricalRouteEvidenceService query execution against real PostgreSQL schema."""
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings

    engine = create_async_engine(settings.ASYNC_DATABASE_URI, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Fetch real plants and site from database
        from app.modules.erp.models import Plant, Site
        plants = (await session.execute(select(Plant).limit(2))).scalars().all()
        sites = (await session.execute(select(Site).limit(1))).scalars().all()

        if len(plants) >= 2 and len(sites) >= 1:
            curr_pid = plants[0].id
            cand_pid = plants[1].id
            sid = sites[0].id

            summary = await HistoricalRouteEvidenceService.get_historical_transit_evidence(
                session=session,
                site_id=sid,
                current_source_plant_id=curr_pid,
                candidate_plant_ids=[cand_pid],
                analysis_timestamp=datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc),
                historical_window_days=90,
            )

            assert summary is not None
            assert str(summary.site_id) == str(sid)
            assert str(summary.current_source_plant_id) == str(curr_pid)
            assert str(curr_pid) in summary.plant_metrics
            assert str(cand_pid) in summary.plant_metrics
            assert len(summary.comparisons) == 1
            assert summary.comparisons[0].tie_threshold_minutes == 2.0
            assert summary.data_source_attribution == "ERP_VTS_HISTORICAL_OPERATIONAL_DATA"

    await engine.dispose()


