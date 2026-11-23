import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.operational_outcome import OperationalOutcome
from app.modules.operational_intelligence.models.ml_feedback_record import MLFeedbackRecord
from app.modules.operational_intelligence.models.continuous_learning_trigger import ContinuousLearningTrigger

logger = logging.getLogger(__name__)

class FeedbackLoopService:
    """
    Workstream 5.7: Feedback & Continuous Learning Engine Service
    Informs continuous model learning by ingesting verified operational outcomes,
    calculating real-time error metrics, detecting outliers, and triggering automated retraining.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def ingest_feedback_for_outcome(
        self,
        outcome_id: str,
        planner_action: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Ingests verified operational outcome and matches it against prediction snapshots
        to generate feedback records across all active model families.
        """
        # Fetch outcome
        stmt_out = select(OperationalOutcome).where(OperationalOutcome.outcome_id == outcome_id)
        res_out = await self.session.execute(stmt_out)
        outcome = res_out.scalars().first()

        if not outcome:
            raise ValueError(f"Outcome '{outcome_id}' not found.")

        if not outcome.is_verified:
            raise ValueError(f"Outcome '{outcome_id}' is unverified and cannot be ingested into learning loop.")

        # Find matching prediction snapshots by dispatch_code / dispatch_id
        disp_str = str(outcome.dispatch_code or outcome.dispatch_id)
        stmt_snaps = select(MLPredictionSnapshot).where(MLPredictionSnapshot.dispatch_id == disp_str)
        res_snaps = await self.session.execute(stmt_snaps)
        snapshots = res_snaps.scalars().all()

        if not snapshots:
            logger.warning(f"No prediction snapshots found for dispatch '{disp_str}'. Skipping feedback generation.")
            return {"success": True, "created_records": 0, "reason": "NO_SNAPSHOTS"}

        records_created = []
        for snap in snapshots:
            # Determine predicted and realized values based on model_name
            predicted_val = float(snap.predicted_value or 0.0)
            realized_val = 0.0

            if snap.model_name == "delay_regressor":
                realized_val = float(outcome.actual_transit_mins or 0.0)
            elif snap.model_name == "turnaround_regressor":
                realized_val = float((outcome.actual_transit_mins or 0.0) + (outcome.actual_unloading_mins or 0.0))
            elif snap.model_name == "sla_breach_classifier":
                realized_val = 1.0 if outcome.actual_sla_breach_flag else 0.0
            elif snap.model_name == "plant_risk_classifier":
                realized_val = float(outcome.actual_plant_risk_class or 0)

            error_delta = predicted_val - realized_val
            is_outlier = abs(error_delta) > 30.0 if "regressor" in snap.model_name else (predicted_val != realized_val)

            feedback_id = f"FB-{snap.model_name[:8].upper()}-{uuid.uuid4().hex[:8]}"

            # Check existing feedback idempotency
            stmt_exist = select(MLFeedbackRecord).where(
                MLFeedbackRecord.prediction_snapshot_id == snap.prediction_snapshot_id,
                MLFeedbackRecord.outcome_id == outcome.outcome_id,
            )
            existing = (await self.session.execute(stmt_exist)).scalars().first()

            if existing:
                records_created.append(existing.feedback_id)
                continue

            fb_record = MLFeedbackRecord(
                feedback_id=feedback_id,
                dispatch_id=disp_str,
                outcome_id=outcome.outcome_id,
                model_family=snap.model_name,
                model_version_id=str(snap.model_version or snap.model_version_id or "v1.1.0-promoted"),
                prediction_snapshot_id=snap.prediction_snapshot_id,
                predicted_value=predicted_val,
                realized_value=realized_val,
                error_delta=error_delta,
                is_error_outlier=is_outlier,
                planner_action_taken=planner_action,
            )
            self.session.add(fb_record)
            records_created.append(feedback_id)

        await self.session.commit()
        return {
            "success": True,
            "created_records": len(records_created),
            "feedback_ids": records_created,
        }

    async def evaluate_continuous_learning_triggers(
        self,
        model_family: str,
        threshold_mae: float = 15.0,
        threshold_acc: float = 0.80,
    ) -> Dict[str, Any]:
        """
        Evaluates rolling error performance over feedback records and determines if
        an automated retraining trigger should be emitted for the model family.
        """
        stmt_records = select(MLFeedbackRecord).where(MLFeedbackRecord.model_family == model_family)
        res = await self.session.execute(stmt_records)
        records = res.scalars().all()

        if not records:
            return {"model_family": model_family, "samples": 0, "retrain_recommended": False}

        total_samples = len(records)
        errors = [abs(r.error_delta) for r in records]
        mae = sum(errors) / total_samples
        rmse = math.sqrt(sum(e ** 2 for e in errors) / total_samples)

        retrain_recommended = False
        reason = "Performance within acceptable operational boundaries."

        if "regressor" in model_family:
            if mae > threshold_mae:
                retrain_recommended = True
                reason = f"MAE metric ({mae:.2f} mins) breached threshold ({threshold_mae:.2f} mins)."
        else:
            correct_count = sum(1 for r in records if r.predicted_value == r.realized_value)
            acc = correct_count / total_samples
            if acc < threshold_acc:
                retrain_recommended = True
                reason = f"Accuracy ({acc:.2%}) fell below quality threshold ({threshold_acc:.2%})."

        # Emit trigger record if retrain recommended
        trigger_id = f"TRG-{model_family[:8].upper()}-{uuid.uuid4().hex[:6]}"
        cur_version = records[0].model_version_id if records else "v1.1.0-promoted"

        trigger_record = ContinuousLearningTrigger(
            trigger_id=trigger_id,
            model_family=model_family,
            current_model_version_id=cur_version,
            trigger_reason=reason,
            total_feedback_samples=float(total_samples),
            error_mae=mae,
            error_rmse=rmse,
            accuracy_score=(sum(1 for r in records if r.predicted_value == r.realized_value) / total_samples) if "classifier" in model_family else None,
            retrain_recommended=retrain_recommended,
            trigger_status="TRIGGERED" if retrain_recommended else "PASSED",
        )
        self.session.add(trigger_record)
        await self.session.commit()

        return {
            "model_family": model_family,
            "total_samples": total_samples,
            "error_mae": round(mae, 4),
            "error_rmse": round(rmse, 4),
            "retrain_recommended": retrain_recommended,
            "reason": reason,
            "trigger_id": trigger_id,
        }
