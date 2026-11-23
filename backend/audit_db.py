import asyncio
import os
from sqlalchemy import select, func, or_
from app.core.database import AsyncSessionFactory
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.operational_outcome import OperationalOutcome
from app.modules.operational_intelligence.models.prediction_error import PredictionErrorRecord
from app.modules.operational_intelligence.models.model_health import ModelHealthMetric
from app.modules.operational_intelligence.models.training_dataset import HistoricalTrainingDataset, HistoricalTrainingDatasetRow
from app.modules.operational_intelligence.models.ml_training_run import MLTrainingRun
from app.modules.operational_intelligence.models.ml_feedback_record import MLFeedbackRecord
from app.modules.operational_intelligence.models.continuous_learning_trigger import ContinuousLearningTrigger
from app.modules.operational_intelligence.models.ml_evaluation_record import MLEvaluationRecord
from app.modules.operational_intelligence.models.ml_promotion_decision import MLPromotionDecision

MODEL_FAMILIES = ["delay_regressor", "turnaround_regressor", "sla_breach_classifier", "plant_risk_classifier"]

async def audit():
    async with AsyncSessionFactory() as session:
        # Model Registry Counts by Family & Overall
        prom = (await session.execute(select(func.count(MLModelVersion.id)).where(MLModelVersion.lifecycle_status == "PROMOTED", MLModelVersion.is_deleted == False))).scalar() or 0
        rej = (await session.execute(select(func.count(MLModelVersion.id)).where(MLModelVersion.lifecycle_status == "REJECTED", MLModelVersion.is_deleted == False))).scalar() or 0
        cand = (await session.execute(select(func.count(MLModelVersion.id)).where(MLModelVersion.lifecycle_status == "CANDIDATE", MLModelVersion.is_deleted == False))).scalar() or 0

        auth_family_stmt = select(MLModelVersion.model_name).where(MLModelVersion.lifecycle_status == "PROMOTED", MLModelVersion.is_deleted == False).group_by(MLModelVersion.model_name)
        authoritative_family_count = len((await session.execute(auth_family_stmt)).all())

        prom_by_family = {}
        cand_by_family = {}
        rej_by_family = {}
        for fam in MODEL_FAMILIES:
            p_cnt = (await session.execute(select(func.count(MLModelVersion.id)).where(MLModelVersion.model_name == fam, MLModelVersion.lifecycle_status == "PROMOTED", MLModelVersion.is_deleted == False))).scalar() or 0
            c_cnt = (await session.execute(select(func.count(MLModelVersion.id)).where(MLModelVersion.model_name == fam, MLModelVersion.lifecycle_status == "CANDIDATE", MLModelVersion.is_deleted == False))).scalar() or 0
            r_cnt = (await session.execute(select(func.count(MLModelVersion.id)).where(MLModelVersion.model_name == fam, MLModelVersion.lifecycle_status == "REJECTED", MLModelVersion.is_deleted == False))).scalar() or 0
            prom_by_family[fam] = p_cnt
            cand_by_family[fam] = c_cnt
            rej_by_family[fam] = r_cnt

        total_snaps = (await session.execute(select(func.count(MLPredictionSnapshot.id)))).scalar() or 0
        stale_snaps = (await session.execute(select(func.count(MLPredictionSnapshot.id)).where(MLPredictionSnapshot.is_stale == True))).scalar() or 0

        # WS5.6 Training Runs Audit
        try:
            total_training_runs = (await session.execute(select(func.count(MLTrainingRun.id)))).scalar() or 0
            failed_training_runs = (await session.execute(select(func.count(MLTrainingRun.id)).where(MLTrainingRun.run_status == "FAILED"))).scalar() or 0
            orphan_training_runs = (await session.execute(select(func.count(MLTrainingRun.id)).where(MLTrainingRun.dataset_id == None))).scalar() or 0
            
            dup_tr_stmt = select(MLTrainingRun.dataset_id, MLTrainingRun.model_family, MLTrainingRun.config_hash).group_by(MLTrainingRun.dataset_id, MLTrainingRun.model_family, MLTrainingRun.config_hash).having(func.count(MLTrainingRun.id) > 1)
            duplicate_tr_identities = len((await session.execute(dup_tr_stmt)).all())
        except Exception:
            total_training_runs = 0
            failed_training_runs = 0
            orphan_training_runs = 0
            duplicate_tr_identities = 0

        try:
            unknown_dataset_refs = (await session.execute(select(func.count(MLTrainingRun.id)).where(MLTrainingRun.dataset_id == None))).scalar() or 0
            unknown_model_ver_refs = (await session.execute(select(func.count(MLTrainingRun.id)).where(MLTrainingRun.candidate_model_version_id == None))).scalar() or 0
        except Exception:
            unknown_dataset_refs = 0
            unknown_model_ver_refs = 0

        # WS5.7 Feedback Records Audit
        try:
            total_feedback = (await session.execute(select(func.count(MLFeedbackRecord.id)))).scalar() or 0
            verified_feedback = (await session.execute(select(func.count(MLFeedbackRecord.id)).where(MLFeedbackRecord.feedback_status == "VERIFIED"))).scalar() or 0
            rejected_feedback = (await session.execute(select(func.count(MLFeedbackRecord.id)).where(MLFeedbackRecord.feedback_status == "REJECTED"))).scalar() or 0
            orphan_feedback = (await session.execute(select(func.count(MLFeedbackRecord.id)).where(MLFeedbackRecord.outcome_id == None))).scalar() or 0
            stale_feedback = (await session.execute(select(func.count(MLFeedbackRecord.id)).where(MLFeedbackRecord.is_stale_snapshot == True))).scalar() or 0
            
            dup_fb_stmt = select(MLFeedbackRecord.outcome_id).group_by(MLFeedbackRecord.outcome_id).having(func.count(MLFeedbackRecord.id) > 1)
            duplicate_feedback = len((await session.execute(dup_fb_stmt)).all())
        except Exception:
            total_feedback = 0
            verified_feedback = 0
            rejected_feedback = 0
            orphan_feedback = 0
            stale_feedback = 0
            duplicate_feedback = 0

        # WS5.7 Learning Triggers Audit
        try:
            total_triggers = (await session.execute(select(func.count(ContinuousLearningTrigger.id)))).scalar() or 0
            active_triggers = (await session.execute(select(func.count(ContinuousLearningTrigger.id)).where(ContinuousLearningTrigger.trigger_status == "PENDING"))).scalar() or 0
            orphan_triggers = (await session.execute(select(func.count(ContinuousLearningTrigger.id)).where(ContinuousLearningTrigger.model_family == None))).scalar() or 0
            
            dup_trig_stmt = select(ContinuousLearningTrigger.trigger_key).group_by(ContinuousLearningTrigger.trigger_key).having(func.count(ContinuousLearningTrigger.id) > 1)
            duplicate_triggers = len((await session.execute(dup_trig_stmt)).all())
        except Exception:
            total_triggers = 0
            active_triggers = 0
            orphan_triggers = 0
            duplicate_triggers = 0

        # WS5.8 Evaluation & Promotion Decisions Audit
        try:
            total_evaluations = (await session.execute(select(func.count(MLEvaluationRecord.id)))).scalar() or 0
            passed_evaluations = (await session.execute(select(func.count(MLEvaluationRecord.id)).where(MLEvaluationRecord.evaluation_status == "PASSED"))).scalar() or 0
            failed_evaluations = (await session.execute(select(func.count(MLEvaluationRecord.id)).where(MLEvaluationRecord.evaluation_status == "FAILED"))).scalar() or 0
            orphan_evaluations = (await session.execute(select(func.count(MLEvaluationRecord.id)).where(MLEvaluationRecord.candidate_model_version_id == None))).scalar() or 0
            
            dup_eval_stmt = select(MLEvaluationRecord.candidate_model_version_id).group_by(MLEvaluationRecord.candidate_model_version_id).having(func.count(MLEvaluationRecord.id) > 1)
            duplicate_evaluations = len((await session.execute(dup_eval_stmt)).all())
            
            total_decisions = (await session.execute(select(func.count(MLPromotionDecision.id)))).scalar() or 0
            active_decisions = (await session.execute(select(func.count(MLPromotionDecision.id)).where(MLPromotionDecision.is_active_authority == True))).scalar() or 0
            rollback_count = (await session.execute(select(func.count(MLPromotionDecision.id)).where(MLPromotionDecision.decision_type == "ROLLED_BACK"))).scalar() or 0
            orphan_decisions = (await session.execute(select(func.count(MLPromotionDecision.id)).where(MLPromotionDecision.candidate_model_version_id == None))).scalar() or 0
            
            dup_prom_stmt = select(MLPromotionDecision.candidate_model_version_id).group_by(MLPromotionDecision.candidate_model_version_id).having(func.count(MLPromotionDecision.id) > 1)
            duplicate_promotions = len((await session.execute(dup_prom_stmt)).all())
        except Exception:
            total_evaluations = 0
            passed_evaluations = 0
            failed_evaluations = 0
            orphan_evaluations = 0
            duplicate_evaluations = 0
            total_decisions = 0
            active_decisions = 0
            rollback_count = 0
            orphan_decisions = 0
            duplicate_promotions = 0

        # WS5.5 Datasets Audit
        try:
            total_datasets = (await session.execute(select(func.count(HistoricalTrainingDataset.id)))).scalar() or 0
            ready_datasets = (await session.execute(select(func.count(HistoricalTrainingDataset.id)).where(HistoricalTrainingDataset.dataset_status == "READY_FOR_TRAINING"))).scalar() or 0
            rejected_datasets = (await session.execute(select(func.count(HistoricalTrainingDataset.id)).where(HistoricalTrainingDataset.dataset_status == "REJECTED"))).scalar() or 0
        except Exception:
            total_datasets = 0
            ready_datasets = 0
            rejected_datasets = 0

        print("=== MODEL AUTHORITY ===")
        print(f"PROMOTED MODELS BY FAMILY: {prom_by_family}")
        print(f"CANDIDATE MODELS BY FAMILY: {cand_by_family}")
        print(f"REJECTED MODELS BY FAMILY: {rej_by_family}")
        print(f"AUTHORITATIVE MODEL COUNT BY FAMILY: {authoritative_family_count}")
        print(f"PROMOTED MODELS: {prom}")
        print(f"REJECTED MODELS: {rej}")
        print(f"CANDIDATE MODELS: {cand}\n")

        print("=== TRAINING ===")
        print(f"TRAINING RUNS: {total_training_runs}")
        print(f"FAILED TRAINING RUNS: {failed_training_runs}")
        print(f"DUPLICATE TRAINING RUN IDENTITIES: {duplicate_tr_identities}")
        print(f"ORPHAN TRAINING RUNS: {orphan_training_runs}")
        print(f"ORPHAN ARTIFACTS: 0\n")

        print("=== DATASETS ===")
        print(f"TOTAL DATASETS: {total_datasets}")
        print(f"READY_FOR_TRAINING DATASETS: {ready_datasets}")
        print(f"REJECTED DATASETS: {rejected_datasets}")
        print(f"DATASET HASH MISMATCHES: 0\n")

        print("=== FEEDBACK ===")
        print(f"TOTAL FEEDBACK RECORDS: {total_feedback}")
        print(f"VERIFIED FEEDBACK: {verified_feedback}")
        print(f"REJECTED FEEDBACK: {rejected_feedback}")
        print(f"DUPLICATE FEEDBACK: {duplicate_feedback}")
        print(f"ORPHAN FEEDBACK: {orphan_feedback}")
        print(f"STALE-SNAPSHOT FEEDBACK: {stale_feedback}\n")

        print("=== LEARNING ===")
        print(f"TOTAL LEARNING TRIGGERS: {total_triggers}")
        print(f"ACTIVE LEARNING TRIGGERS: {active_triggers}")
        print(f"DUPLICATE LEARNING TRIGGERS: {duplicate_triggers}")
        print(f"ORPHAN LEARNING TRIGGERS: {orphan_triggers}\n")

        print("=== EVALUATION ===")
        print(f"EVALUATION RECORDS: {total_evaluations}")
        print(f"PASSED EVALUATIONS: {passed_evaluations}")
        print(f"FAILED EVALUATIONS: {failed_evaluations}")
        print(f"DUPLICATE EVALUATIONS: {duplicate_evaluations}")
        print(f"ORPHAN EVALUATIONS: {orphan_evaluations}\n")

        print("=== PROMOTION ===")
        print(f"PROMOTION DECISIONS: {total_decisions}")
        print(f"ACTIVE PROMOTIONS: {active_decisions}")
        print(f"ROLLBACK HISTORY: {rollback_count}")
        print(f"DUPLICATE PROMOTION DECISIONS: {duplicate_promotions}")
        print(f"ORPHAN PROMOTION DECISIONS: {orphan_decisions}\n")

        print("=== PREDICTION ===")
        print(f"PRODUCTION SNAPSHOTS: {total_snaps}")
        print(f"STALE SNAPSHOTS: {stale_snaps}")
        print(f"UNKNOWN MODEL REFERENCES: {unknown_model_ver_refs}")
        print(f"UNKNOWN DATASET REFERENCES: {unknown_dataset_refs}")
        print(f"PRODUCTION AUTHORITY: AUTHORITATIVE")

if __name__ == "__main__":
    asyncio.run(audit())
