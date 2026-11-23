from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import (
    SiteReadinessDTO,
    SiteReadinessResponseDTO,
    OperationalIntelligenceStatusEnum,
    OperationalGradeEnum,
)
from app.modules.operational_dashboard.widgets.operational_intelligence.repository import (
    OperationalIntelligenceRepository,
    RawSiteReadinessObservation,
)


class SiteReadinessEngine:
    """Business Engine ONLY for WS-03.2 Site Readiness Index (SRI)."""

    @classmethod
    def calculate_swi_site(cls, obs: RawSiteReadinessObservation) -> float:
        """Calculates SWI: max(0.0, 100.0 - (total_holding_penalty_mins / total_trips * 2.0))."""
        if obs.total_trips <= 0:
            return 100.0
        avg_penalty = obs.holding_penalty_mins / obs.total_trips
        raw_swi = 100.0 - (avg_penalty * 2.0)
        return max(0.0, float(raw_swi))

    @classmethod
    def calculate_dpi_site(cls, obs: RawSiteReadinessObservation) -> float:
        """Calculates DPI: (compliant_transit_trips / total_trips) * 100.0."""
        if obs.total_trips <= 0:
            return 100.0
        raw_dpi = (obs.compliant_transit_trips / obs.total_trips) * 100.0
        return max(0.0, min(100.0, float(raw_dpi)))

    @classmethod
    def calculate_fui_site(cls, obs: RawSiteReadinessObservation) -> float:
        """Calculates FUI: min(100.0, (active_tms / plant_fleet_denominator) * 100.0)."""
        if obs.plant_fleet_denominator <= 0:
            return 0.0
        raw_fui = (obs.active_tms / obs.plant_fleet_denominator) * 100.0
        return max(0.0, min(100.0, float(raw_fui)))

    @classmethod
    def calculate_sri_score(cls, swi: float, dpi: float, fui: float) -> float:
        """Calculates Composite SRI: (0.40 * SWI) + (0.35 * DPI) + (0.25 * FUI)."""
        score = (0.40 * swi) + (0.35 * dpi) + (0.25 * fui)
        return max(0.0, min(100.0, float(score)))

    @classmethod
    def classify_grade(cls, sri_score: float) -> OperationalGradeEnum:
        """Classifies SRI score into Operational Grade (GRADE_A, GRADE_B, GRADE_C, GRADE_D)."""
        if sri_score >= 80.0:
            return OperationalGradeEnum.GRADE_A
        elif sri_score >= 70.0:
            return OperationalGradeEnum.GRADE_B
        elif sri_score >= 50.0:
            return OperationalGradeEnum.GRADE_C
        else:
            return OperationalGradeEnum.GRADE_D

    @classmethod
    async def get_site_readiness(
        cls, session: AsyncSession, filters: Dict[str, Any], limit: int | None = None
    ) -> SiteReadinessResponseDTO:
        """Executes site readiness evaluation, scoring, grading, and ranking."""
        raw_obs = await OperationalIntelligenceRepository.get_site_readiness_observations(
            session, filters
        )

        if not raw_obs:
            return SiteReadinessResponseDTO(
                success=True,
                status=OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
                total_sites=0,
                data=[],
                filters=filters,
            )

        calculated_sites: List[SiteReadinessDTO] = []
        for obs in raw_obs:
            swi = cls.calculate_swi_site(obs)
            dpi = cls.calculate_dpi_site(obs)
            fui = cls.calculate_fui_site(obs)
            sri = cls.calculate_sri_score(swi, dpi, fui)
            grade = cls.classify_grade(sri)

            calculated_sites.append(
                SiteReadinessDTO(
                    site_id=obs.site_code,
                    site_name=obs.site_name,
                    rank=0,  # Computed after sorting
                    total_trips=obs.total_trips,
                    swi_site=round(swi, 1),
                    dpi_site=round(dpi, 1),
                    fui_site=round(fui, 1),
                    sri_score=round(sri, 1),
                    grade=grade,
                )
            )

        # Deterministic Ranking: ORDER BY sri_score ASC, total_trips DESC, site_id ASC
        sorted_sites = sorted(
            calculated_sites,
            key=lambda x: (x.sri_score, -x.total_trips, x.site_id),
        )

        # Assign 1-indexed ranks
        final_sites: List[SiteReadinessDTO] = []
        subset = sorted_sites[:limit] if limit is not None else sorted_sites
        for idx, site in enumerate(subset, start=1):
            site_dict = site.model_dump()
            site_dict["rank"] = idx
            final_sites.append(SiteReadinessDTO(**site_dict))

        return SiteReadinessResponseDTO(
            success=True,
            status=OperationalIntelligenceStatusEnum.AVAILABLE,
            total_sites=len(final_sites),
            data=final_sites,
            filters=filters,
        )
