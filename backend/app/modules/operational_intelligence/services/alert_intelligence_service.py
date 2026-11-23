"""
WS-09 Section 02 Operational Alert Intelligence Backend Service
Consumes WS-07 OperationalAlertRepository and AlertService to assemble Section 02 response.
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_dashboard.context.service import OperationalContextService
from app.modules.operational_dashboard.widgets.alerts.repository import OperationalAlertRepository
from app.modules.operational_intelligence.schemas.alert_intelligence_dtos import (
    AlertSummaryCountsDTO,
    AlertSeverityDistributionItemDTO,
    AlertCategoryDistributionItemDTO,
    AlertConcentrationItemDTO,
    PriorityAlertItemDTO,
    OperationalAlertIntelligenceResponseDTO,
)


class OperationalAlertIntelligenceService:
    """
    Canonical Service for WS-09 Section 02 Operational Alert Intelligence.
    Consumes authoritative WS-07 alert models and repository aggregations.
    """

    @classmethod
    async def get_alert_intelligence(
        cls,
        session: AsyncSession,
        params: DashboardFilterParams,
    ) -> OperationalAlertIntelligenceResponseDTO:
        # 1. Resolve shell context & active dataset ID
        shell_context = await OperationalContextService.get_shell_context(session, params)
        context_env = shell_context.context
        meta = shell_context.metadata
        total_dispatches = meta.get("total_dispatches", 0)

        effective_plant = params.plant_id or "ALL"
        effective_customer = params.customer_id or "ALL"
        effective_dataset = params.dataset_id or context_env.dataset_id or "DS-20260805-001"

        # 2. Fetch summary counts from WS-07 OperationalAlertRepository
        summary_raw = await OperationalAlertRepository.get_summary_counts(
            session=session,
            plant_id=effective_plant,
            customer_id=effective_customer,
            dataset_id=effective_dataset,
        )

        critical_cnt = summary_raw.get("active_critical_count", summary_raw.get("critical_count", 0))
        warning_cnt = summary_raw.get("active_warning_count", summary_raw.get("warning_count", 0))
        info_cnt = summary_raw.get("active_info_count", summary_raw.get("info_count", 0))
        open_cnt = summary_raw.get("open_count", 0)
        ack_cnt = summary_raw.get("acknowledged_count", 0)
        total_active = open_cnt + ack_cnt

        summary_dto = AlertSummaryCountsDTO(
            total_active=total_active,
            open_count=open_cnt,
            acknowledged_count=ack_cnt,
            critical_count=critical_cnt,
            warning_count=warning_cnt,
            info_count=info_cnt,
        )

        # Handle 0 / No Records condition
        if total_active == 0 and total_dispatches == 0:
            return OperationalAlertIntelligenceResponseDTO(
                summary=summary_dto,
                severity_distribution=[],
                top_categories=[],
                plant_concentration=[],
                customer_concentration=[],
                priority_alerts=[],
                calculation_status="NO_RECORDS",
                calculation_notes="No active operational alerts or dispatches found under the active filter context.",
            )

        # 3. Severity Distribution
        sev_dist: List[AlertSeverityDistributionItemDTO] = []
        if total_active > 0:
            sev_dist = [
                AlertSeverityDistributionItemDTO(
                    severity="CRITICAL",
                    count=critical_cnt,
                    percentage=round((critical_cnt / total_active) * 100, 1),
                ),
                AlertSeverityDistributionItemDTO(
                    severity="WARNING",
                    count=warning_cnt,
                    percentage=round((warning_cnt / total_active) * 100, 1),
                ),
                AlertSeverityDistributionItemDTO(
                    severity="INFO",
                    count=info_cnt,
                    percentage=round((info_cnt / total_active) * 100, 1),
                ),
            ]

        # 4. Top Alert Categories
        cat_raw = await OperationalAlertRepository.get_top_categories(
            session=session,
            plant_id=effective_plant,
            customer_id=effective_customer,
            dataset_id=effective_dataset,
            limit=5,
        )
        top_cats: List[AlertCategoryDistributionItemDTO] = []
        for c in cat_raw:
            count_val = c["count"]
            pct = round((count_val / total_active) * 100, 1) if total_active > 0 else 0.0
            top_cats.append(
                AlertCategoryDistributionItemDTO(
                    alert_type=c["alert_type"],
                    label=c["alert_type"].replace("_", " ").title(),
                    severity=c["severity"],
                    count=count_val,
                    percentage=pct,
                )
            )

        # 5. Plant & Customer Concentration
        plant_raw = await OperationalAlertRepository.get_plant_concentration(
            session=session,
            plant_id=effective_plant,
            customer_id=effective_customer,
            dataset_id=effective_dataset,
            limit=5,
        )
        plant_conc = [AlertConcentrationItemDTO(**p) for p in plant_raw]

        cust_raw = await OperationalAlertRepository.get_customer_concentration(
            session=session,
            plant_id=effective_plant,
            customer_id=effective_customer,
            dataset_id=effective_dataset,
            limit=5,
        )
        cust_conc = [AlertConcentrationItemDTO(**c) for c in cust_raw]

        # 6. Priority Unresolved Alerts
        models = await OperationalAlertRepository.get_priority_unresolved_alerts(
            session=session,
            plant_id=effective_plant,
            customer_id=effective_customer,
            dataset_id=effective_dataset,
            limit=5,
        )
        priority_alerts: List[PriorityAlertItemDTO] = []
        for m in models:
            priority_alerts.append(
                PriorityAlertItemDTO(
                    id=str(m.id),
                    alert_type=m.alert_type,
                    severity=m.severity,
                    status=m.status,
                    plant_id=m.plant_id,
                    customer_id=m.customer_id,
                    metric_name=m.metric_name,
                    actual_value=float(m.actual_value) if m.actual_value is not None else None,
                    threshold_value=float(m.threshold_value) if m.threshold_value is not None else None,
                    unit=m.unit,
                    business_impact=m.business_impact,
                    detected_at=m.detected_at.isoformat() if m.detected_at else "",
                )
            )

        filter_desc = f"Plant: {effective_plant}, Customer: {effective_customer}, Dataset: {effective_dataset}"
        return OperationalAlertIntelligenceResponseDTO(
            summary=summary_dto,
            severity_distribution=sev_dist,
            top_categories=top_cats,
            plant_concentration=plant_conc,
            customer_concentration=cust_conc,
            priority_alerts=priority_alerts,
            calculation_status="SUCCESS",
            calculation_notes=f"Authoritative WS-07 alert intelligence calculation successful across {summary_dto.total_active} active alerts ({filter_desc}).",
        )
