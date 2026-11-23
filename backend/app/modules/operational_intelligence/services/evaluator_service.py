"""
WS-10.4 Authoritative Candidate Model Evaluation & Phase 7.3 Promotion-Gate Service.

Consumes candidate model versions (lifecycle_status = 'TRAINED_CANDIDATE' & evaluation_decision = 'PENDING_EVALUATION'),
performs artifact immutability verification (SHA-256 verification), evaluates models strictly against
HOLDOUT_TEST dataset partitions, enforces Phase 7.3 promotion gate thresholds for all 4 approved model families,
and persists evaluation jobs and audit records without silently promoting models.
"""

import os
import time
import json
import uuid
import hashlib
import logging
import numpy as np
import pandas as pd
import joblib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sklearn.metrics import (
    r2_score,
    mean_absolute_error,
    mean_squared_error,
    roc_auc_score,
    f1_score,
    precision_score,
    recall_score,
)
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_intelligence.models.ml_dataset import MLDataset
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion, MLModelAuditEvent
from app.modules.operational_intelligence.models.ml_evaluation_job import MLEvaluationJob
from app.modules.operational_intelligence.repositories.ml_registry_repository import MLModelRegistryRepository
from app.modules.operational_intelligence.ml.feature_extractor import (
    ALLOWED_INFERENCE_FEATURES,
    FEATURE_SET_VERSION,
    FeatureRecordDTO,
)
from app.modules.operational_intelligence.ml.dataset_builder import FeatureSetV1Preprocessor
from app.modules.operational_intelligence.ml.trainer import MODEL_CONFIGURATIONS
from app.modules.operational_intelligence.ml.evaluator import (
    PROMOTION_GATE_THRESHOLDS,
    GateThresholdRuleDTO,
    SingleModelEvaluationReportDTO,
)

logger = logging.getLogger(__name__)


class WS10CandidateEvaluationService:
    """
    Authoritative WS-10.4 Automated Candidate Model Evaluation Service.
    """

    TARGET_MAPPINGS: Dict[str, str] = {
        "delay_regressor": "predicted_delay_mins",
        "turnaround_regressor": "predicted_avg_turnaround_mins",
        "sla_breach_classifier": "predicted_sla_breach_target",
        "plant_risk_classifier": "predicted_plant_congestion_target",
    }

    @classmethod
    def calculate_metrics_for_family(
        cls,
        model_family: str,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        y_prob: Optional[np.ndarray] = None,
    ) -> Dict[str, Optional[float]]:
        """
        Computes the standard evaluation metrics for a specific model family.
        """
        metrics: Dict[str, Optional[float]] = {
            "r2": None,
            "mae": None,
            "rmse": None,
            "roc_auc": None,
            "f1": None,
            "precision": None,
            "recall": None,
        }

        if len(y_true) == 0:
            return metrics

        category = "Regression" if "regressor" in model_family else "Classification"

        if category == "Regression":
            metrics["r2"] = float(r2_score(y_true, y_pred))
            metrics["mae"] = float(mean_absolute_error(y_true, y_pred))
            metrics["rmse"] = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        else:
            metrics["f1"] = float(f1_score(y_true, y_pred, zero_division=0))
            metrics["precision"] = float(precision_score(y_true, y_pred, zero_division=0))
            metrics["recall"] = float(recall_score(y_true, y_pred, zero_division=0))

            if y_prob is not None and len(np.unique(y_true)) > 1:
                try:
                    metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob))
                except Exception:
                    metrics["roc_auc"] = 0.5
            elif len(np.unique(y_true)) == 1:
                metrics["roc_auc"] = 1.0 if y_true[0] == y_pred[0] else 0.0

        return metrics

    @classmethod
    def evaluate_threshold_rules(
        cls, model_family: str, metrics: Dict[str, Optional[float]]
    ) -> Tuple[List[Dict[str, Any]], bool, List[str]]:
        """
        Evaluates metrics against authoritative Phase 7.3 promotion gate thresholds.
        """
        gate_cfg = PROMOTION_GATE_THRESHOLDS.get(model_family, {})
        rules: List[Dict[str, Any]] = []
        rejection_reasons: List[str] = []
        overall_pass = True

        category = "Regression" if "regressor" in model_family else "Classification"

        if category == "Regression":
            # R2
            r2_min = gate_cfg.get("r2_min", 0.70)
            r2_val = metrics.get("r2")
            r2_pass = r2_val is not None and r2_val >= r2_min
            rules.append({
                "metric_name": "r2",
                "comparison": ">=",
                "threshold_value": r2_min,
                "actual_holdout_value": r2_val,
                "passed": r2_pass,
            })
            if not r2_pass:
                overall_pass = False
                rejection_reasons.append(f"Holdout R^2 {r2_val} < required threshold {r2_min}")

            # MAE
            mae_max = gate_cfg.get("mae_max", 10.0)
            mae_val = metrics.get("mae")
            mae_pass = mae_val is not None and mae_val <= mae_max
            rules.append({
                "metric_name": "mae",
                "comparison": "<=",
                "threshold_value": mae_max,
                "actual_holdout_value": mae_val,
                "passed": mae_pass,
            })
            if not mae_pass:
                overall_pass = False
                rejection_reasons.append(f"Holdout MAE {mae_val} > required threshold {mae_max}")

            # RMSE
            rmse_max = gate_cfg.get("rmse_max", 15.0)
            rmse_val = metrics.get("rmse")
            rmse_pass = rmse_val is not None and rmse_val <= rmse_max
            rules.append({
                "metric_name": "rmse",
                "comparison": "<=",
                "threshold_value": rmse_max,
                "actual_holdout_value": rmse_val,
                "passed": rmse_pass,
            })
            if not rmse_pass:
                overall_pass = False
                rejection_reasons.append(f"Holdout RMSE {rmse_val} > required threshold {rmse_max}")

        else:
            # ROC-AUC
            auc_min = gate_cfg.get("roc_auc_min", 0.75)
            auc_val = metrics.get("roc_auc")
            auc_pass = auc_val is not None and auc_val >= auc_min
            rules.append({
                "metric_name": "roc_auc",
                "comparison": ">=",
                "threshold_value": auc_min,
                "actual_holdout_value": auc_val,
                "passed": auc_pass,
            })
            if not auc_pass:
                overall_pass = False
                rejection_reasons.append(f"Holdout ROC-AUC {auc_val} < required threshold {auc_min}")

            # F1
            f1_min = gate_cfg.get("f1_min", 0.70)
            f1_val = metrics.get("f1")
            f1_pass = f1_val is not None and f1_val >= f1_min
            rules.append({
                "metric_name": "f1",
                "comparison": ">=",
                "threshold_value": f1_min,
                "actual_holdout_value": f1_val,
                "passed": f1_pass,
            })
            if not f1_pass:
                overall_pass = False
                rejection_reasons.append(f"Holdout F1 {f1_val} < required threshold {f1_min}")

            # Precision
            if "precision_min" in gate_cfg:
                prec_min = gate_cfg["precision_min"]
                prec_val = metrics.get("precision")
                prec_pass = prec_val is not None and prec_val >= prec_min
                rules.append({
                    "metric_name": "precision",
                    "comparison": ">=",
                    "threshold_value": prec_min,
                    "actual_holdout_value": prec_val,
                    "passed": prec_pass,
                })
                if not prec_pass:
                    overall_pass = False
                    rejection_reasons.append(f"Holdout Precision {prec_val} < required threshold {prec_min}")

            # Recall
            if "recall_min" in gate_cfg:
                rec_min = gate_cfg["recall_min"]
                rec_val = metrics.get("recall")
                rec_pass = rec_val is not None and rec_val >= rec_min
                rules.append({
                    "metric_name": "recall",
                    "comparison": ">=",
                    "threshold_value": rec_min,
                    "actual_holdout_value": rec_val,
                    "passed": rec_pass,
                })
                if not rec_pass:
                    overall_pass = False
                    rejection_reasons.append(f"Holdout Recall {rec_val} < required threshold {rec_min}")

        return rules, overall_pass, rejection_reasons

    @classmethod
    async def evaluate_candidate_version(
        cls,
        session: AsyncSession,
        model_version: MLModelVersion,
        dataset_override: Optional[MLDataset] = None,
    ) -> Tuple[MLEvaluationJob, MLModelVersion]:
        """
        Evaluates a candidate MLModelVersion against its immutable dataset and artifact.
        """
        start_time = time.perf_counter()
        started_at = datetime.now(timezone.utc)
        job_id = f"eval-job-{uuid.uuid4().hex[:8]}"

        repo = MLModelRegistryRepository(session)

        # 1. Verification of candidate artifact on-disk SHA-256
        art_path = model_version.artifact_path
        if not os.path.exists(art_path):
            duration = time.perf_counter() - start_time
            eval_job = MLEvaluationJob(
                job_id=job_id,
                model_version_id=model_version.id,
                model_name=model_version.model_name,
                model_version=model_version.model_version,
                dataset_id=model_version.training_dataset_id,
                status="FAILED",
                evaluation_decision="REJECTED",
                execution_duration_sec=duration,
                reason="MISSING_ARTIFACT",
                error_metadata={"error": f"Artifact file not found at '{art_path}'"},
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
            session.add(eval_job)

            updated_version = await repo.update_evaluation_decision(
                version_id=model_version.id,
                new_decision="REJECTED",
                new_lifecycle_status="REJECTED",
                rejection_reasons=["Candidate artifact missing from storage location."],
                evaluation_provenance={"job_id": job_id, "error": "MISSING_ARTIFACT"},
            )
            return eval_job, updated_version

        # Compute SHA-256
        with open(art_path, "rb") as f:
            calc_sha = hashlib.sha256(f.read()).hexdigest()

        if calc_sha.lower() != model_version.artifact_sha256.lower():
            duration = time.perf_counter() - start_time
            eval_job = MLEvaluationJob(
                job_id=job_id,
                model_version_id=model_version.id,
                model_name=model_version.model_name,
                model_version=model_version.model_version,
                dataset_id=model_version.training_dataset_id,
                status="FAILED",
                evaluation_decision="REJECTED",
                execution_duration_sec=duration,
                reason="ARTIFACT_MUTATION_DETECTED",
                error_metadata={
                    "registered_sha": model_version.artifact_sha256,
                    "computed_sha": calc_sha,
                },
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
            session.add(eval_job)

            updated_version = await repo.update_evaluation_decision(
                version_id=model_version.id,
                new_decision="REJECTED",
                new_lifecycle_status="REJECTED",
                rejection_reasons=["ARTIFACT_MUTATION_DETECTED: Artifact SHA-256 mismatch!"],
                evaluation_provenance={
                    "job_id": job_id,
                    "error": "ARTIFACT_MUTATION_DETECTED",
                    "registered_sha": model_version.artifact_sha256,
                    "computed_sha": calc_sha,
                },
            )
            return eval_job, updated_version

        # 2. Resolve dataset
        dataset_id = model_version.training_dataset_id
        db_ds = dataset_override
        if db_ds is None:
            stmt_ds = select(MLDataset).where(MLDataset.dataset_id == dataset_id)
            res_ds = await session.execute(stmt_ds)
            db_ds = res_ds.scalars().first()

        if not db_ds:
            duration = time.perf_counter() - start_time
            eval_job = MLEvaluationJob(
                job_id=job_id,
                model_version_id=model_version.id,
                model_name=model_version.model_name,
                model_version=model_version.model_version,
                dataset_id=dataset_id,
                status="FAILED",
                evaluation_decision="REJECTED",
                execution_duration_sec=duration,
                reason="MISSING_DATASET",
                error_metadata={"error": f"MLDataset '{dataset_id}' not found in registry."},
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
            session.add(eval_job)

            updated_version = await repo.update_evaluation_decision(
                version_id=model_version.id,
                new_decision="REJECTED",
                new_lifecycle_status="REJECTED",
                rejection_reasons=[f"MISSING_DATASET: Immutable MLDataset '{dataset_id}' not found."],
                evaluation_provenance={"job_id": job_id, "error": "MISSING_DATASET"},
            )
            return eval_job, updated_version

        # Verify FeatureSetV1 compatibility
        if db_ds.feature_set_version != FEATURE_SET_VERSION:
            duration = time.perf_counter() - start_time
            eval_job = MLEvaluationJob(
                job_id=job_id,
                model_version_id=model_version.id,
                model_name=model_version.model_name,
                model_version=model_version.model_version,
                dataset_id=dataset_id,
                status="FAILED",
                evaluation_decision="REJECTED",
                execution_duration_sec=duration,
                reason="MALFORMED_FEATURESET",
                error_metadata={"feature_set_version": db_ds.feature_set_version},
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
            session.add(eval_job)

            updated_version = await repo.update_evaluation_decision(
                version_id=model_version.id,
                new_decision="REJECTED",
                new_lifecycle_status="REJECTED",
                rejection_reasons=[f"MALFORMED_FEATURESET: Incompatible dataset version '{db_ds.feature_set_version}'."],
                evaluation_provenance={"job_id": job_id, "error": "MALFORMED_FEATURESET"},
            )
            return eval_job, updated_version

        # 3. Extract HOLDOUT_TEST partition
        from app.modules.operational_intelligence.ml.feature_extractor import Phase71FeatureExtractor

        holdout_dtos: List[FeatureRecordDTO] = []
        partition_found = False
        if hasattr(db_ds, "lineage_metadata") and isinstance(db_ds.lineage_metadata, dict):
            parts = db_ds.lineage_metadata.get("partitions", {})
            if "HOLDOUT_TEST" in parts:
                partition_found = True
                raw_recs = parts["HOLDOUT_TEST"]
                if isinstance(raw_recs, list):
                    for r in raw_recs:
                        if isinstance(r, dict):
                            holdout_dtos.append(FeatureRecordDTO(**r))
                        elif isinstance(r, FeatureRecordDTO):
                            holdout_dtos.append(r)
            elif "records" in db_ds.lineage_metadata and isinstance(db_ds.lineage_metadata["records"], list):
                partition_found = True
                for r in db_ds.lineage_metadata["records"]:
                    if isinstance(r, dict) and r.get("partition") == "HOLDOUT_TEST":
                        holdout_dtos.append(FeatureRecordDTO(**r))

        if not holdout_dtos and not partition_found:
            try:
                extracted_ds = await Phase71FeatureExtractor.extract_training_dataset(session=session, dataset_id=dataset_id)
                holdout_dtos = [r for r in extracted_ds.records if r.partition == "HOLDOUT_TEST"]
            except Exception as ex:
                logger.warning(f"Feature dataset extraction fallback failed for {dataset_id}: {ex}")

        if not holdout_dtos:
            duration = time.perf_counter() - start_time
            eval_job = MLEvaluationJob(
                job_id=job_id,
                model_version_id=model_version.id,
                model_name=model_version.model_name,
                model_version=model_version.model_version,
                dataset_id=dataset_id,
                status="FAILED",
                evaluation_decision="REJECTED",
                execution_duration_sec=duration,
                reason="EMPTY_HOLDOUT",
                error_metadata={"error": "HOLDOUT_TEST partition is empty or missing."},
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
            session.add(eval_job)

            updated_version = await repo.update_evaluation_decision(
                version_id=model_version.id,
                new_decision="REJECTED",
                new_lifecycle_status="REJECTED",
                rejection_reasons=["EMPTY_HOLDOUT: HOLDOUT_TEST partition contains zero records."],
                evaluation_provenance={"job_id": job_id, "error": "EMPTY_HOLDOUT"},
            )
            return eval_job, updated_version

        # 4. Target mapping & Feature Matrix
        target_name = cls.TARGET_MAPPINGS.get(model_version.model_name, model_version.target_name)

        from app.modules.operational_intelligence.ml.trainer import WS10ModelTrainer
        preprocessor = FeatureSetV1Preprocessor()
        preprocessor.fit(holdout_dtos)
        X_holdout, y_holdout_dict = WS10ModelTrainer.prepare_dataframe(holdout_dtos, preprocessor)

        if target_name not in y_holdout_dict or y_holdout_dict[target_name].isnull().all():
            duration = time.perf_counter() - start_time
            eval_job = MLEvaluationJob(
                job_id=job_id,
                model_version_id=model_version.id,
                model_name=model_version.model_name,
                model_version=model_version.model_version,
                dataset_id=dataset_id,
                status="FAILED",
                evaluation_decision="REJECTED",
                execution_duration_sec=duration,
                reason="INVALID_TARGET_MAPPING",
                error_metadata={"missing_target": target_name},
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
            session.add(eval_job)

            updated_version = await repo.update_evaluation_decision(
                version_id=model_version.id,
                new_decision="REJECTED",
                new_lifecycle_status="REJECTED",
                rejection_reasons=[f"INVALID_TARGET_MAPPING: Target column '{target_name}' missing in holdout dataset."],
                evaluation_provenance={"job_id": job_id, "error": "INVALID_TARGET_MAPPING"},
            )
            return eval_job, updated_version

        y_holdout = y_holdout_dict[target_name].values.astype(float)

        # 5. Load model artifact & compute predictions
        try:
            loaded_artifact = joblib.load(art_path)
            if isinstance(loaded_artifact, dict):
                model = loaded_artifact.get("estimator", loaded_artifact)
                feat_cols = loaded_artifact.get("feature_columns")
                if feat_cols:
                    missing_cols = [c for c in feat_cols if c not in X_holdout.columns]
                    if missing_cols:
                        missing_df = pd.DataFrame(0, index=X_holdout.index, columns=missing_cols)
                        X_holdout = pd.concat([X_holdout, missing_df], axis=1)
                    X_holdout = X_holdout[feat_cols]
            else:
                model = loaded_artifact
        except Exception as ex:
            duration = time.perf_counter() - start_time
            eval_job = MLEvaluationJob(
                job_id=job_id,
                model_version_id=model_version.id,
                model_name=model_version.model_name,
                model_version=model_version.model_version,
                dataset_id=dataset_id,
                status="FAILED",
                evaluation_decision="REJECTED",
                execution_duration_sec=duration,
                reason="MODEL_LOAD_FAILURE",
                error_metadata={"exception": str(ex)},
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
            session.add(eval_job)

            updated_version = await repo.update_evaluation_decision(
                version_id=model_version.id,
                new_decision="REJECTED",
                new_lifecycle_status="REJECTED",
                rejection_reasons=[f"MODEL_LOAD_FAILURE: Failed to deserialize candidate artifact: {ex}"],
                evaluation_provenance={"job_id": job_id, "error": "MODEL_LOAD_FAILURE"},
            )
            return eval_job, updated_version

        try:
            y_pred = model.predict(X_holdout)
            y_prob = None
            if hasattr(model, "predict_proba"):
                probs = model.predict_proba(X_holdout)
                if probs.ndim == 2 and probs.shape[1] > 1:
                    y_prob = probs[:, 1]
                else:
                    y_prob = probs.ravel()
        except Exception as ex:
            duration = time.perf_counter() - start_time
            eval_job = MLEvaluationJob(
                job_id=job_id,
                model_version_id=model_version.id,
                model_name=model_version.model_name,
                model_version=model_version.model_version,
                dataset_id=dataset_id,
                status="FAILED",
                evaluation_decision="REJECTED",
                execution_duration_sec=duration,
                reason="PREDICTION_FAILURE",
                error_metadata={"exception": str(ex)},
                started_at=started_at,
                completed_at=datetime.now(timezone.utc),
            )
            session.add(eval_job)

            updated_version = await repo.update_evaluation_decision(
                version_id=model_version.id,
                new_decision="REJECTED",
                new_lifecycle_status="REJECTED",
                rejection_reasons=[f"PREDICTION_FAILURE: Error generating predictions on holdout: {ex}"],
                evaluation_provenance={"job_id": job_id, "error": "PREDICTION_FAILURE"},
            )
            return eval_job, updated_version

        # 6. Metric calculation & Phase 7.3 gate enforcement
        metrics = cls.calculate_metrics_for_family(model_version.model_name, y_holdout, y_pred, y_prob)
        threshold_rules, overall_pass, rejection_reasons = cls.evaluate_threshold_rules(
            model_version.model_name, metrics
        )

        duration = time.perf_counter() - start_time

        # Explicit promotion decision (PROMOTION_ELIGIBLE or REJECTED)
        # CRITICAL: Evaluation PASS does NOT automatically mean PROMOTED!
        decision = "PROMOTION_ELIGIBLE" if overall_pass else "REJECTED"
        new_lifecycle_status = "TRAINED_CANDIDATE" if overall_pass else "REJECTED"

        eval_job = MLEvaluationJob(
            job_id=job_id,
            model_version_id=model_version.id,
            model_name=model_version.model_name,
            model_version=model_version.model_version,
            dataset_id=dataset_id,
            status="COMPLETED",
            evaluation_decision=decision,
            metrics_holdout=metrics,
            threshold_rules=threshold_rules,
            execution_duration_sec=duration,
            reason="EVALUATION_PASSED" if overall_pass else "GATE_THRESHOLD_FAILED",
            error_metadata={"rejection_reasons": rejection_reasons} if not overall_pass else None,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
        )
        session.add(eval_job)

        updated_version = await repo.update_evaluation_decision(
            version_id=model_version.id,
            new_decision=decision,
            new_lifecycle_status=new_lifecycle_status,
            rejection_reasons=rejection_reasons,
            evaluation_provenance={
                "job_id": job_id,
                "holdout_row_count": len(holdout_dtos),
                "metrics_holdout": metrics,
                "threshold_rules": threshold_rules,
                "overall_gate_passed": overall_pass,
                "evaluation_duration_sec": duration,
                "evaluator_version": "WS-10.4",
            },
        )

        return eval_job, updated_version

    @classmethod
    async def process_pending_candidates(
        cls, session: AsyncSession, model_name: Optional[str] = None
    ) -> List[MLEvaluationJob]:
        """
        Finds and evaluates pending candidate models using row-level locking (SKIP LOCKED).
        Returns list of executed evaluation jobs.
        """
        repo = MLModelRegistryRepository(session)
        jobs: List[MLEvaluationJob] = []

        while True:
            candidate = await repo.claim_next_pending_candidate(model_name)
            if not candidate:
                break

            job, _ = await cls.evaluate_candidate_version(session, candidate)
            jobs.append(job)

        return jobs
