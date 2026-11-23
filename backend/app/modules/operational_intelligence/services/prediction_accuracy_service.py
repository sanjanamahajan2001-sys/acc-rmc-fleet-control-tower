"""
WS-10 Phase 5.3: Prediction Accuracy & Error Calculation Engine.
Calculates prediction accuracy, prediction error, regression metrics (MAE, MSE, MAPE),
classification metrics (TP, TN, FP, FN, Brier score), and financial prediction error
from authoritative WS5.2 matched outcome-snapshot pairs.
"""

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.operational_outcome import OperationalOutcome
from app.modules.operational_intelligence.models.prediction_error import PredictionErrorRecord

logger = logging.getLogger(__name__)

CALCULATION_VERSION = "v1.0.0-phase53-accuracy-engine"
FORMULA_VERSION = "WS53_STANDARD_METRICS_V1"


class PredictionAccuracyService:
    """
    Authoritative Prediction Accuracy & Error Engine for Phase 5 Workstream 5.3.
    Operates strictly on WS5.2 matched authoritative outcomes and snapshots.
    """

    @classmethod
    def calculate_regression_error(
        cls, predicted_val: float, actual_val: float
    ) -> Tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Optional[Decimal]]:
        """
        Calculates regression metrics:
        returns (predicted, actual, error, absolute_error, squared_error, percentage_error).
        If actual == 0, percentage_error is None (NULL in DB).
        """
        pred_dec = Decimal(str(round(predicted_val, 4)))
        act_dec = Decimal(str(round(actual_val, 4)))
        err_dec = pred_dec - act_dec
        abs_err_dec = abs(err_dec)
        sq_err_dec = err_dec ** 2

        pct_err_dec: Optional[Decimal] = None
        if act_dec != Decimal("0"):
            pct_err_dec = (abs_err_dec / abs(act_dec)) * Decimal("100")
            pct_err_dec = pct_err_dec.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        return pred_dec, act_dec, err_dec, abs_err_dec, sq_err_dec, pct_err_dec

    @classmethod
    def calculate_classification_metrics(
        cls,
        model_name: str,
        prob_val: float,
        pred_class: int,
        actual_class: int,
    ) -> Tuple[Decimal, int, int, bool, str, Decimal]:
        """
        Calculates classification metrics:
        returns (predicted_prob, pred_class, actual_class, is_correct, confusion_matrix_category, brier_contribution).
        """
        # Validate probability bounds: 0.0 <= prob <= 1.0
        if prob_val < 0.0 or prob_val > 1.0:
            raise ValueError(f"CLASSIFICATION PROBABILITY VIOLATION: Probability {prob_val} is outside [0.0, 1.0].")

        prob_dec = Decimal(str(round(prob_val, 4)))
        is_correct = (pred_class == actual_class)

        category = "UNKNOWN"
        if model_name == "sla_breach_classifier":
            # Binary Classification (0 = NO BREACH, 1 = BREACH)
            if actual_class == 1 and pred_class == 1:
                category = "TP"
            elif actual_class == 0 and pred_class == 0:
                category = "TN"
            elif actual_class == 0 and pred_class == 1:
                category = "FP"
            elif actual_class == 1 and pred_class == 0:
                category = "FN"
            
            brier_y = Decimal("1.0") if actual_class == 1 else Decimal("0.0")
            brier_contrib = (prob_dec - brier_y) ** 2

        elif model_name == "plant_risk_classifier":
            # Multi-Class Classification (0 = NORMAL, 1 = MODERATE, 2 = SEVERE)
            # Binary SLA Equivalent for Confusion Matrix Category (Breach threshold > 0)
            act_breach = 1 if actual_class > 0 else 0
            pred_breach = 1 if pred_class > 0 else 0

            if act_breach == 1 and pred_breach == 1:
                category = "TP"
            elif act_breach == 0 and pred_breach == 0:
                category = "TN"
            elif act_breach == 0 and pred_breach == 1:
                category = "FP"
            elif act_breach == 1 and pred_breach == 0:
                category = "FN"

            brier_y = Decimal("1.0") if actual_class > 0 else Decimal("0.0")
            brier_contrib = (prob_dec - brier_y) ** 2
        else:
            category = "CORRECT" if is_correct else "INCORRECT"
            brier_contrib = Decimal("0.0")

        brier_contrib = brier_contrib.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        return prob_dec, pred_class, actual_class, is_correct, category, brier_contrib

    @classmethod
    async def calculate_and_persist_prediction_error(
        cls,
        session: AsyncSession,
        outcome_id: str,
        force_recompute: bool = False,
    ) -> Dict[str, Any]:
        """
        Calculates and persists prediction error metrics for a WS5.2 matched outcome.
        1. Queries OperationalOutcome and linked MLPredictionSnapshot.
        2. Validates authoritative match presence (rejecting missing/unmatched outcomes).
        3. Enforces idempotency via idempotency_key = IK-ERR-<outcome_id>-<snapshot_id>.
        4. Evaluates model family specific error metrics (Regression, Classification, Financial).
        5. Persists PredictionErrorRecord.
        """
        # 1. Query outcome
        stmt_out = select(OperationalOutcome).where(
            OperationalOutcome.outcome_id == outcome_id,
            OperationalOutcome.is_superseded == False,
        )
        outcome = (await session.execute(stmt_out)).scalar_one_or_none()

        if not outcome:
            logger.warning(f"[ACCURACY ENGINE] Outcome '{outcome_id}' not found or superseded.")
            return {
                "success": False,
                "reason": "OUTCOME_NOT_FOUND",
                "outcome_id": outcome_id,
                "error_record_id": None,
            }

        # 2. Validate snapshot match
        if not outcome.prediction_snapshot_id:
            logger.info(f"[ACCURACY ENGINE] Outcome '{outcome_id}' has no prediction snapshot (UNMATCHED_MISSING_SNAPSHOT). Skipping error calculation.")
            return {
                "success": True,
                "reason": "UNMATCHED_MISSING_SNAPSHOT",
                "outcome_id": outcome_id,
                "error_record_id": None,
            }

        # Fetch matched snapshot
        stmt_snap = select(MLPredictionSnapshot).where(
            MLPredictionSnapshot.prediction_snapshot_id == outcome.prediction_snapshot_id
        )
        snapshot = (await session.execute(stmt_snap)).scalar_one_or_none()

        if not snapshot:
            logger.warning(f"[ACCURACY ENGINE] Snapshot '{outcome.prediction_snapshot_id}' not found in DB.")
            return {
                "success": False,
                "reason": "SNAPSHOT_NOT_FOUND",
                "outcome_id": outcome_id,
                "error_record_id": None,
            }

        model_name = snapshot.model_name
        model_version = snapshot.model_version
        feature_set_version = snapshot.feature_set_version

        # 3. Idempotency Check
        base_ik = f"IK-ERR-{outcome.outcome_id}-{snapshot.prediction_snapshot_id}"
        stmt_existing_err = select(PredictionErrorRecord).where(
            PredictionErrorRecord.outcome_id == outcome_id,
            PredictionErrorRecord.is_superseded == False,
        )
        prior_errs = list((await session.execute(stmt_existing_err)).scalars().all())

        if prior_errs and not force_recompute:
            existing_err = prior_errs[0]
            logger.info(f"[ACCURACY ENGINE] Error record for outcome '{outcome_id}' already calculated (ID: {existing_err.error_record_id}).")
            return {
                "success": True,
                "reason": "OUTCOME_ERROR_ALREADY_CALCULATED",
                "outcome_id": outcome_id,
                "error_record_id": existing_err.error_record_id,
                "model_name": model_name,
            }

        # 4. Handle Outcome Correction Lineage (O1 -> O2 Lineage for Error Records)
        superseded_error_id: Optional[str] = None
        rev_count = len(prior_errs)
        idempotency_key = base_ik if rev_count == 0 else f"{base_ik}-rev{rev_count+1}-{uuid.uuid4().hex[:4]}"

        if prior_errs:
            for old_err in prior_errs:
                new_superseded_id = f"ERR-{uuid.uuid4().hex[:8].upper()}"
                old_err.is_superseded = True
                old_err.superseded_by_error_id = new_superseded_id
                superseded_error_id = new_superseded_id
                logger.info(f"[ACCURACY ENGINE] Superseded prior error record {old_err.error_record_id} -> {new_superseded_id}.")

        new_error_record_id = superseded_error_id or f"ERR-{uuid.uuid4().hex[:8].upper()}"

        # 5. Model Family Metric Calculation
        pred_num: Optional[Decimal] = None
        act_num: Optional[Decimal] = None
        abs_err: Optional[Decimal] = None
        sq_err: Optional[Decimal] = None
        pct_err: Optional[Decimal] = None

        pred_prob: Optional[Decimal] = None
        pred_label: Optional[int] = None
        act_label: Optional[int] = None
        is_correct: Optional[bool] = None
        cm_category: Optional[str] = None
        brier_contrib: Optional[Decimal] = None

        if model_name == "delay_regressor":
            pred_val = snapshot.predicted_value if snapshot.predicted_value is not None else 0.0
            act_val = outcome.actual_transit_mins if outcome.actual_transit_mins is not None else 0.0
            pred_num, act_num, err_dec, abs_err, sq_err, pct_err = cls.calculate_regression_error(pred_val, act_val)

        elif model_name == "turnaround_regressor":
            pred_val = snapshot.predicted_value if snapshot.predicted_value is not None else 0.0
            act_val = outcome.actual_unloading_mins if outcome.actual_unloading_mins is not None else 0.0
            pred_num, act_num, err_dec, abs_err, sq_err, pct_err = cls.calculate_regression_error(pred_val, act_val)

        elif model_name == "sla_breach_classifier":
            prob = snapshot.confidence_score if snapshot.confidence_score is not None else 0.5
            pred_label = 1 if prob >= 0.5 else 0
            act_label = 1 if outcome.actual_sla_breach_flag is True else 0
            pred_prob, pred_label, act_label, is_correct, cm_category, brier_contrib = cls.calculate_classification_metrics(
                model_name, prob, pred_label, act_label
            )

        elif model_name == "plant_risk_classifier":
            prob = snapshot.confidence_score if snapshot.confidence_score is not None else 0.5
            pred_label = int(snapshot.predicted_value) if snapshot.predicted_value is not None else 0
            act_label = int(outcome.actual_plant_risk_class) if outcome.actual_plant_risk_class is not None else 0
            pred_prob, pred_label, act_label, is_correct, cm_category, brier_contrib = cls.calculate_classification_metrics(
                model_name, prob, pred_label, act_label
            )

        # 6. Financial Prediction Error Integration
        realized_fin: Optional[Decimal] = outcome.actual_financial_impact_inr
        fin_error: Optional[Decimal] = None

        if realized_fin is not None:
            # Fetch predicted financial exposure from snapshot outputs
            pred_fin_float = snapshot.prediction_outputs.get("financial_exposure_inr") or snapshot.prediction_outputs.get("predicted_total_cost_exposure_inr") or 0.0
            pred_fin_dec = Decimal(str(round(float(pred_fin_float), 2)))
            fin_error = pred_fin_dec - realized_fin

        # 7. Construct & Persist PredictionErrorRecord
        error_entity = PredictionErrorRecord(
            error_record_id=new_error_record_id,
            outcome_id=outcome.outcome_id,
            prediction_snapshot_id=snapshot.prediction_snapshot_id,
            idempotency_key=idempotency_key,
            model_name=model_name,
            model_version=model_version,
            feature_set_version=feature_set_version,
            predicted_numeric_value=pred_num,
            actual_numeric_value=act_num,
            absolute_error=abs_err,
            squared_error=sq_err,
            percentage_error=pct_err,
            predicted_class_or_prob=pred_prob,
            predicted_class_label=pred_label,
            actual_class_label=act_label,
            is_correct_classification=is_correct,
            confusion_matrix_category=cm_category,
            brier_score_contribution=brier_contrib,
            realized_financial_impact_inr=realized_fin,
            financial_error_inr=fin_error,
            is_stale_snapshot=snapshot.is_stale,
            is_superseded=False,
        )

        session.add(error_entity)
        await session.commit()

        logger.info(f"[ACCURACY ENGINE COMPLETE] Error record '{new_error_record_id}' persisted for model '{model_name}' (Outcome: {outcome_id}).")

        return {
            "success": True,
            "reason": "PREDICTION_ERROR_CALCULATED_SUCCESSFULLY",
            "error_record_id": new_error_record_id,
            "outcome_id": outcome.outcome_id,
            "prediction_snapshot_id": snapshot.prediction_snapshot_id,
            "model_name": model_name,
            "model_version": model_version,
            "is_correct_classification": is_correct,
            "confusion_matrix_category": cm_category,
            "absolute_error": float(abs_err) if abs_err is not None else None,
            "financial_error_inr": float(fin_error) if fin_error is not None else None,
        }
