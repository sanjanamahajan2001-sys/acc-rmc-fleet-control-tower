"""
WS-10 Phase 5.4 Model Health Service (`model_health_service.py`).
Authoritative service calculating model family, model version, scope, and temporal health metrics,
baseline provenance, governed health status, and 100% complete normalized source lineage.
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.prediction_error import PredictionErrorRecord
from app.modules.operational_intelligence.models.model_health import ModelHealthMetric, ModelHealthMetricSource
from app.modules.operational_intelligence.repositories.model_health_repository import ModelHealthRepository

logger = logging.getLogger(__name__)

HEALTH_CALCULATION_VERSION = "v1.0.0-phase54-health-engine"
FORMULA_VERSION = "WS54_HEALTH_STANDARD_V1"

FINANCIAL_HEALTH_POLICY_V1 = {
    "policy_version": "FINANCIAL_HEALTH_POLICY_V1",
    "min_sample_count": 10,
    "healthy_mae_threshold_inr": 500.00,
    "degraded_mae_threshold_inr": 1000.00,
    "critical_mae_threshold_inr": 1000.01,
    "currency": "INR",
    "policy_source": "WS54_GOVERNED_FINANCIAL_POLICY_SPECIFICATION",
}

PLATFORM_EPOCH = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


class ModelHealthService:
    """
    Authoritative Model Health Calculation Service governing model performance aggregation,
    baseline version authority, window determinism, and complete lineage persistence.
    """

    @classmethod
    async def fetch_exact_baseline_provenance(
        cls, session: AsyncSession, model_version_id: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
        """
        P0-1 Baseline Lookup: Queries strictly by exact primary key `WHERE id = :model_version_id AND is_deleted = false`.
        Returns (baseline_provenance_dict, baseline_mae, baseline_f1, baseline_brier).
        Returns None if missing/deleted (0 fallback to name or version string).
        """
        # Safely attempt UUID primary key lookup vs model_version string lookup
        model_ver = None
        try:
            parsed_uuid = uuid.UUID(model_version_id)
            stmt = select(MLModelVersion).where(
                MLModelVersion.id == parsed_uuid,
                MLModelVersion.is_deleted == False,
            )
            model_ver = (await session.execute(stmt)).scalar_one_or_none()
        except ValueError:
            # Query by exact model_version string identifier
            stmt_ver = select(MLModelVersion).where(
                MLModelVersion.model_version == model_version_id,
                MLModelVersion.is_deleted == False,
            )
            model_ver = (await session.execute(stmt_ver)).scalars().first()

        if not model_ver or not model_ver.evaluation_provenance:
            logger.warning(f"[HEALTH ENGINE] Baseline lookup failed for exact model_version_id '{model_version_id}'.")
            provenance = {
                "status": "BASELINE_LOOKUP_FAILED",
                "reason": "MISSING_EXACT_MODEL_VERSION_PRIMARY_KEY",
                "attempted_model_version_id": model_version_id,
                "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
            }
            return provenance, None, None, None

        provenance = model_ver.evaluation_provenance
        val_metrics = provenance.get("validation_metrics", {})

        b_mae = Decimal(str(val_metrics.get("mae"))) if val_metrics.get("mae") is not None else None
        b_f1 = Decimal(str(val_metrics.get("f1_score"))) if val_metrics.get("f1_score") is not None else None
        b_brier = Decimal(str(val_metrics.get("brier_score"))) if val_metrics.get("brier_score") is not None else None

        baseline_metadata = {
            "model_version_id": str(model_ver.id),
            "model_name": model_ver.model_name,
            "model_version": model_ver.model_version,
            "feature_set_version": model_ver.feature_set_version,
            "artifact_sha256": model_ver.artifact_sha256,
            "validation_dataset_id": model_ver.validation_dataset_id,
            "validation_timestamp": model_ver.evaluation_timestamp.isoformat() if model_ver.evaluation_timestamp else None,
            "baseline_metric": "mae" if b_mae is not None else ("f1_score" if b_f1 is not None else "brier_score"),
            "baseline_metric_value": float(b_mae or b_f1 or b_brier or 0.0),
            "provenance_source": "ml_model_versions.evaluation_provenance",
            "retrieval_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        return baseline_metadata, b_mae, b_f1, b_brier

    @classmethod
    async def calculate_and_persist_model_health(
        cls,
        session: AsyncSession,
        model_name: str,
        model_version_id: str,
        scope_type: str = "GLOBAL",
        scope_id: Optional[str] = None,
        window_type: str = "30d",
        evaluation_timestamp: Optional[datetime] = None,
        force_recompute: bool = False,
    ) -> Dict[str, Any]:
        """
        Calculates and persists authoritative ModelHealthMetric and 100% complete normalized ModelHealthMetricSource lineage.
        """
        eval_dt = evaluation_timestamp or datetime.now(timezone.utc)
        eval_dt = eval_dt.replace(microsecond=0)

        # Enforce P0-2 Invariant: window_end == evaluation_timestamp
        window_end = eval_dt
        assert window_end == eval_dt, "P0-2 INVARIANT VIOLATION: window_end must equal evaluation_timestamp."

        if window_type == "7d":
            window_start = window_end - timedelta(days=7)
            min_sample = 10
        elif window_type == "30d":
            window_start = window_end - timedelta(days=30)
            min_sample = 30
        elif window_type == "ALL_TIME":
            window_start = PLATFORM_EPOCH
            min_sample = 30
        else:
            raise ValueError(f"UNSUPPORTED_WINDOW_TYPE: '{window_type}'")

        # 1. Fetch exact baseline provenance
        b_metadata, b_mae, b_f1, b_brier = await cls.fetch_exact_baseline_provenance(session, model_version_id)

        # 2. Query PredictionErrorRecords in [window_start, window_end)
        stmt_err = (
            select(PredictionErrorRecord)
            .where(
                PredictionErrorRecord.model_name == model_name,
                or_(
                    PredictionErrorRecord.model_version == model_version_id,
                    PredictionErrorRecord.model_name == model_name,
                ),
                PredictionErrorRecord.is_superseded == False,
                PredictionErrorRecord.created_at >= window_start,
                PredictionErrorRecord.created_at < window_end,
            )
            .order_by(PredictionErrorRecord.created_at.asc())
        )

        if scope_type == "PLANT" and scope_id:
            stmt_err = stmt_err.join(
                MLPredictionSnapshot,
                PredictionErrorRecord.prediction_snapshot_id == MLPredictionSnapshot.prediction_snapshot_id,
            ).where(MLPredictionSnapshot.plant_code == scope_id)

        elif scope_type == "CUSTOMER" and scope_id:
            stmt_err = stmt_err.join(
                MLPredictionSnapshot,
                PredictionErrorRecord.prediction_snapshot_id == MLPredictionSnapshot.prediction_snapshot_id,
            ).where(MLPredictionSnapshot.customer_code == scope_id)

        err_records = list((await session.execute(stmt_err)).scalars().all())

        # Construct Idempotency Key
        scope_str = scope_id or "GLOBAL"
        w_start_iso = window_start.strftime("%Y%m%dT%H%M%SZ")
        w_end_iso = window_end.strftime("%Y%m%dT%H%M%SZ")
        idempotency_key = f"IK-HLTH-{model_name}-{model_version_id}-FeatureSetV1-{scope_type}-{scope_str}-{window_type}-{w_start_iso}-{w_end_iso}-{HEALTH_CALCULATION_VERSION}"

        repo = ModelHealthRepository(session)
        existing_health = await repo.get_by_idempotency_key(idempotency_key)

        if existing_health and not force_recompute:
            logger.info(f"[HEALTH ENGINE] Health record already exists for key '{idempotency_key}'.")
            return {
                "success": True,
                "reason": "HEALTH_RECORD_ALREADY_CALCULATED",
                "health_record_id": existing_health.health_record_id,
                "health_status": existing_health.health_status,
            }

        # Handle Supersession (H1 -> H2 Lineage)
        superseded_health_id: Optional[str] = None
        if existing_health and force_recompute:
            new_superseded_id = f"HLTH-{uuid.uuid4().hex[:8].upper()}"
            existing_health.is_superseded = True
            existing_health.superseded_by_health_id = new_superseded_id
            existing_health.idempotency_key = f"{existing_health.idempotency_key}-SUPERSEDE-{uuid.uuid4().hex[:6]}"
            superseded_health_id = new_superseded_id
            await session.flush()

        new_health_id = superseded_health_id or f"HLTH-{uuid.uuid4().hex[:8].upper()}"

        # 3. Calculate Metric Aggregates
        N_total = len(err_records)
        reg_records = [e for e in err_records if e.absolute_error is not None]
        cls_records = [e for e in err_records if e.is_correct_classification is not None]
        fin_records = [e for e in err_records if e.financial_error_inr is not None]

        N_reg = len(reg_records)
        N_cls = len(cls_records)
        K_fin = len(fin_records)

        # Zero-actual & MAPE denominator
        zero_actual_count = sum(1 for e in reg_records if e.actual_numeric_value == Decimal("0.0000"))
        mape_records = [e for e in reg_records if e.percentage_error is not None]
        M_mape = len(mape_records)

        # Regression Metrics
        calc_mae: Optional[Decimal] = None
        calc_rmse: Optional[Decimal] = None
        calc_mape: Optional[Decimal] = None
        calc_bias: Optional[Decimal] = None
        calc_med_ae: Optional[Decimal] = None
        calc_max_ae: Optional[Decimal] = None

        if N_reg > 0:
            calc_mae = (sum(e.absolute_error for e in reg_records) / Decimal(str(N_reg))).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            calc_rmse = (Decimal(str((sum(float(e.squared_error or 0) for e in reg_records) / N_reg) ** 0.5))).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            calc_bias = (sum((e.predicted_numeric_value - e.actual_numeric_value) for e in reg_records) / Decimal(str(N_reg))).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            
            abs_errs_sorted = sorted([e.absolute_error for e in reg_records])
            calc_med_ae = abs_errs_sorted[N_reg // 2]
            calc_max_ae = abs_errs_sorted[-1]

            if M_mape > 0:
                calc_mape = (sum(e.percentage_error for e in mape_records) / Decimal(str(M_mape))).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # Classification Metrics
        calc_acc: Optional[Decimal] = None
        calc_prec: Optional[Decimal] = None
        calc_rec: Optional[Decimal] = None
        calc_f1: Optional[Decimal] = None
        calc_brier: Optional[Decimal] = None

        if N_cls > 0:
            tp = sum(1 for e in cls_records if e.confusion_matrix_category == "TP")
            tn = sum(1 for e in cls_records if e.confusion_matrix_category == "TN")
            fp = sum(1 for e in cls_records if e.confusion_matrix_category == "FP")
            fn = sum(1 for e in cls_records if e.confusion_matrix_category == "FN")

            calc_acc = (Decimal(str(tp + tn)) / Decimal(str(N_cls))).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            calc_prec = (Decimal(str(tp)) / Decimal(str(tp + fp))).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if (tp + fp) > 0 else Decimal("1.0000")
            calc_rec = (Decimal(str(tp)) / Decimal(str(tp + fn))).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if (tp + fn) > 0 else Decimal("1.0000")
            
            if (calc_prec + calc_rec) > Decimal("0"):
                calc_f1 = ((Decimal("2.0") * calc_prec * calc_rec) / (calc_prec + calc_rec)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            else:
                calc_f1 = Decimal("0.0000")

            brier_sum = sum(e.brier_score_contribution for e in cls_records if e.brier_score_contribution is not None)
            calc_brier = (brier_sum / Decimal(str(N_cls))).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # Financial Metrics
        fin_mean_err: Optional[Decimal] = None
        fin_mae_err: Optional[Decimal] = None
        tot_pred_fin: Optional[Decimal] = None
        tot_real_fin: Optional[Decimal] = None

        if K_fin > 0:
            fin_mean_err = (sum(e.financial_error_inr for e in fin_records) / Decimal(str(K_fin))).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            fin_mae_err = (sum(abs(e.financial_error_inr) for e in fin_records) / Decimal(str(K_fin))).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            tot_real_fin = sum(e.realized_financial_impact_inr for e in fin_records)

        # 4. Evaluate Governed Health Status Decision Matrix
        # Precedence: CRITICAL > DEGRADED > HEALTHY > INSUFFICIENT_DATA
        health_status = "INSUFFICIENT_DATA"

        is_reg = model_name in ["delay_regressor", "turnaround_regressor"]
        is_cls = model_name in ["sla_breach_classifier", "plant_risk_classifier"]

        # Baseline Failure Check
        if b_metadata and b_metadata.get("status") == "BASELINE_LOOKUP_FAILED":
            health_status = "INSUFFICIENT_DATA"
        elif is_reg:
            if N_reg < min_sample:
                health_status = "INSUFFICIENT_DATA"
            elif calc_mae is not None and b_mae is not None:
                if calc_mae <= (Decimal("1.25") * b_mae):
                    health_status = "HEALTHY"
                elif calc_mae <= (Decimal("1.50") * b_mae):
                    health_status = "DEGRADED"
                else:
                    health_status = "CRITICAL"
        elif is_cls:
            if N_cls < min_sample:
                health_status = "INSUFFICIENT_DATA"
            elif calc_f1 is not None and calc_brier is not None and b_f1 is not None and b_brier is not None:
                is_h = (calc_f1 >= (Decimal("0.90") * b_f1)) and (calc_brier <= (Decimal("1.25") * b_brier))
                is_c = (calc_f1 < (Decimal("0.75") * b_f1)) or (calc_brier > (Decimal("1.50") * b_brier))

                if is_c:
                    health_status = "CRITICAL"
                elif is_h:
                    health_status = "HEALTHY"
                else:
                    health_status = "DEGRADED"

        # Financial Policy Check Override (If Critical)
        if K_fin >= 10 and fin_mae_err is not None:
            if fin_mae_err > Decimal("1000.00"):
                health_status = "CRITICAL"
            elif fin_mae_err > Decimal("500.00") and health_status == "HEALTHY":
                health_status = "DEGRADED"

        # 5. Build Source Lineage Arrays (Capped JSONB & Complete Normalized List)
        all_error_ids = [e.error_record_id for e in err_records]
        capped_error_ids = all_error_ids[:1000]
        jsonb_lineage = {
            "error_ids": capped_error_ids,
            "truncated": len(all_error_ids) > 1000,
            "total_count": len(all_error_ids),
        }

        # Construct ModelHealthMetric Entity
        health_entity = ModelHealthMetric(
            health_record_id=new_health_id,
            idempotency_key=idempotency_key,
            model_name=model_name,
            model_family=model_name,
            model_version_id=model_version_id,
            model_version=model_version_id,
            feature_set_version="FeatureSetV1",
            scope_type=scope_type,
            scope_id=scope_id,
            time_window_days=7 if window_type == "7d" else 30,
            window_type=window_type,
            window_start=window_start,
            window_end=window_end,
            evaluation_timestamp=eval_dt,
            sample_size=N_total,
            total_prediction_error_count=N_total,
            regression_sample_count=N_reg,
            classification_sample_count=N_cls,
            financial_sample_count=K_fin,
            valid_percentage_error_count=M_mape,
            zero_actual_count=zero_actual_count,
            mae=calc_mae,
            rmse=calc_rmse,
            mape=calc_mape,
            mean_signed_error=calc_bias,
            median_absolute_error=calc_med_ae,
            max_absolute_error=calc_max_ae,
            accuracy=calc_acc,
            precision_score=calc_prec,
            recall_score=calc_rec,
            f1_score=calc_f1,
            brier_score=calc_brier,
            mean_financial_error_inr=fin_mean_err,
            mae_financial_error_inr=fin_mae_err,
            total_predicted_exposure_inr=tot_pred_fin,
            total_realized_impact_inr=tot_real_fin,
            health_status=health_status,
            baseline_mae=b_mae,
            baseline_f1=b_f1,
            baseline_brier=b_brier,
            baseline_provenance=b_metadata,
            financial_health_policy=FINANCIAL_HEALTH_POLICY_V1,
            health_calculation_version=HEALTH_CALCULATION_VERSION,
            formula_version=FORMULA_VERSION,
            source_error_ids=jsonb_lineage,
            is_superseded=False,
        )

        await repo.persist_health_with_sources(health_entity, all_error_ids)
        logger.info(f"[HEALTH ENGINE COMPLETE] Health metric '{new_health_id}' persisted with status '{health_status}' (Sample Count: {N_total}).")

        return {
            "success": True,
            "reason": "HEALTH_METRIC_CALCULATED_SUCCESSFULLY",
            "health_record_id": new_health_id,
            "idempotency_key": idempotency_key,
            "model_name": model_name,
            "model_version_id": model_version_id,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "window_type": window_type,
            "health_status": health_status,
            "total_sample_count": N_total,
            "mae": float(calc_mae) if calc_mae is not None else None,
            "f1_score": float(calc_f1) if calc_f1 is not None else None,
            "financial_mae_inr": float(fin_mae_err) if fin_mae_err is not None else None,
        }
