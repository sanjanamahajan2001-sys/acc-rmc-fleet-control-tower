"""
Operational Intelligence API Router
WS-09 Phase 1 REST API Endpoints
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.common import get_db_session
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_intelligence.services.health_service import OperationalHealthService
from app.modules.operational_intelligence.schemas.health_dtos import OperationalHealthResponseDTO
from app.schemas.envelope import APIResponse

from app.modules.operational_intelligence.services.alert_intelligence_service import OperationalAlertIntelligenceService
from app.modules.operational_intelligence.schemas.alert_intelligence_dtos import OperationalAlertIntelligenceResponseDTO

from app.modules.operational_intelligence.services.decision_recommendation_service import OperationalDecisionRecommendationService
from app.modules.operational_intelligence.schemas.decision_recommendation_dtos import OperationalDecisionRecommendationResponseDTO

from app.modules.operational_intelligence.services.financial_exposure_service import OperationalFinancialExposureService
from app.modules.operational_intelligence.schemas.financial_exposure_dtos import OperationalFinancialExposureResponseDTO

from app.modules.operational_intelligence.services.fleet_efficiency_service import OperationalFleetEfficiencyService
from app.modules.operational_intelligence.schemas.fleet_efficiency_dtos import OperationalFleetEfficiencyResponseDTO

from app.modules.operational_intelligence.services.cost_exposure_service import OperationalCostExposureService
from app.modules.operational_intelligence.schemas.cost_exposure_dtos import OperationalCostExposureResponseDTO

from app.modules.operational_intelligence.routers.feedback_loop_router import router as feedback_loop_router
from app.modules.operational_intelligence.routers.model_evaluation_router import router as model_evaluation_router
from app.modules.operational_intelligence.routers.predictive_management_router import router as predictive_management_router
from app.modules.operational_intelligence.api.action_routes import router as action_routes_router

router = APIRouter(prefix="/operational-intelligence", tags=["Operational Intelligence Workspace"])
router.include_router(feedback_loop_router)
router.include_router(model_evaluation_router)
router.include_router(predictive_management_router)
router.include_router(action_routes_router)


@router.get(
    "/health",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Operational Health & Executive Index (WS-09 Section 01)",
    description="Returns authoritative PostgreSQL operational health metrics, dataset freshness, and provenance.",
)
async def get_operational_health(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    dto: OperationalHealthResponseDTO = await OperationalHealthService.get_operational_health(session, params)
    return {"success": True, "data": dto.model_dump()}


@router.get(
    "/alerts",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Operational Alert Intelligence (WS-09 Section 02)",
    description="Returns authoritative WS-07 operational alert distribution, concentration, and priority alert metrics.",
)
async def get_operational_alerts(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    dto: OperationalAlertIntelligenceResponseDTO = await OperationalAlertIntelligenceService.get_alert_intelligence(session, params)
    return {"success": True, "data": dto.model_dump()}


@router.get(
    "/recommendations",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Actionable Decision Recommendations (WS-09 Section 03)",
    description="Returns authoritative decision recommendations derived from RecommendationEngine authority.",
)
async def get_decision_recommendations(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    dto: OperationalDecisionRecommendationResponseDTO = await OperationalDecisionRecommendationService.get_decision_recommendations(session, params)
    return {"success": True, "data": dto.model_dump()}


@router.get(
    "/financial",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Financial Loss & SLA Risk Exposure (WS-09 Section 04)",
    description="Returns authoritative quantified financial loss, SLA penalty exposure, and idle fuel waste metrics.",
)
async def get_financial_exposure(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    dto: OperationalFinancialExposureResponseDTO = await OperationalFinancialExposureService.get_financial_exposure(session, params)
    return {"success": True, "data": dto.model_dump()}


@router.get(
    "/efficiency",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Fleet & Plant Operational Efficiency (WS-09 Section 05)",
    description="Returns authoritative capacity utilization, turnaround times, and fleet distribution efficiency metrics.",
)
async def get_fleet_efficiency(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    dto: OperationalFleetEfficiencyResponseDTO = await OperationalFleetEfficiencyService.get_fleet_efficiency(session, params)
    return {"success": True, "data": dto.model_dump()}


@router.get(
    "/cost-exposure",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Cost & Exposure Intelligence (WS-09 Section 06)",
    description="Returns authoritative realized cost exposure, paginated high-cost operations, plant/customer risk concentration, and model provenance.",
)
async def get_cost_exposure(
    params: DashboardFilterParams = Depends(),
    page: int = Query(1, ge=1, description="Page number for high-cost operations pagination"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page for high-cost operations pagination"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    dto: OperationalCostExposureResponseDTO = await OperationalCostExposureService.get_cost_exposure(
        session, params, page=page, page_size=page_size
    )
    return {"success": True, "data": dto.model_dump()}


# =============================================================================
# WS-09 PHASE 7.6 PREDICTIVE INTELLIGENCE WORKSPACE API ENDPOINTS
# =============================================================================

from app.modules.operational_intelligence.services.predictive_service import PredictiveIntelligenceService
from app.modules.operational_intelligence.repositories.prediction_snapshot_repository import PredictionRequestDTO


@router.get(
    "/predictive/authority",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Predictive Intelligence Workspace Authority Overview (WS-09 Phase 7.6)",
    description="Returns active prediction authority status across all candidate model families.",
)
async def get_predictive_authority_overview(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    dto = await PredictiveIntelligenceService.get_predictive_authority_overview(session)
    return {"success": True, "data": dto.model_dump()}


@router.post(
    "/predictive/inference",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Execute Prediction Inference & Snapshot Generation (WS-09 Phase 7.6)",
    description="Generates authoritative prediction snapshot or returns NOT_CONFIGURED state.",
)
async def execute_prediction_inference(
    model_name: str = Query(..., description="Target model family name"),
    request: PredictionRequestDTO = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    dto = await PredictiveIntelligenceService.execute_prediction_inference(session, model_name, request)
    return {"success": True, "data": dto.model_dump()}


@router.get(
    "/predictive/snapshots",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Prediction Snapshot History (WS-09 Phase 7.6)",
    description="Returns historical prediction snapshots from PostgreSQL.",
)
async def get_prediction_snapshot_history(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    dto = await PredictiveIntelligenceService.get_prediction_snapshot_history(session, params)
    return {"success": True, "data": dto.model_dump()}


@router.get(
    "/predictive/operational-overview",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Operational Predictive Intelligence & Risk Prioritization (WS-09 Phase 7.7)",
    description="Returns enriched prediction snapshots and operational decision intelligence prioritization.",
)
async def get_operational_predictive_intelligence(
    params: DashboardFilterParams = Depends(),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    dto = await PredictiveIntelligenceService.get_operational_predictive_intelligence(session, params)
    return {"success": True, "data": dto.model_dump()}


# =============================================================================
# WS-10 PHASE 5.4 MODEL HEALTH & PERFORMANCE AGGREGATION ENDPOINT
# =============================================================================

from app.modules.operational_intelligence.services.model_health_service import ModelHealthService
from app.modules.operational_intelligence.repositories.model_health_repository import ModelHealthRepository
from fastapi import HTTPException


@router.get(
    "/predictive/health",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Governed Model Health & Drift Metrics (WS-10 Phase 5.4)",
    description="Returns aggregated model health, version performance, sample counts, baseline provenance, financial policy, and governed health status.",
)
async def get_model_health_metrics(
    model_name: str = Query("delay_regressor", description="Target model family name"),
    model_version_id: Optional[str] = Query(None, description="Exact model version ID or version string"),
    scope_type: str = Query("GLOBAL", description="Scope type: GLOBAL, PLANT, or CUSTOMER"),
    scope_id: Optional[str] = Query(None, description="Scope ID string for PLANT or CUSTOMER"),
    window_type: str = Query("30d", description="Window type: 7d, 30d, or ALL_TIME"),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Retrieves or calculates authoritative ModelHealthMetric for specified criteria."""
    target_version_id = model_version_id or "v1.1.0-candidate-ds-fsv1-prom"
    repo = ModelHealthRepository(session)

    health_record = await repo.get_latest_health(
        model_name=model_name,
        model_version_id=target_version_id,
        scope_type=scope_type,
        scope_id=scope_id,
        window_type=window_type,
    )

    if not health_record:
        # Calculate dynamically if not present
        res = await ModelHealthService.calculate_and_persist_model_health(
            session=session,
            model_name=model_name,
            model_version_id=target_version_id,
            scope_type=scope_type,
            scope_id=scope_id,
            window_type=window_type,
        )
        health_record = await repo.get_by_id(res["health_record_id"])

    if not health_record:
        raise HTTPException(status_code=404, detail="MODEL_HEALTH_RECORD_NOT_FOUND")

    sources = await repo.get_sources_for_health_record(health_record.health_record_id)

    return {
        "success": True,
        "data": {
            "health_record_id": health_record.health_record_id,
            "idempotency_key": health_record.idempotency_key,
            "model_identity": {
                "model_name": health_record.model_name,
                "model_family": health_record.model_family,
                "model_version_id": health_record.model_version_id,
                "model_version": health_record.model_version,
                "feature_set_version": health_record.feature_set_version,
            },
            "scope": {
                "scope_type": health_record.scope_type,
                "scope_id": health_record.scope_id,
            },
            "window": {
                "window_type": health_record.window_type,
                "window_start": health_record.window_start.isoformat(),
                "window_end": health_record.window_end.isoformat(),
                "evaluation_timestamp": health_record.evaluation_timestamp.isoformat(),
            },
            "sample_counts": {
                "total_prediction_error_count": health_record.total_prediction_error_count,
                "regression_sample_count": health_record.regression_sample_count,
                "classification_sample_count": health_record.classification_sample_count,
                "financial_sample_count": health_record.financial_sample_count,
                "valid_percentage_error_count": health_record.valid_percentage_error_count,
                "zero_actual_count": health_record.zero_actual_count,
            },
            "metrics": {
                "mae": float(health_record.mae) if health_record.mae is not None else None,
                "rmse": float(health_record.rmse) if health_record.rmse is not None else None,
                "mape": float(health_record.mape) if health_record.mape is not None else None,
                "mean_signed_error": float(health_record.mean_signed_error) if health_record.mean_signed_error is not None else None,
                "median_absolute_error": float(health_record.median_absolute_error) if health_record.median_absolute_error is not None else None,
                "max_absolute_error": float(health_record.max_absolute_error) if health_record.max_absolute_error is not None else None,
                "accuracy": float(health_record.accuracy) if health_record.accuracy is not None else None,
                "precision_score": float(health_record.precision_score) if health_record.precision_score is not None else None,
                "recall_score": float(health_record.recall_score) if health_record.recall_score is not None else None,
                "f1_score": float(health_record.f1_score) if health_record.f1_score is not None else None,
                "brier_score": float(health_record.brier_score) if health_record.brier_score is not None else None,
            },
            "financial_metrics": {
                "mean_financial_error_inr": float(health_record.mean_financial_error_inr) if health_record.mean_financial_error_inr is not None else None,
                "mae_financial_error_inr": float(health_record.mae_financial_error_inr) if health_record.mae_financial_error_inr is not None else None,
                "total_predicted_exposure_inr": float(health_record.total_predicted_exposure_inr) if health_record.total_predicted_exposure_inr is not None else None,
                "total_realized_impact_inr": float(health_record.total_realized_impact_inr) if health_record.total_realized_impact_inr is not None else None,
            },
            "governance": {
                "health_status": health_record.health_status,
                "baseline_mae": float(health_record.baseline_mae) if health_record.baseline_mae is not None else None,
                "baseline_f1": float(health_record.baseline_f1) if health_record.baseline_f1 is not None else None,
                "baseline_brier": float(health_record.baseline_brier) if health_record.baseline_brier is not None else None,
                "baseline_provenance": health_record.baseline_provenance,
                "financial_health_policy": health_record.financial_health_policy,
            },
            "lineage": {
                "health_calculation_version": health_record.health_calculation_version,
                "formula_version": health_record.formula_version,
                "is_superseded": health_record.is_superseded,
                "superseded_by_health_id": health_record.superseded_by_health_id,
                "source_error_count": len(sources),
                "capped_jsonb_summary": health_record.source_error_ids,
            },
        },
    }


# ============================================================================
# WS5.5 HISTORICAL VERIFIED DATASET BUILDER ENDPOINTS
# ============================================================================

from pydantic import BaseModel, Field
from datetime import datetime

class DatasetGenerateRequestDTO(BaseModel):
    model_family: str = Field(..., description="Target model family: delay_regressor, turnaround_regressor, sla_breach_classifier, plant_risk_classifier")
    source_time_range_start: datetime = Field(..., description="Start of historical outcome window")
    source_time_range_end: datetime = Field(..., description="End of historical outcome window")
    evaluation_cutoff: datetime = Field(..., description="Evaluation cutoff timestamp")
    model_version_id: Optional[str] = Field(None, description="Optional exact model version primary key")
    feature_set_version: str = Field("FeatureSetV1", description="Feature set contract version")
    scope_type: str = Field("GLOBAL", description="Scope type: GLOBAL, SITE, ROUTE, PLANT")
    scope_id: Optional[str] = Field(None, description="Optional scope identifier")
    dataset_version: str = Field("v1.0.0", description="Dataset semver")
    min_sample_count: int = Field(10, description="Minimum sample count threshold")
    force_recompute: bool = Field(False, description="Force recompute dataset version")


@router.post(
    "/predictive/datasets/generate",
    status_code=status.HTTP_201_CREATED,
    summary="Generate Historical Verified Training Dataset",
    description="Constructs immutable, quality-gated training dataset from verified non-superseded outcome lineage.",
)
async def generate_training_dataset(
    payload: DatasetGenerateRequestDTO,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    from app.modules.operational_intelligence.services.training_dataset_service import TrainingDatasetService
    
    service = TrainingDatasetService(session)
    dataset = await service.generate_and_persist_dataset(
        model_family=payload.model_family,
        source_time_range_start=payload.source_time_range_start,
        source_time_range_end=payload.source_time_range_end,
        evaluation_cutoff=payload.evaluation_cutoff,
        model_version_id=payload.model_version_id,
        feature_set_version=payload.feature_set_version,
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        dataset_version=payload.dataset_version,
        min_sample_count=payload.min_sample_count,
        force_recompute=payload.force_recompute,
    )

    return {
        "success": True,
        "message": f"Dataset {dataset.dataset_id} processed with status {dataset.dataset_status}.",
        "data": {
            "dataset_id": dataset.dataset_id,
            "idempotency_key": dataset.idempotency_key,
            "dataset_version": dataset.dataset_version,
            "model_family": dataset.model_family,
            "feature_set_version": dataset.feature_set_version,
            "dataset_status": dataset.dataset_status,
            "quality_gate_passed": dataset.quality_gate_passed,
            "rejection_reason": dataset.rejection_reason,
            "total_row_count": dataset.total_row_count,
            "dataset_content_hash": dataset.dataset_content_hash,
            "source_outcome_count": dataset.source_outcome_count,
            "source_error_count": dataset.source_error_count,
            "source_snapshot_count": dataset.source_snapshot_count,
            "validation_policy_version": dataset.validation_policy_version,
            "leakage_policy_version": dataset.leakage_policy_version,
            "generation_timestamp": dataset.generation_timestamp.isoformat(),
        },
    }


@router.get(
    "/predictive/datasets/{dataset_id}",
    summary="Get Training Dataset Metadata",
    description="Fetches detailed training dataset metadata, quality gates, and lineage summary.",
)
async def get_training_dataset(
    dataset_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    from app.modules.operational_intelligence.repositories.training_dataset_repository import TrainingDatasetRepository
    
    repo = TrainingDatasetRepository(session)
    dataset = await repo.get_by_dataset_id(dataset_id)
    if not dataset:
        return {
            "success": False,
            "message": f"Training dataset '{dataset_id}' not found.",
            "data": {},
        }

    return {
        "success": True,
        "message": "Dataset retrieved successfully.",
        "data": {
            "dataset_id": dataset.dataset_id,
            "dataset_version": dataset.dataset_version,
            "model_family": dataset.model_family,
            "feature_set_version": dataset.feature_set_version,
            "scope": {"scope_type": dataset.scope_type, "scope_id": dataset.scope_id},
            "boundaries": {
                "source_time_range_start": dataset.source_time_range_start.isoformat(),
                "source_time_range_end": dataset.source_time_range_end.isoformat(),
                "evaluation_cutoff": dataset.evaluation_cutoff.isoformat(),
                "generation_timestamp": dataset.generation_timestamp.isoformat(),
            },
            "governance": {
                "dataset_status": dataset.dataset_status,
                "quality_gate_passed": dataset.quality_gate_passed,
                "rejection_reason": dataset.rejection_reason,
                "quality_metrics": dataset.quality_metrics,
                "validation_policy_version": dataset.validation_policy_version,
                "leakage_policy_version": dataset.leakage_policy_version,
                "code_version": dataset.code_version,
                "dataset_content_hash": dataset.dataset_content_hash,
            },
            "counts": {
                "total_row_count": dataset.total_row_count,
                "source_outcome_count": dataset.source_outcome_count,
                "source_error_count": dataset.source_error_count,
                "source_snapshot_count": dataset.source_snapshot_count,
            },
            "lineage_summary": dataset.source_record_ids,
            "is_superseded": dataset.is_superseded,
            "superseded_by_dataset_id": dataset.superseded_by_dataset_id,
        },
    }





