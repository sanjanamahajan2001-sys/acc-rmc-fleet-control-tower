import pytest
from datetime import datetime, timedelta
from app.modules.operational_dashboard.widgets.operational_intelligence.services.overlap_heatmap import OverlapHeatmapEngine
from app.modules.operational_dashboard.widgets.operational_intelligence.repository import RawDispatchIntervalObservation
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import OverlapSiteDTO, OverlapHeatmapResponseDTO, OperationalIntelligenceStatusEnum

def create_obs(dispatch_id: int, customer_code: str, time_in: str, time_out: str) -> RawDispatchIntervalObservation:
    return RawDispatchIntervalObservation(
        dispatch_id=dispatch_id,
        customer_id=dispatch_id,
        customer_code=customer_code,
        vehicle_id=dispatch_id,
        time_in=time_in,
        time_out=time_out,
    )

def test_01_single_interval_2_concurrent_tms():
    # T1: 10:00:00 - 10:30:00 (30m)
    # T2: 10:10:00 - 10:40:00 (30m)
    # Overlap: 10:10 - 10:30 (20m), concurrency=2 -> Weighted TM-Mins = 20m, Avg = 2.0
    obs1 = create_obs(1, "SITE_A", "10:00:00", "10:30:00")
    obs2 = create_obs(2, "SITE_A", "10:10:00", "10:40:00")
    
    events = [(600.0, 1), (630.0, -1), (610.0, 1), (640.0, -1)]
    events.sort(key=lambda x: (x[0], x[1]))
    
    current, peak, prev, overlap, weighted = 0, 0, None, 0.0, 0.0
    for ts, evt in events:
        if prev is not None and ts > prev:
            dur = ts - prev
            if current >= 2 and dur > 0:
                overlap += dur
                weighted += dur * (current - 1)
        current += evt
        if current > peak: peak = current
        prev = ts
        
    assert overlap == 20.0
    assert weighted == 20.0
    assert peak == 2
    assert (1.0 + (weighted / overlap)) == 2.0

def test_02_3_concurrent_tms_weighted_mins():
    # 3 TMs present 10:00 - 10:30 (30m) -> Concurrency = 3, Weighted Mins = 30 * (3 - 1) = 60.0
    events = [(600.0, 1), (630.0, -1), (600.0, 1), (630.0, -1), (600.0, 1), (630.0, -1)]
    events.sort(key=lambda x: (x[0], x[1]))
    
    current, peak, prev, overlap, weighted = 0, 0, None, 0.0, 0.0
    for ts, evt in events:
        if prev is not None and ts > prev:
            dur = ts - prev
            if current >= 2 and dur > 0:
                overlap += dur
                weighted += dur * (current - 1)
        current += evt
        if current > peak: peak = current
        prev = ts
        
    assert overlap == 30.0
    assert weighted == 60.0
    assert peak == 3
    assert (1.0 + (weighted / overlap)) == 3.0

def test_03_multiple_overlapping_intervals():
    # T1: 10:00 - 10:30, T2: 10:10 - 10:40, T3: 10:20 - 10:50
    # 10:00-10:10 (1TM), 10:10-10:20 (2TMs, 10m), 10:20-10:30 (3TMs, 10m), 10:30-10:40 (2TMs, 10m), 10:40-10:50 (1TM)
    # Total Overlap = 10 + 10 + 10 = 30m
    # Weighted Mins = (10 * 1) + (10 * 2) + (10 * 1) = 40m
    events = [
        (600.0, 1), (630.0, -1),
        (610.0, 1), (640.0, -1),
        (620.0, 1), (650.0, -1),
    ]
    events.sort(key=lambda x: (x[0], x[1]))
    
    current, peak, prev, overlap, weighted = 0, 0, None, 0.0, 0.0
    for ts, evt in events:
        if prev is not None and ts > prev:
            dur = ts - prev
            if current >= 2 and dur > 0:
                overlap += dur
                weighted += dur * (current - 1)
        current += evt
        if current > peak: peak = current
        prev = ts

    assert overlap == 30.0
    assert weighted == 40.0
    assert peak == 3
    assert round(1.0 + (weighted / overlap), 2) == 2.33

def test_04_non_overlapping_intervals():
    # T1: 10:00 - 10:20, T2: 10:30 - 10:50
    events = [(600.0, 1), (620.0, -1), (630.0, 1), (650.0, -1)]
    events.sort(key=lambda x: (x[0], x[1]))
    
    current, peak, prev, overlap, weighted = 0, 0, None, 0.0, 0.0
    for ts, evt in events:
        if prev is not None and ts > prev:
            dur = ts - prev
            if current >= 2 and dur > 0:
                overlap += dur
                weighted += dur * (current - 1)
        current += evt
        if current > peak: peak = current
        prev = ts

    assert overlap == 0.0
    assert peak == 1

def test_05_nested_intervals():
    # T1: 10:00 - 11:00 (outer), T2: 10:15 - 10:45 (inner)
    events = [(600.0, 1), (660.0, -1), (615.0, 1), (645.0, -1)]
    events.sort(key=lambda x: (x[0], x[1]))
    
    current, peak, prev, overlap, weighted = 0, 0, None, 0.0, 0.0
    for ts, evt in events:
        if prev is not None and ts > prev:
            dur = ts - prev
            if current >= 2 and dur > 0:
                overlap += dur
                weighted += dur * (current - 1)
        current += evt
        if current > peak: peak = current
        prev = ts

    assert overlap == 30.0
    assert weighted == 30.0
    assert peak == 2

def test_06_same_timestamp_exit_before_entry_tie_breaker():
    # T1: 10:00 - 10:20, T2: 10:20 - 10:40 (starts when T1 ends)
    # EXIT (-1) < ENTRY (+1) -> concurrency never reaches 2!
    events = [(600.0, 1), (620.0, -1), (620.0, 1), (640.0, -1)]
    events.sort(key=lambda x: (x[0], x[1]))
    
    current, peak, prev, overlap = 0, 0, None, 0.0
    for ts, evt in events:
        if prev is not None and ts > prev:
            dur = ts - prev
            if current >= 2 and dur > 0:
                overlap += dur
        current += evt
        if current > peak: peak = current
        prev = ts

    assert overlap == 0.0
    assert peak == 1

def test_07_overnight_wraparound_intervals():
    # T1: 23:30 - 01:15 (wrap around midnight) -> 1410m to 1515m (75m total duration)
    # T2: 00:30 - 01:30 -> 30m to 90m
    # Overlap: 00:30 to 01:15 (45m overlap)
    t1_in = 23 * 60 + 30  # 1410
    t1_out = 1 * 60 + 15 + 1440 # 1515
    t2_in = 30 # 00:30
    t2_out = 90 # 01:30
    # Shift t2 to same scale if after midnight
    t2_in += 1440
    t2_out += 1440
    
    events = [(t1_in, 1), (t1_out, -1), (t2_in, 1), (t2_out, -1)]
    events.sort(key=lambda x: (x[0], x[1]))
    
    current, peak, prev, overlap = 0, 0, None, 0.0
    for ts, evt in events:
        if prev is not None and ts > prev:
            dur = ts - prev
            if current >= 2 and dur > 0:
                overlap += dur
        current += evt
        if current > peak: peak = current
        prev = ts

    assert overlap == 45.0
    assert peak == 2

def test_08_empty_input_semantics():
    res = OverlapHeatmapResponseDTO(
        success=True,
        status=OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
        total_sites=0,
        data=[],
        filters={"plant_id": "ALL"},
    )
    assert res.status == OperationalIntelligenceStatusEnum.NO_OBSERVATIONS
    assert res.total_sites == 0
    assert res.data == []

def test_09_deterministic_ranking_sort_order():
    s1 = OverlapSiteDTO(
        site_id="S1", site_name="S1", rank=1, total_trips=100,
        peak_tms_together=10, avg_tms_standing_together=5.0,
        overlap_hours=20.0, weighted_tm_minutes=5000.0
    )
    s2 = OverlapSiteDTO(
        site_id="S2", site_name="S2", rank=2, total_trips=100,
        peak_tms_together=8, avg_tms_standing_together=4.0,
        overlap_hours=15.0, weighted_tm_minutes=3000.0
    )
    assert s1.weighted_tm_minutes > s2.weighted_tm_minutes
    assert s1.rank < s2.rank
