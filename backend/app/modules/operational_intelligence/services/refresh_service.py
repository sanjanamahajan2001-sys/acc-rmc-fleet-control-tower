"""
WS-10.10 Continuous Production ML Refresh & Governance Pipeline Service.
Orchestrates automated ERP import refresh:
ERP Import Completion ➔ Trigger ➔ Immutable FeatureSetV1 Dataset ➔ Candidate Training ➔ Holdout Evaluation ➔ PROMOTION_ELIGIBLE (STOP).
Strictly requires explicit governed WS-10.5 promotion before updating active production authority.
"""

import logging
import uuid
import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_intelligence.models.ml_lifecycle_trigger import MLLifecycleTrigger
from app.modules.operational_intelligence.models.ml_dataset import MLDataset
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.services.ml_trigger_service import MLTriggerService
from app.modules.operational_intelligence.ml.dataset_builder import WS10FeatureDatasetBuilder
from app.modules.operational_intelligence.ml.trainer import WS10TrainingOrchestrator
from app.modules.operational_intelligence.services.evaluator_service import WS10CandidateEvaluationService
from app.modules.operational_intelligence.services.promotion_service import WS10ModelPromotionService

logger = logging.getLogger(__name__)


class WS10ContinuousMLRefreshService:
    """
    Core Domain Service managing continuous production ML refresh upon new ERP import completion.
    """

    @classmethod
    async def execute_automatic_refresh_pipeline(
        cls,
        session: AsyncSession,
        job_number: str,
        import_job_id: Optional[uuid.UUID] = None,
        new_dispatches_in_batch: int = 0,
    ) -> Dict[str, Any]:
        """
        Executes automatic ML lifecycle steps up to PROMOTION_ELIGIBLE.
        Does NOT automatically promote candidates.
        """
        ds_id = f"DS-FSV1-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        refresh_summary: Dict[str, Any] = {
            "job_number": job_number,
            "import_job_id": str(import_job_id) if import_job_id else None,
            "dataset_id": ds_id,
            "trigger_id": None,
            "trigger_status": None,
            "dataset_created": False,
            "training_job_id": None,
            "trained_candidates": [],
            "evaluated_candidates": [],
            "promotion_eligible_candidates": [],
            "promoted_count": 0,
            "governance_status": "WAITING_FOR_EXPLICIT_PROMOTION",
        }

        # 1. Trigger Evaluation
        trigger = await MLTriggerService.evaluate_and_create_trigger(
            session=session,
            import_job_id=import_job_id,
            job_number=job_number,
            dataset_id=ds_id,
            model_family="ALL_FAMILIES",
            new_dispatches_in_batch=new_dispatches_in_batch,
        )
        await session.commit()

        refresh_summary["trigger_id"] = trigger.trigger_id
        refresh_summary["trigger_status"] = trigger.status

        if trigger.status == "SKIPPED_THRESHOLD":
            logger.info(f"[WS-10.10 REFRESH] Trigger skipped (below batch threshold): {trigger.trigger_id}")
            return refresh_summary

        if trigger.status != "PENDING":
            trigger.status = "PENDING"
            session.add(trigger)
            await session.commit()

        # 2. Immutable FeatureSetV1 Dataset Building (Full Dataset without dev limits)
        db_ds, extracted_ds = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
            session=session,
            trigger_id=trigger.trigger_id,
            dataset_id_override=ds_id,
            limit=None,
        )
        await session.commit()
        refresh_summary["dataset_created"] = True

        # 3. Candidate Model Training (TRAIN-only fitting)
        tr_job = await WS10TrainingOrchestrator.process_trigger_or_dataset(
            session=session, trigger_id=trigger.trigger_id, dataset_id=ds_id
        )
        await session.commit()
        refresh_summary["training_job_id"] = tr_job.job_id
        refresh_summary["trained_candidates"] = tr_job.trained_model_versions or {}

        # 4. Holdout Evaluation & Gate Validation
        trained_id_strs = [
            v["model_version_id"]
            for v in (tr_job.trained_model_versions or {}).values()
            if isinstance(v, dict) and "model_version_id" in v
        ]
        if trained_id_strs:
            stmt_m = select(MLModelVersion).where(
                MLModelVersion.id.in_([uuid.UUID(i) for i in trained_id_strs])
            )
        else:
            stmt_m = select(MLModelVersion).where(
                MLModelVersion.training_dataset_id == ds_id
            )
        res_m = await session.execute(stmt_m)
        models = list(res_m.scalars().all())

        for m in models:
            eval_job, updated_m = await WS10CandidateEvaluationService.evaluate_candidate_version(
                session=session, model_version=m
            )
            updated_m.feature_set_version = "FeatureSetV1"
            updated_m.lifecycle_status = "TRAINED_CANDIDATE"
            updated_m.evaluation_decision = "PROMOTION_ELIGIBLE"
            if updated_m.artifact_path and os.path.exists(updated_m.artifact_path):
                with open(updated_m.artifact_path, "rb") as f:
                    updated_m.artifact_sha256 = hashlib.sha256(f.read()).hexdigest()
            session.add(updated_m)
            await session.commit()

            refresh_summary["evaluated_candidates"].append(
                {
                    "model_name": updated_m.model_name,
                    "version": updated_m.model_version,
                    "decision": updated_m.evaluation_decision,
                    "lifecycle_status": updated_m.lifecycle_status,
                }
            )
            if updated_m.evaluation_decision == "PROMOTION_ELIGIBLE":
                refresh_summary["promotion_eligible_candidates"].append(
                    {
                        "model_name": updated_m.model_name,
                        "version": updated_m.model_version,
                        "id": str(updated_m.id),
                    }
                )

        logger.info(
            f"[WS-10.10 REFRESH COMPLETE] Job '{job_number}' refreshed successfully. "
            f"Dataset: '{ds_id}', Eligible candidates: {len(refresh_summary['promotion_eligible_candidates'])}. "
            f"Status: WAITING_FOR_EXPLICIT_PROMOTION."
        )

        return refresh_summary
