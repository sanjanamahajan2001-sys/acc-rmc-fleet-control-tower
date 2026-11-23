from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reports.schemas.report_schemas import ReportStatus
from app.modules.reports.schemas.operational_intelligence_canonical import (
    CanonicalOperationalIntelligenceReport,
    ReportMetadataDTO,
    OperationalIntelligenceKPISummary,
    SiteReadinessRecord,
)
from app.modules.operational_dashboard.widgets.operational_intelligence.services.site_readiness import SiteReadinessEngine


from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_intelligence.services.health_service import OperationalHealthService
from app.modules.operational_intelligence.services.alert_intelligence_service import OperationalAlertIntelligenceService
from app.modules.operational_intelligence.services.decision_recommendation_service import OperationalDecisionRecommendationService
from app.modules.operational_intelligence.services.financial_exposure_service import OperationalFinancialExposureService
from app.modules.operational_intelligence.services.fleet_efficiency_service import OperationalFleetEfficiencyService
from app.modules.operational_intelligence.services.cost_exposure_service import OperationalCostExposureService


class OperationalIntelligenceReportHandler:
    """Handler for assembling canonical Operational Intelligence reports from all 6 UI section engines."""

    async def build_canonical_report(
        self,
        session: AsyncSession,
        execution_id: str,
        requested_scope: Dict[str, Any],
        effective_scope: Dict[str, Any],
        scope_fingerprint: str,
        requested_by: str = "SYSTEM"
    ) -> CanonicalOperationalIntelligenceReport:
        now_str = datetime.now(timezone.utc).isoformat()
        metadata = ReportMetadataDTO(
            execution_id=execution_id,
            report_id="operational_intelligence",
            report_name="Operational Intelligence Report",
            generated_at=now_str,
            requested_by=requested_by
        )

        params = DashboardFilterParams(
            plant_id=effective_scope.get("plant_id", "ALL"),
            customer_id=effective_scope.get("customer_id", "ALL"),
            operation_date=effective_scope.get("operation_date", "2026-08-05"),
            shift=effective_scope.get("shift", "ALL"),
            dataset_type=effective_scope.get("dataset_type", "ALL")
        )

        health_dict = {}
        alerts_dict = {}
        recommendations_dict = {}
        financial_dict = {}
        efficiency_dict = {}
        cost_dict = {}

        import logging
        logger = logging.getLogger(__name__)

        try:
            h_dto = await OperationalHealthService.get_operational_health(session, params)
            health_dict = h_dto.model_dump()
        except Exception as e:
            logger.error(f"Error in OperationalHealthService: {e}", exc_info=True)

        try:
            a_dto = await OperationalAlertIntelligenceService.get_alert_intelligence(session, params)
            alerts_dict = a_dto.model_dump()
        except Exception as e:
            logger.error(f"Error in OperationalAlertIntelligenceService: {e}", exc_info=True)

        try:
            r_dto = await OperationalDecisionRecommendationService.get_decision_recommendations(session, params)
            recommendations_dict = r_dto.model_dump()
        except Exception as e:
            logger.error(f"Error in OperationalDecisionRecommendationService: {e}", exc_info=True)

        try:
            f_dto = await OperationalFinancialExposureService.get_financial_exposure(session, params)
            financial_dict = f_dto.model_dump()
        except Exception as e:
            logger.error(f"Error in OperationalFinancialExposureService: {e}", exc_info=True)

        try:
            e_dto = await OperationalFleetEfficiencyService.get_fleet_efficiency(session, params)
            efficiency_dict = e_dto.model_dump()
        except Exception as e:
            logger.error(f"Error in OperationalFleetEfficiencyService: {e}", exc_info=True)

        try:
            c_dto = await OperationalCostExposureService.get_cost_exposure(session, params)
            cost_dict = c_dto.model_dump()
        except Exception as e:
            logger.error(f"Error in OperationalCostExposureService: {e}", exc_info=True)


        try:
            readiness_dto = await SiteReadinessEngine.get_site_readiness(session, effective_scope)
            sites = readiness_dto.data

            records = [
                SiteReadinessRecord(
                    rank=s.rank,
                    site_id=s.site_id,
                    site_name=s.site_name,
                    total_trips=s.total_trips,
                    swi_site=s.swi_site,
                    dpi_site=s.dpi_site,
                    fui_site=s.fui_site,
                    sri_score=s.sri_score,
                    grade=s.grade.value if hasattr(s.grade, "value") else str(s.grade)
                )
                for s in sites
            ]

            total_sites = len(records)
            total_trips = sum(r.total_trips for r in records)
            avg_sri = round(sum(r.sri_score for r in records) / total_sites, 1) if total_sites > 0 else 0.0
            avg_swi = round(sum(r.swi_site for r in records) / total_sites, 1) if total_sites > 0 else 0.0
            avg_dpi = round(sum(r.dpi_site for r in records) / total_sites, 1) if total_sites > 0 else 0.0
            avg_fui = round(sum(r.fui_site for r in records) / total_sites, 1) if total_sites > 0 else 0.0
            grade_a_cnt = sum(1 for r in records if "GRADE_A" in r.grade)

            kpis = OperationalIntelligenceKPISummary(
                total_sites_evaluated=total_sites,
                total_trips=total_trips,
                avg_sri_score=avg_sri,
                avg_swi_site=avg_swi,
                avg_dpi_site=avg_dpi,
                avg_fui_site=avg_fui,
                grade_a_sites_count=grade_a_cnt
            )

            status = ReportStatus.COMPLETED

            return CanonicalOperationalIntelligenceReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=status,
                record_count=total_sites,
                kpis=kpis,
                health=health_dict,
                alerts=alerts_dict,
                recommendations=recommendations_dict,
                financial_exposure=financial_dict,
                efficiency=efficiency_dict,
                cost_exposure=cost_dict,
                records=records,
                exceptions=[]
            )
        except Exception:
            return CanonicalOperationalIntelligenceReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=ReportStatus.NO_DATA,
                record_count=0,
                kpis=OperationalIntelligenceKPISummary(),
                records=[],
                exceptions=[]
            )

