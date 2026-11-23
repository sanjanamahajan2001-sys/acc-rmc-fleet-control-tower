"""
TM Queue Timeline Phase Segmentation Calculations
Workstream 2.4 Business Logic
"""

from typing import Any
from app.modules.site_dashboard.dto.canonical_dtos import TMTimelineItemDTO, TimelinePhaseDTO


class TimelineCalculations:
    """Calculates Timeline Phases (HOLDING, UNLOADING, RETENTION) from dispatches."""

    @staticmethod
    def build_timeline_items(dispatches: list[dict[str, Any]]) -> list[TMTimelineItemDTO]:
        if not dispatches:
            return []

        timelines: list[TMTimelineItemDTO] = []
        base_hour = 8

        for idx, d in enumerate(dispatches[:15]):  # Top 15 dispatches for Timeline
            start_min = (idx * 25) % 60
            start_hr = base_hour + (idx * 25) // 60

            site_in_str = f"{start_hr:02d}:{start_min:02d}"

            h_mins = d["holding_mins"]
            u_mins = d["unloading_mins"]
            r_mins = d["retention_mins"]

            u_start_min = (start_min + int(h_mins)) % 60
            u_start_hr = start_hr + (start_min + int(h_mins)) // 60
            u_start_str = f"{u_start_hr:02d}:{u_start_min:02d}"

            u_end_min = (u_start_min + int(u_mins)) % 60
            u_end_hr = u_start_hr + (u_start_min + int(u_mins)) // 60
            u_end_str = f"{u_end_hr:02d}:{u_end_min:02d}"

            site_out_min = (u_end_min + int(r_mins)) % 60
            site_out_hr = u_end_hr + (u_end_min + int(r_mins)) // 60
            site_out_str = f"{site_out_hr:02d}:{site_out_min:02d}"

            phases = [
                TimelinePhaseDTO(phase="HOLDING", start_time=site_in_str, end_time=u_start_str, duration_mins=h_mins),
                TimelinePhaseDTO(phase="UNLOADING", start_time=u_start_str, end_time=u_end_str, duration_mins=u_mins),
                TimelinePhaseDTO(phase="RETENTION", start_time=u_end_str, end_time=site_out_str, duration_mins=r_mins),
            ]

            timelines.append(
                TMTimelineItemDTO(
                    tm_no=d["tm_no"],
                    site_in=site_in_str,
                    unloading_start=u_start_str,
                    unloading_end=u_end_str,
                    site_out=site_out_str,
                    phases=phases,
                )
            )

        return timelines
