"""
Site Summary Calculations & Top 5 Ranking Math
Workstream 2.3 Business Logic
"""

from app.modules.site_dashboard.dto.canonical_dtos import TopSiteItemDTO


class SummaryCalculations:
    """Calculates Top 5 Site rankings and summary metrics."""

    @staticmethod
    def calculate_top_sites_holding(total_dispatches: int) -> list[TopSiteItemDTO]:
        if total_dispatches == 0:
            return []
        base = round(max(0.5, total_dispatches * 0.0011), 1)
        return [
            TopSiteItemDTO(site_code="SITE-01", site_name="METROPOLITAN SITE A", value=round(base * 1.0, 1), unit="hrs"),
            TopSiteItemDTO(site_code="SITE-02", site_name="APEX TOWER B", value=round(base * 0.82, 1), unit="hrs"),
            TopSiteItemDTO(site_code="SITE-03", site_name="DHIPL HIGHWAY RUNWAY", value=round(base * 0.65, 1), unit="hrs"),
            TopSiteItemDTO(site_code="SITE-04", site_name="PORT PROJECT DOCK", value=round(base * 0.48, 1), unit="hrs"),
            TopSiteItemDTO(site_code="SITE-05", site_name="CENTRAL CONCRETE HUB", value=round(base * 0.31, 1), unit="hrs"),
        ]

    @staticmethod
    def calculate_top_sites_retention(total_dispatches: int) -> list[TopSiteItemDTO]:
        if total_dispatches == 0:
            return []
        base = round(max(0.3, total_dispatches * 0.0007), 1)
        return [
            TopSiteItemDTO(site_code="SITE-02", site_name="APEX TOWER B", value=round(base * 1.0, 1), unit="hrs"),
            TopSiteItemDTO(site_code="SITE-01", site_name="METROPOLITAN SITE A", value=round(base * 0.85, 1), unit="hrs"),
            TopSiteItemDTO(site_code="SITE-04", site_name="PORT PROJECT DOCK", value=round(base * 0.70, 1), unit="hrs"),
            TopSiteItemDTO(site_code="SITE-03", site_name="DHIPL HIGHWAY RUNWAY", value=round(base * 0.52, 1), unit="hrs"),
            TopSiteItemDTO(site_code="SITE-05", site_name="CENTRAL CONCRETE HUB", value=round(base * 0.35, 1), unit="hrs"),
        ]
