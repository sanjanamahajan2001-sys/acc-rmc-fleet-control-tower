"""
WS-09 Phase 7.6 Predictive Intelligence Service Layer

Provides application service methods for:
- Querying predictive workspace authority status (`get_predictive_authority_overview`)
- Invoking prediction inference & snapshots (`execute_prediction_inference`)
- Querying historical prediction snapshots (`get_prediction_snapshot_history`)
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.repositories.ml_registry_repository import MLModelRegistryRepository
from app.modules.operational_intelligence.repositories.prediction_snapshot_repository import (
    MLPredictionSnapshotRepository,
    PredictionRequestDTO,
)
from app.modules.operational_intelligence.schemas.predictive_dtos import (
    ModelAuthorityItemDTO,
    PredictiveAuthorityOverviewDTO,
    InferenceSnapshotResponseDTO,
    PredictiveSnapshotItemDTO,
    PredictiveSnapshotHistoryResponseDTO,
)


class PredictiveIntelligenceService:
    """Service authority layer for Predictive Intelligence frontend integration."""

    @classmethod
    async def get_predictive_authority_overview(
        cls, session: AsyncSession
    ) -> PredictiveAuthorityOverviewDTO:
        """
        Inspects ML Model Registry for all 4 candidate model families.
        Determines overall predictive workspace status: AUTHORITATIVE or NOT_CONFIGURED.
        """
        registry_repo = MLModelRegistryRepository(session)
        model_families = [
            ("delay_regressor", "predicted_delay_mins", "Regression"),
            ("turnaround_regressor", "predicted_avg_turnaround_mins", "Regression"),
            ("sla_breach_classifier", "predicted_sla_breach_target", "Classification"),
            ("plant_risk_classifier", "predicted_plant_congestion_target", "Classification"),
        ]

        items: List[ModelAuthorityItemDTO] = []
        promoted_count = 0

        for m_name, t_name, cat in model_families:
            promoted = await registry_repo.get_active_promoted_model(m_name)
            if promoted:
                promoted_count += 1
                items.append(
                    ModelAuthorityItemDTO(
                        model_name=m_name,
                        target_name=t_name,
                        model_category=cat,
                        prediction_authority="AUTHORITATIVE",
                        active_version=promoted.model_version,
                        artifact_sha256=promoted.artifact_sha256,
                        feature_set_version=promoted.feature_set_version,
                        last_promoted_at=promoted.promotion_timestamp.isoformat() if promoted.promotion_timestamp else None,
                    )
                )
            else:
                items.append(
                    ModelAuthorityItemDTO(
                        model_name=m_name,
                        target_name=t_name,
                        model_category=cat,
                        prediction_authority="NOT_CONFIGURED",
                        active_version=None,
                        artifact_sha256=None,
                        feature_set_version="FeatureSetV1",
                        last_promoted_at=None,
                    )
                )

        overall_status = "AUTHORITATIVE" if promoted_count > 0 else "NOT_CONFIGURED"
        notes = (
            f"Predictive workspace configured with {promoted_count}/4 active promoted models."
            if promoted_count > 0
            else "PREDICTION AUTHORITY = NOT_CONFIGURED. All 4 candidate models are REJECTED. No promoted production model is currently active."
        )

        return PredictiveAuthorityOverviewDTO(
            overall_authority_status=overall_status,
            total_model_families=4,
            promoted_model_count=promoted_count,
            rejected_model_count=4 - promoted_count,
            models=items,
            calculation_status=overall_status,
            calculation_notes=notes,
        )

    @classmethod
    async def execute_prediction_inference(
        cls, session: AsyncSession, model_name: str, request: PredictionRequestDTO
    ) -> InferenceSnapshotResponseDTO:
        """Executes prediction inference via snapshot repository authority."""
        snapshot_repo = MLPredictionSnapshotRepository(session)
        dto = await snapshot_repo.generate_and_persist_prediction_snapshot(model_name, request)
        return InferenceSnapshotResponseDTO(
            prediction_snapshot_id=dto.prediction_snapshot_id,
            idempotency_key=dto.idempotency_key,
            prediction_timestamp=dto.prediction_timestamp,
            prediction_status=dto.prediction_status,
            model_name=dto.model_name,
            model_version=dto.model_version,
            artifact_sha256=dto.artifact_sha256,
            feature_set_version=dto.feature_set_version,
            dispatch_id=dto.dispatch_id,
            dispatch_code=dto.dispatch_code,
            input_features=dto.input_features,
            prediction_outputs=dto.prediction_outputs,
            predicted_value=dto.predicted_value,
            confidence_score=dto.confidence_score,
            lineage_metadata=dto.lineage_metadata,
        )

    @classmethod
    async def get_operational_predictive_intelligence(
        cls, session: AsyncSession, params: DashboardFilterParams
    ) -> "OperationalPredictiveResponseDTO":
        """
        WS-09 Phase 7.7 Operational Consumption & Decision Intelligence Layer.
        1. Resolves model authority via MLModelRegistryRepository.
        2. If NOT_CONFIGURED (0 promoted models), returns safe NOT_CONFIGURED payload.
        3. If AUTHORITATIVE, queries prediction snapshots, enriches with operational entities, and computes prioritization.
        """
        from app.modules.operational_intelligence.schemas.predictive_operational_dtos import (
            OperationalPredictionItemDTO,
            OperationalPrioritizationDTO,
            OperationalPredictiveResponseDTO,
        )

        overview = await cls.get_predictive_authority_overview(session)
        promoted_count = overview.promoted_model_count

        if promoted_count == 0:
            return OperationalPredictiveResponseDTO(
                overall_authority_status="NOT_CONFIGURED",
                promoted_model_count=0,
                total_snapshots_found=0,
                prioritization=OperationalPrioritizationDTO(
                    top_delayed_dispatches=[],
                    high_sla_risk_dispatches=[],
                    high_plant_risk_dispatches=[],
                ),
                snapshots=[],
                calculation_status="NOT_CONFIGURED",
                calculation_notes="PREDICTION AUTHORITY = NOT_CONFIGURED. No active promoted model exists. Predictive operational intelligence disabled.",
            )

        # Promoted model exists -> Fetch active non-stale snapshots matching filters
        stmt = select(MLPredictionSnapshot).where(
            MLPredictionSnapshot.is_deleted == False,
            MLPredictionSnapshot.is_stale == False,
        )

        if params.plant_id and params.plant_id.upper() != "ALL":
            p_term = params.plant_id.replace("_", " ").strip()
            stmt = stmt.where(
                (MLPredictionSnapshot.plant_code.ilike(f"%{params.plant_id}%"))
                | (MLPredictionSnapshot.plant_code.ilike(f"%{p_term}%"))
            )
        if params.customer_id and params.customer_id.upper() != "ALL":
            c_term = params.customer_id.replace("_", " ").strip()
            stmt = stmt.where(
                (MLPredictionSnapshot.customer_code.ilike(f"%{params.customer_id}%"))
                | (MLPredictionSnapshot.customer_code.ilike(f"%{c_term}%"))
            )
        if params.search and params.search.strip():
            s_clean = params.search.strip()
            s_term = f"%{s_clean}%"
            s_term_underscore = f"%{s_clean.replace(' ', '_')}%"
            s_term_space = f"%{s_clean.replace('_', ' ')}%"
            stmt = stmt.where(
                (MLPredictionSnapshot.prediction_snapshot_id.ilike(s_term))
                | (MLPredictionSnapshot.dispatch_code.ilike(s_term))
                | (MLPredictionSnapshot.customer_code.ilike(s_term))
                | (MLPredictionSnapshot.customer_code.ilike(s_term_underscore))
                | (MLPredictionSnapshot.customer_code.ilike(s_term_space))
                | (MLPredictionSnapshot.plant_code.ilike(s_term))
                | (MLPredictionSnapshot.plant_code.ilike(s_term_underscore))
                | (MLPredictionSnapshot.plant_code.ilike(s_term_space))
                | (MLPredictionSnapshot.model_name.ilike(s_term))
                | (MLPredictionSnapshot.vehicle_code.ilike(s_term))
            )

        stmt_exec = stmt.order_by(MLPredictionSnapshot.prediction_timestamp.desc()).limit(100)
        res = await session.execute(stmt_exec)
        records = res.scalars().all()

        items: List[OperationalPredictionItemDTO] = []
        for r in records:
            # Operational enrichment
            plant_name = f"Plant {r.plant_code}" if r.plant_code else None
            customer_name = f"Customer {r.customer_code}" if r.customer_code else None
            target_name = (
                "predicted_delay_mins"
                if "delay" in r.model_name
                else "predicted_avg_turnaround_mins"
                if "turnaround" in r.model_name
                else "predicted_sla_breach_target"
                if "sla" in r.model_name
                else "predicted_plant_congestion_target"
            )

            # Phase 3 Financial Calculation Engine Integration
            fin_metrics = {}
            try:
                from app.modules.operational_intelligence.services.calculation_engine import FinancialCalculationEngine
                fin_metrics = await FinancialCalculationEngine.compute_snapshot_financial_exposure(
                    session=session,
                    model_name=r.model_name,
                    predicted_value=r.predicted_value,
                    confidence_score=r.confidence_score,
                    plant_code=r.plant_code,
                    customer_code=r.customer_code,
                    input_features=r.input_features or {},
                    target_date=r.prediction_timestamp,
                )
            except Exception as fin_err:
                fin_metrics = {
                    "calculation_status": "NOT_CONFIGURED",
                    "currency": "INR",
                    "calculation_lineage": {"status": "SKIPPED", "error": str(fin_err)},
                }

            items.append(
                OperationalPredictionItemDTO(
                    id=str(r.id),
                    prediction_snapshot_id=r.prediction_snapshot_id,
                    idempotency_key=r.idempotency_key,
                    prediction_timestamp=r.prediction_timestamp.isoformat(),
                    prediction_status=r.prediction_status,
                    model_name=r.model_name,
                    model_version=r.model_version,
                    artifact_sha256=r.artifact_sha256,
                    feature_set_version=r.feature_set_version,
                    dispatch_id=r.dispatch_id,
                    dispatch_code=r.dispatch_code,
                    plant_code=r.plant_code,
                    plant_name=plant_name,
                    customer_code=r.customer_code,
                    customer_name=customer_name,
                    vehicle_code=r.vehicle_code,
                    target_name=target_name,
                    predicted_value=r.predicted_value,
                    confidence_score=r.confidence_score,
                    input_features=r.input_features,
                    prediction_outputs=r.prediction_outputs,
                    lineage_metadata=r.lineage_metadata,
                    financial_exposure_inr=fin_metrics.get("financial_exposure_inr"),
                    sla_penalty_risk_inr=fin_metrics.get("sla_penalty_risk_inr"),
                    plant_congestion_risk_inr=fin_metrics.get("plant_congestion_risk_inr"),
                    idle_queue_cost_inr=fin_metrics.get("idle_queue_cost_inr"),
                    total_financial_risk_inr=fin_metrics.get("total_financial_risk_inr"),
                    currency=fin_metrics.get("currency", "INR"),
                    calculation_lineage=fin_metrics.get("calculation_lineage"),
                )
            )

        # Operational Prioritization logic
        delay_items = sorted(
            [item for item in items if "delay" in item.model_name and item.predicted_value is not None],
            key=lambda x: x.predicted_value or 0.0,
            reverse=True,
        )[:5]

        sla_items = sorted(
            [item for item in items if "sla" in item.model_name and item.predicted_value is not None],
            key=lambda x: x.predicted_value or 0.0,
            reverse=True,
        )[:5]

        plant_items = sorted(
            [item for item in items if ("plant" in item.model_name or "turnaround" in item.model_name) and item.predicted_value is not None],
            key=lambda x: x.predicted_value or 0.0,
            reverse=True,
        )[:5]

        calc_status = "SUCCESS" if len(items) > 0 else "NO_DATA"
        notes = (
            f"Retrieved {len(items)} authoritative prediction snapshots and generated operational decision intelligence."
            if len(items) > 0
            else "PREDICTION AUTHORITY = AUTHORITATIVE. No prediction snapshots match the selected global filters."
        )

        return OperationalPredictiveResponseDTO(
            overall_authority_status="AUTHORITATIVE",
            promoted_model_count=promoted_count,
            total_snapshots_found=len(items),
            prioritization=OperationalPrioritizationDTO(
                top_delayed_dispatches=delay_items,
                high_sla_risk_dispatches=sla_items,
                high_plant_risk_dispatches=plant_items,
            ),
            snapshots=items,
            calculation_status=calc_status,
            calculation_notes=notes,
        )

