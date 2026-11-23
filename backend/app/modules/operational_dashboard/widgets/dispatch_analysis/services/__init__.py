"""
WS-ROUT-1: ERP T1 Transit Statistics Engine & Cleansing Pipeline Service
Frozen blueprint v1.2.1 compliant.
"""

import math
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.erp.models import Plant, Site
from app.modules.operational_dashboard.widgets.dispatch_analysis.repository import HistoricalRouteRepository
from app.modules.operational_dashboard.widgets.dispatch_analysis.dtos import (
    HistoricalConfidenceLevel,
    HistoricalWinnerOutcome,
    CleansedT1TripRecord,
    PlantSiteHistoricalMetricDTO,
    HistoricalComparisonPairDTO,
    HistoricalTransitEvidenceSummaryDTO,
    RouteAnalysisMode,
    TrafficSpeedState,
    SpeedReadingIntervalDTO,
    RouteWaypointDTO,
    GoogleCandidateMatrixItemDTO,
    GoogleDetailedRouteDTO,
    GoogleRouteEvidenceSummaryDTO,
    SynthesisDecisionOutcome,
    SynthesisCaseCategory,
    SynthesisCandidateComparisonDTO,
    RouteAnalysisSynthesisResultDTO,
)
from app.modules.operational_dashboard.widgets.dispatch_analysis.services.google_routes_client import (
    GoogleRoutesClient,
    GoogleRoutesProvider,
    GoogleRoutesCircuitBreaker,
    GoogleRoutesCache,
    IRouteProvider,
)
from app.modules.operational_dashboard.widgets.dispatch_analysis.services.synthesis_engine import (
    RouteAnalysisSynthesisEngine,
    DeterministicExplanationGenerator,
)


class HistoricalCleansingPipeline:
    """
    Deterministic multi-stage quality and cleansing pipeline for raw ERP/VTS dispatch rows.
    Enforces all frozen blueprint v1.2.1 rules:
      Stage 1: Completion Requirement (status == 'COMPLETED')
      Stage 2: Non-null plant_out / time_out and site_in / time_in
      Stage 3: Plant/Site Foreign Key and Entity Master Validity
      Stage 4: T1 Duration Calculation in Minutes
      Stage 5: T1 Physical Bounds (5.0 <= T1 <= 300.0 minutes)
      Stage 6: Distance Bounds (0.5 <= distance_km <= 150.0 km)
      Stage 7: Deduplication by trip_number / dispatch_number lineage
      Stage 8: Rolling Window Filter (T_analysis - 90 days <= dispatch_date <= T_analysis)
    """

    MIN_T1_MINUTES: float = 5.0
    MAX_T1_MINUTES: float = 300.0
    MIN_DISTANCE_KM: float = 0.5
    MAX_DISTANCE_KM: float = 150.0

    @classmethod
    def parse_time_component(cls, disp_date: datetime, time_val: Any) -> Optional[datetime]:
        """
        Anchors time string (HH:MM:SS or HH:MM) or datetime to dispatch_date in UTC.
        """
        if time_val is None:
            return None
        if isinstance(time_val, datetime):
            if time_val.tzinfo is None:
                return time_val.replace(tzinfo=timezone.utc)
            return time_val

        try:
            time_str = str(time_val).strip()
            parts = time_str.split(":")
            if len(parts) < 2:
                return None
            h = int(parts[0])
            m = int(parts[1])
            s = int(parts[2]) if len(parts) > 2 else 0
            base_d = disp_date.date() if hasattr(disp_date, "date") else disp_date
            return datetime(base_d.year, base_d.month, base_d.day, h, m, s, tzinfo=timezone.utc)
        except Exception:
            return None

    @classmethod
    def calculate_t1_minutes(
        cls,
        raw_t1_mins: Optional[float],
        plant_out_dt: Optional[datetime],
        site_in_dt: Optional[datetime],
    ) -> Optional[float]:
        """
        Calculates authoritative T1 Transit Duration = (Site In - Plant Out) in minutes.
        Strict contract: Derived from authoritative timestamps.
        If timestamps are present, always computes (Site In - Plant Out).
        Only falls back to raw_t1_mins if timestamps are absent or unparseable.
        """
        if plant_out_dt is not None and site_in_dt is not None:
            delta_secs = (site_in_dt - plant_out_dt).total_seconds()
            if delta_secs < 0:
                # Overnight trip adjustment if within 24h
                delta_secs += 86400.0
            return round(delta_secs / 60.0, 2)

        if raw_t1_mins is not None and not math.isnan(raw_t1_mins):
            return float(raw_t1_mins)

        return None

    @classmethod
    def cleanse_and_filter_records(
        cls,
        raw_rows: Sequence[Dict[str, Any]],
        window_start: datetime,
        window_end: datetime,
    ) -> List[CleansedT1TripRecord]:
        """
        Executes deterministic multi-stage cleansing pass across candidate rows.
        """
        cleansed: List[CleansedT1TripRecord] = []
        seen_keys: set = set()

        for row in raw_rows:
            # Stage 1: Completion filter
            status = str(row.get("status", "")).upper()
            if status != "COMPLETED":
                continue

            # Stage 2 & 3: Master Data IDs and Timestamps
            plant_id = row.get("plant_id")
            site_id = row.get("site_id")
            disp_id = row.get("dispatch_id")
            disp_no = row.get("dispatch_number")
            if not plant_id or not site_id or not disp_id or not disp_no:
                continue

            disp_date = row.get("dispatch_date")
            if not disp_date:
                continue
            if isinstance(disp_date, datetime):
                if disp_date.tzinfo is None:
                    disp_date_utc = disp_date.replace(tzinfo=timezone.utc)
                else:
                    disp_date_utc = disp_date
            else:
                try:
                    disp_date_utc = datetime.fromisoformat(str(disp_date)).replace(tzinfo=timezone.utc)
                except Exception:
                    continue

            # Stage 8: Rolling Window Check
            if disp_date_utc < window_start or disp_date_utc > window_end:
                continue

            time_out_raw = row.get("time_out")
            time_in_raw = row.get("time_in") or row.get("date_in")
            if not time_out_raw or not time_in_raw:
                continue

            plant_out_dt = cls.parse_time_component(disp_date_utc, time_out_raw)
            site_in_dt = cls.parse_time_component(disp_date_utc, time_in_raw)
            if not plant_out_dt or not site_in_dt:
                continue

            # Stage 4: T1 Duration Calculation
            raw_t1 = row.get("t1_transit_mins")
            t1_val = cls.calculate_t1_minutes(raw_t1, plant_out_dt, site_in_dt)
            if t1_val is None:
                continue

            # Stage 5: T1 Physical Bounds (5.0 <= T1 <= 300.0)
            if t1_val < cls.MIN_T1_MINUTES or t1_val > cls.MAX_T1_MINUTES:
                continue

            # Stage 6: Distance Bounds (0.5 <= distance_km <= 150.0)
            dist_raw = row.get("distance_km")
            try:
                dist_val = float(dist_raw) if dist_raw is not None else None
            except (ValueError, TypeError):
                dist_val = None

            if dist_val is None or dist_val < cls.MIN_DISTANCE_KM or dist_val > cls.MAX_DISTANCE_KM:
                continue

            # Stage 7: Deduplication by trip_number / dispatch_number lineage
            trip_no = row.get("trip_number") or str(disp_no)
            dedup_key = (str(plant_id), str(site_id), str(trip_no))
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            cleansed.append(
                CleansedT1TripRecord(
                    dispatch_id=str(disp_id),
                    dispatch_number=str(disp_no),
                    trip_number=str(trip_no),
                    plant_id=str(plant_id),
                    plant_code=str(row.get("plant_code") or ""),
                    site_id=str(site_id),
                    site_code=str(row.get("site_code") or ""),
                    dispatch_date=disp_date_utc.isoformat(),
                    plant_out_time=plant_out_dt.isoformat(),
                    site_in_time=site_in_dt.isoformat(),
                    t1_transit_mins=round(t1_val, 2),
                    distance_km=round(dist_val, 2),
                    is_generated=bool(row.get("is_generated", False)),
                    source_lineage=row.get("source_lineage"),
                )
            )

        return cleansed


class HistoricalRouteEvidenceService:
    """
    Authoritative Historical T1 Transit Statistics Calculation Service (WS-ROUT-1).
    Frozen Blueprint v1.2.1 compliant.
    """

    DEFAULT_HISTORICAL_WINDOW_DAYS: int = 90
    MIN_HISTORICAL_SAMPLE_COUNT: int = 5
    HIGH_CONFIDENCE_SAMPLE_MIN: int = 15
    HIGH_CONFIDENCE_IQR_MAX_MINS: float = 20.0
    HISTORICAL_TIE_THRESHOLD_MINS: float = 2.0

    @classmethod
    def calculate_percentiles(cls, sorted_values: List[float]) -> Tuple[float, float, float, float]:
        """
        Computes mathematically exact p25, p50 (median), p75, and IQR = p75 - p25.
        Uses standard nearest-rank / linear interpolation (R-7 / NumPy / PostgreSQL continuous percentile equivalent).
        """
        n = len(sorted_values)
        if n == 0:
            return (0.0, 0.0, 0.0, 0.0)
        if n == 1:
            val = round(sorted_values[0], 2)
            return (val, val, val, 0.0)

        def get_p(p: float) -> float:
            k = (n - 1) * p
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return sorted_values[int(k)]
            d0 = sorted_values[int(f)] * (c - k)
            d1 = sorted_values[int(c)] * (k - f)
            return d0 + d1

        p25 = round(get_p(0.25), 2)
        p50 = round(get_p(0.50), 2)
        p75 = round(get_p(0.75), 2)
        iqr = round(p75 - p25, 2)
        return (p25, p50, p75, iqr)

    @classmethod
    def classify_confidence(cls, sample_count: int, iqr: float) -> HistoricalConfidenceLevel:
        """
        Classifies historical confidence level deterministically:
        - HIGH: N >= 15 and IQR <= 20.0 minutes
        - MODERATE: 5 <= N < 15
        - LOW: 1 <= N < 5
        - NONE: N == 0
        """
        if sample_count == 0:
            return HistoricalConfidenceLevel.NONE
        if sample_count >= cls.HIGH_CONFIDENCE_SAMPLE_MIN and iqr <= cls.HIGH_CONFIDENCE_IQR_MAX_MINS:
            return HistoricalConfidenceLevel.HIGH
        if sample_count >= cls.MIN_HISTORICAL_SAMPLE_COUNT:
            return HistoricalConfidenceLevel.MODERATE
        return HistoricalConfidenceLevel.LOW

    @classmethod
    def evaluate_winner(
        cls,
        current_p50: Optional[float],
        current_sample_count: int,
        candidate_p50: Optional[float],
        candidate_sample_count: int,
        tie_threshold: float = 2.0,
    ) -> Tuple[HistoricalWinnerOutcome, Optional[float], str]:
        """
        Evaluates historical winner according to Blueprint Section 4.A & Tie Rule:
        delta_hist = p50(current) - p50(candidate)
        - delta_hist <= -2.0m -> CURRENT_PLANT_FASTER
        - delta_hist >= +2.0m -> CANDIDATE_PLANT_FASTER
        - abs(delta_hist) < 2.0m -> NO_MEANINGFUL_HISTORICAL_DIFFERENCE
        - Sample count < 5 -> INSUFFICIENT_EVIDENCE
        """
        if (
            current_p50 is None
            or candidate_p50 is None
            or current_sample_count < cls.MIN_HISTORICAL_SAMPLE_COUNT
            or candidate_sample_count < cls.MIN_HISTORICAL_SAMPLE_COUNT
        ):
            return (
                HistoricalWinnerOutcome.INSUFFICIENT_EVIDENCE,
                None,
                "Insufficient historical sample count (< 5 completed trips) on one or both candidate plants.",
            )

        delta_hist = round(current_p50 - candidate_p50, 2)

        if delta_hist <= -tie_threshold:
            return (
                HistoricalWinnerOutcome.CURRENT_PLANT_FASTER,
                delta_hist,
                f"Current plant is historically faster by {abs(delta_hist)} mins (p50: {current_p50}m vs {candidate_p50}m).",
            )
        elif delta_hist >= tie_threshold:
            return (
                HistoricalWinnerOutcome.CANDIDATE_PLANT_FASTER,
                delta_hist,
                f"Candidate plant is historically faster by {abs(delta_hist)} mins (p50: {candidate_p50}m vs {current_p50}m).",
            )
        else:
            return (
                HistoricalWinnerOutcome.NO_MEANINGFUL_HISTORICAL_DIFFERENCE,
                delta_hist,
                f"No meaningful historical difference (delta: {abs(delta_hist)}m < {tie_threshold}m threshold; p50: {current_p50}m vs {candidate_p50}m).",
            )

    @classmethod
    async def get_historical_transit_evidence(
        cls,
        session: AsyncSession,
        site_id: Any,
        current_source_plant_id: Any,
        candidate_plant_ids: List[Any],
        analysis_timestamp: Optional[datetime] = None,
        historical_window_days: int = 90,
    ) -> HistoricalTransitEvidenceSummaryDTO:
        """
        Authoritative entry point for WS-ROUT-1.
        Calculates and returns complete historical T1 transit statistics and comparison pairs.
        """
        if analysis_timestamp is None:
            analysis_ts = datetime.now(timezone.utc)
        elif analysis_timestamp.tzinfo is None:
            analysis_ts = analysis_timestamp.replace(tzinfo=timezone.utc)
        else:
            analysis_ts = analysis_timestamp

        window_start = analysis_ts - timedelta(days=historical_window_days)
        window_end = analysis_ts

        # Combine all distinct plant IDs to evaluate
        all_plant_ids = list(dict.fromkeys([current_source_plant_id] + candidate_plant_ids))

        # Query authoritative site and plant metadata
        site_stmt = select(Site).where(Site.id == site_id)
        site_obj = (await session.execute(site_stmt)).scalars().first()
        site_code = site_obj.code if site_obj else "UNKNOWN_SITE"
        site_name = site_obj.name if site_obj else "Unknown Delivery Site"

        plant_stmt = select(Plant).where(Plant.id.in_(all_plant_ids))
        plants = (await session.execute(plant_stmt)).scalars().all()
        plant_map = {str(p.id): p for p in plants}

        curr_plant_obj = plant_map.get(str(current_source_plant_id))
        curr_plant_code = curr_plant_obj.code if curr_plant_obj else "CURRENT_PLANT"

        # Fetch candidate dispatches from repository
        raw_dispatches = await HistoricalRouteRepository.get_raw_candidate_dispatches(
            session=session,
            site_id=site_id,
            plant_ids=all_plant_ids,
            window_start=window_start,
            window_end=window_end,
        )

        # Run Stage 1-8 deterministic cleansing pipeline
        cleansed_records = HistoricalCleansingPipeline.cleanse_and_filter_records(
            raw_rows=raw_dispatches,
            window_start=window_start,
            window_end=window_end,
        )

        # Group cleansed trips by plant_id
        trips_by_plant: Dict[str, List[CleansedT1TripRecord]] = {str(pid): [] for pid in all_plant_ids}
        for rec in cleansed_records:
            if rec.plant_id in trips_by_plant:
                trips_by_plant[rec.plant_id].append(rec)

        # Calculate percentile metrics per plant
        plant_metrics: Dict[str, PlantSiteHistoricalMetricDTO] = {}
        for pid_str in [str(pid) for pid in all_plant_ids]:
            p_trips = trips_by_plant.get(pid_str, [])
            p_obj = plant_map.get(pid_str)
            p_code = p_obj.code if p_obj else pid_str
            p_name = p_obj.name if p_obj else f"Plant {p_code}"

            sample_cnt = len(p_trips)
            if sample_cnt == 0:
                plant_metrics[pid_str] = PlantSiteHistoricalMetricDTO(
                    plant_id=pid_str,
                    plant_code=p_code,
                    plant_name=p_name,
                    site_id=str(site_id),
                    site_code=site_code,
                    site_name=site_name,
                    sample_count=0,
                    confidence_level=HistoricalConfidenceLevel.NONE,
                    is_sufficient_sample=False,
                    cleansed_trip_ids=[],
                )
                continue

            t1_durations = sorted([r.t1_transit_mins for r in p_trips])
            p25, p50, p75, iqr = cls.calculate_percentiles(t1_durations)
            confidence = cls.classify_confidence(sample_cnt, iqr)
            is_sufficient = sample_cnt >= cls.MIN_HISTORICAL_SAMPLE_COUNT

            trip_dates = sorted([r.dispatch_date for r in p_trips])

            plant_metrics[pid_str] = PlantSiteHistoricalMetricDTO(
                plant_id=pid_str,
                plant_code=p_code,
                plant_name=p_name,
                site_id=str(site_id),
                site_code=site_code,
                site_name=site_name,
                sample_count=sample_cnt,
                p25_minutes=p25,
                p50_minutes=p50,
                p75_minutes=p75,
                iqr_minutes=iqr,
                min_minutes=round(min(t1_durations), 2),
                max_minutes=round(max(t1_durations), 2),
                mean_minutes=round(sum(t1_durations) / sample_cnt, 2),
                confidence_level=confidence,
                is_sufficient_sample=is_sufficient,
                earliest_trip_date=trip_dates[0] if trip_dates else None,
                latest_trip_date=trip_dates[-1] if trip_dates else None,
                cleansed_trip_ids=[r.dispatch_id for r in p_trips],
            )

        # Build comparison pairs between Current Plant and each Alternative Candidate Plant
        curr_metric = plant_metrics.get(str(current_source_plant_id))
        curr_p50 = curr_metric.p50_minutes if curr_metric else None
        curr_sample_cnt = curr_metric.sample_count if curr_metric else 0

        comparisons: List[HistoricalComparisonPairDTO] = []
        overall_winner: Optional[HistoricalWinnerOutcome] = None
        overall_winner_pid: Optional[str] = None
        overall_winner_pcode: Optional[str] = None

        alt_plant_ids = [pid for pid in candidate_plant_ids if str(pid) != str(current_source_plant_id)]

        for alt_pid in alt_plant_ids:
            alt_pid_str = str(alt_pid)
            alt_metric = plant_metrics.get(alt_pid_str)
            alt_p50 = alt_metric.p50_minutes if alt_metric else None
            alt_sample_cnt = alt_metric.sample_count if alt_metric else 0
            alt_code = alt_metric.plant_code if alt_metric else alt_pid_str

            winner_status, delta_hist, expl = cls.evaluate_winner(
                current_p50=curr_p50,
                current_sample_count=curr_sample_cnt,
                candidate_p50=alt_p50,
                candidate_sample_count=alt_sample_cnt,
                tie_threshold=cls.HISTORICAL_TIE_THRESHOLD_MINS,
            )

            winner_id = None
            winner_code = None
            if winner_status == HistoricalWinnerOutcome.CURRENT_PLANT_FASTER:
                winner_id = str(current_source_plant_id)
                winner_code = curr_plant_code
            elif winner_status == HistoricalWinnerOutcome.CANDIDATE_PLANT_FASTER:
                winner_id = alt_pid_str
                winner_code = alt_code

            comparisons.append(
                HistoricalComparisonPairDTO(
                    current_plant_id=str(current_source_plant_id),
                    current_plant_code=curr_plant_code,
                    candidate_plant_id=alt_pid_str,
                    candidate_plant_code=alt_code,
                    site_id=str(site_id),
                    site_code=site_code,
                    current_p50_minutes=curr_p50,
                    candidate_p50_minutes=alt_p50,
                    delta_hist_minutes=delta_hist,
                    historical_winner_status=winner_status,
                    winner_plant_id=winner_id,
                    winner_plant_code=winner_code,
                    tie_threshold_minutes=cls.HISTORICAL_TIE_THRESHOLD_MINS,
                    explanation=expl,
                )
            )

            # Record overall winner if exactly one alternative is being evaluated or candidate is faster
            if overall_winner is None:
                overall_winner = winner_status
                overall_winner_pid = winner_id
                overall_winner_pcode = winner_code

        is_overall_sufficient = (
            curr_metric.is_sufficient_sample
            if curr_metric
            else False
        )

        return HistoricalTransitEvidenceSummaryDTO(
            site_id=str(site_id),
            site_code=site_code,
            site_name=site_name,
            current_source_plant_id=str(current_source_plant_id),
            current_source_plant_code=curr_plant_code,
            analysis_timestamp=analysis_ts.isoformat(),
            historical_window_days=historical_window_days,
            window_start_date=window_start.isoformat(),
            window_end_date=window_end.isoformat(),
            plant_metrics=plant_metrics,
            comparisons=comparisons,
            overall_historical_winner=overall_winner,
            overall_winner_plant_id=overall_winner_pid,
            overall_winner_plant_code=overall_winner_pcode,
            is_overall_sufficient=is_overall_sufficient,
            data_source_attribution="ERP_VTS_HISTORICAL_OPERATIONAL_DATA",
        )
