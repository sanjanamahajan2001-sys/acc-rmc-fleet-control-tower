from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reports.schemas.report_schemas import ReportStatus
from app.modules.reports.schemas.predictive_intelligence_canonical import (
    CanonicalPredictiveIntelligenceReport,
    ReportMetadataDTO,
    PredictiveKPISummary,
    PredictionSnapshotRecord,
)
from app.modules.operational_intelligence.services.predictive_service import PredictiveIntelligenceService
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams


class PredictiveIntelligenceReportHandler:
    """Handler for assembling canonical Predictive Intelligence reports from PredictiveIntelligenceService."""

    async def build_canonical_report(
        self,
        session: AsyncSession,
        execution_id: str,
        requested_scope: Dict[str, Any],
        effective_scope: Dict[str, Any],
        scope_fingerprint: str,
        requested_by: str = "SYSTEM"
    ) -> CanonicalPredictiveIntelligenceReport:
        now_str = datetime.now(timezone.utc).isoformat()
        metadata = ReportMetadataDTO(
            execution_id=execution_id,
            report_id="predictive_intelligence",
            report_name="Predictive Intelligence Report",
            generated_at=now_str,
            requested_by=requested_by
        )

        try:
            params = DashboardFilterParams(
                plant_id=effective_scope.get("plant_id", "ALL"),
                customer_id=effective_scope.get("customer_id", "ALL"),
                date_range=effective_scope.get("operation_date", "ALL")
            )
            op_pred = await PredictiveIntelligenceService.get_operational_predictive_intelligence(session, params)

            snapshots = op_pred.snapshots

            records = [
                PredictionSnapshotRecord(
                    prediction_snapshot_id=s.prediction_snapshot_id,
                    prediction_timestamp=s.prediction_timestamp,
                    prediction_status=s.prediction_status,
                    model_name=s.model_name,
                    model_version=s.model_version,
                    feature_set_version=s.feature_set_version,
                    dispatch_id=s.dispatch_id,
                    dispatch_code=s.dispatch_code,
                    plant_code=s.plant_code,
                    customer_code=s.customer_code,
                    vehicle_code=s.vehicle_code,
                    target_name=s.target_name,
                    predicted_value=s.predicted_value,
                    confidence_score=s.confidence_score,
                    financial_exposure_inr=s.financial_exposure_inr,
                    total_financial_risk_inr=s.total_financial_risk_inr
                )
                for s in snapshots
            ]

            total_snaps = len(records)
            valid_delays = [r.predicted_value for r in records if r.predicted_value is not None]
            avg_delay = round(sum(valid_delays) / len(valid_delays), 1) if valid_delays else 0.0
            valid_conf = [r.confidence_score for r in records if r.confidence_score is not None]
            avg_conf = round(sum(valid_conf) / len(valid_conf), 2) if valid_conf else 0.0
            total_risk = round(sum(r.total_financial_risk_inr or 0.0 for r in records), 2)

            kpis = PredictiveKPISummary(
                promoted_model_count=op_pred.promoted_model_count,
                total_snapshots_found=op_pred.total_snapshots_found,
                avg_predicted_delay_mins=avg_delay,
                avg_confidence_score=avg_conf,
                total_financial_risk_inr=total_risk
            )

            status = ReportStatus.COMPLETED if total_snaps > 0 else ReportStatus.NO_DATA

            return CanonicalPredictiveIntelligenceReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=status,
                record_count=total_snaps,
                overall_authority_status=op_pred.overall_authority_status,
                kpis=kpis,
                records=records,
                exceptions=[]
            )
        except Exception:
            return CanonicalPredictiveIntelligenceReport(
                metadata=metadata,
                requested_scope=requested_scope,
                effective_scope=effective_scope,
                scope_fingerprint=scope_fingerprint,
                status=ReportStatus.NO_DATA,
                record_count=0,
                overall_authority_status="NOT_CONFIGURED",
                kpis=PredictiveKPISummary(),
                records=[],
                exceptions=[]
            )
