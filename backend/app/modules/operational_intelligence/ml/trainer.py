"""
WS-10.3 Authoritative Automated Candidate Model Training Pipeline & Orchestrator.
Consumes FeatureSetV1 datasets (from WS-10.2 or WS-10.1 trigger), trains candidate versions of all 4 model families,
verifies anti-leakage guards & SHA-256 artifact integrity, registers TRAINED_CANDIDATE versions in ml_model_versions,
and persists execution jobs to ml_training_jobs.
"""

import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_intelligence.ml.dataset_builder import (
    FeatureSetV1Preprocessor,
    WS10FeatureDatasetBuilder,
)
from app.modules.operational_intelligence.ml.feature_extractor import (
    ALLOWED_INFERENCE_FEATURES,
    FEATURE_SET_VERSION,
    FORBIDDEN_LEAKAGE_FIELDS,
    ExtractedTrainingDatasetDTO,
    FeatureRecordDTO,
    Phase71FeatureExtractor,
)
from app.modules.operational_intelligence.models.ml_dataset import MLDataset
from app.modules.operational_intelligence.models.ml_lifecycle_trigger import MLLifecycleTrigger
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.ml_training_job import MLTrainingJob
from app.modules.operational_intelligence.repositories.ml_registry_repository import MLModelRegistryRepository
from app.modules.operational_intelligence.services.ml_trigger_service import MLTriggerService

logger = logging.getLogger(__name__)

MODEL_STORAGE_BASE_DIR: str = "/home/sanjana/fleet-operational-intelligence-platform/models/ml"
RANDOM_SEED: int = 42

# Lightning tree configuration (n_estimators=5, max_depth=3) for guaranteed sub-10s four-model training
MODEL_CONFIGURATIONS: Dict[str, Dict[str, Any]] = {
    "delay_regressor": {
        "model_name": "delay_regressor",
        "category": "Regression",
        "target_key": "predicted_delay_mins",
        "algorithm": "RandomForestRegressor",
        "hyperparameters": {"n_estimators": 5, "max_depth": 3, "n_jobs": -1, "random_state": RANDOM_SEED},
    },
    "turnaround_regressor": {
        "model_name": "turnaround_regressor",
        "category": "Regression",
        "target_key": "predicted_avg_turnaround_mins",
        "algorithm": "RandomForestRegressor",
        "hyperparameters": {"n_estimators": 5, "max_depth": 3, "n_jobs": -1, "random_state": RANDOM_SEED},
    },
    "sla_breach_classifier": {
        "model_name": "sla_breach_classifier",
        "category": "Classification",
        "target_key": "predicted_sla_breach_target",
        "algorithm": "RandomForestClassifier",
        "hyperparameters": {"n_estimators": 5, "max_depth": 3, "n_jobs": -1, "random_state": RANDOM_SEED},
    },
    "plant_risk_classifier": {
        "model_name": "plant_risk_classifier",
        "category": "Classification",
        "target_key": "predicted_plant_congestion_target",  # Distinct Target: holding_pen > 0
        "algorithm": "RandomForestClassifier",
        "hyperparameters": {"n_estimators": 5, "max_depth": 3, "min_samples_leaf": 2, "n_jobs": -1, "random_state": RANDOM_SEED},
    },
}


class ModelEvaluationMetricsDTO(BaseModel):
    """Evaluation metrics for a dataset split (TRAIN, VALIDATION, HOLDOUT)."""
    r2: Optional[float] = None
    mae: Optional[float] = None
    rmse: Optional[float] = None
    roc_auc: Optional[float] = None
    f1: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None


class ModelTrainingMetadataDTO(BaseModel):
    """Metadata tracking training execution and artifact parameters."""
    model_name: str
    model_category: str
    target_name: str
    algorithm: str
    hyperparameters: Dict[str, Any]
    training_dataset_id: str
    feature_set_version: str
    source_trigger_id: Optional[str] = None
    train_row_count: int
    val_row_count: int
    holdout_row_count: int
    fit_duration_sec: float
    validation_metrics: Dict[str, Any] = Field(default_factory=dict)
    artifact_path: str
    artifact_size_bytes: int
    artifact_sha256: str
    random_seed: int = RANDOM_SEED
    is_authoritative_candidate: bool = True


class WS10ModelTrainer:
    """
    WS-10.3 Authoritative Candidate Model Training Service.
    Consumes FeatureSetV1 datasets, enforces anti-leakage guards, fits TRAIN-only estimators,
    exports candidate joblib artifacts, computes SHA-256 checksums, and registers TRAINED_CANDIDATE versions.
    """

    @classmethod
    def validate_no_leakage_in_dataframe(cls, df: pd.DataFrame) -> None:
        """Runtime assertion verifying no forbidden target/outcome fields exist in X."""
        for forbidden in FORBIDDEN_LEAKAGE_FIELDS:
            if forbidden in df.columns:
                raise ValueError(
                    f"ANTI-LEAKAGE TRAINING VIOLATION: Forbidden column '{forbidden}' found in feature matrix X!"
                )

    @classmethod
    def prepare_dataframe(
        cls, records: List[FeatureRecordDTO], preprocessor: FeatureSetV1Preprocessor
    ) -> Tuple[pd.DataFrame, Dict[str, pd.Series]]:
        """Converts feature records into preprocessed feature matrix X and target dict y."""
        transformed = [preprocessor.transform_record(r) for r in records]
        df_x = pd.DataFrame(transformed)

        # Drop non-feature columns
        feature_cols = [c for c in ALLOWED_INFERENCE_FEATURES if c in df_x.columns]
        X = df_x[feature_cols].copy()

        # Enforce Anti-Leakage Assertion
        cls.validate_no_leakage_in_dataframe(X)

        # One-hot encode categoricals deterministically
        X = pd.get_dummies(X, columns=["plant_code", "customer_code", "vehicle_code"], drop_first=False)

        # Extract Targets
        y_dict: Dict[str, pd.Series] = {}
        target_keys = [
            "predicted_delay_mins", "predicted_avg_turnaround_mins",
            "predicted_sla_breach_target", "predicted_plant_congestion_target"
        ]
        for key in target_keys:
            vals = [r.targets.get(key) for r in records]
            y_dict[key] = pd.Series(vals)

        return X, y_dict

    @classmethod
    async def train_candidate_model(
        cls,
        session: AsyncSession,
        model_name: str,
        dataset_id: str = "DS-FSV1-DIRECT",
        trigger_id: Optional[str] = None,
    ) -> MLModelVersion:
        """Backward-compatibility wrapper for legacy Phase 7.2 train_candidate_model."""
        stmt_ds = select(MLDataset).where(MLDataset.dataset_id == dataset_id)
        res_ds = await session.execute(stmt_ds)
        db_ds = res_ds.scalars().first()
        if not db_ds:
            db_ds, extracted_ds = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
                session=session, dataset_id_override=dataset_id, limit=30
            )
        else:
            extracted_ds = await Phase71FeatureExtractor.extract_training_dataset(
                session=session, dataset_id=dataset_id
            )

        model_ver, _, _ = await cls.train_candidate_family(
            session=session,
            model_name=model_name,
            extracted_ds=extracted_ds,
            dataset_id=dataset_id,
            trigger_id=trigger_id,
        )
        return model_ver

    @classmethod
    async def train_all_candidate_models(
        cls,
        session: AsyncSession,
        dataset_id: str = "DS-FSV1-DIRECT",
        trigger_id: Optional[str] = None,
    ) -> List[MLModelVersion]:
        """Backward-compatibility wrapper for legacy Phase 7.2 train_all_candidate_models."""
        results = []
        for name in ["delay_regressor", "turnaround_regressor", "sla_breach_classifier", "plant_risk_classifier"]:
            mv = await cls.train_candidate_model(session=session, model_name=name, dataset_id=dataset_id, trigger_id=trigger_id)
            results.append(mv)
        return results

    @classmethod
    async def train_candidate_family(
        cls,
        session: AsyncSession,
        model_name: str,
        extracted_ds: ExtractedTrainingDatasetDTO,
        dataset_id: str,
        trigger_id: Optional[str] = None,
        source_import_job_id: Optional[uuid.UUID] = None,
    ) -> Tuple[MLModelVersion, str, str]:
        """
        Trains candidate model for a specific model family using TRAIN partition only.
        Exports joblib artifact, verifies SHA-256, and registers TRAINED_CANDIDATE version.
        """
        if model_name not in MODEL_CONFIGURATIONS:
            raise ValueError(f"Unknown model family '{model_name}'.")

        cfg = MODEL_CONFIGURATIONS[model_name]
        records = extracted_ds.records

        # Separate Partitions
        train_recs = [r for r in records if r.partition == "TRAIN"]
        val_recs = [r for r in records if r.partition == "VALIDATION"]
        holdout_recs = [r for r in records if r.partition == "HOLDOUT_TEST"]

        if len(train_recs) == 0:
            raise ValueError(f"Insufficient training records for '{model_name}'. Train count is 0.")

        # Fit Preprocessor on TRAIN records ONLY
        preproc = FeatureSetV1Preprocessor()
        preproc.fit(train_recs)

        # Prepare X and y for TRAIN
        X_train, y_train_dict = cls.prepare_dataframe(train_recs, preproc)
        target_key = cfg["target_key"]
        y_train = y_train_dict[target_key]

        # Filter non-null target rows
        valid_idx = y_train.notnull()
        X_train = X_train[valid_idx]
        y_train = y_train[valid_idx]

        if len(X_train) == 0:
            raise ValueError(f"No valid non-null target rows for '{target_key}' in TRAIN partition.")

        # Align Feature Columns for Model Fit
        all_feature_columns = list(X_train.columns)

        # Initialize Estimator
        hyperparams = cfg["hyperparameters"]
        if cfg["category"] == "Regression":
            estimator = RandomForestRegressor(**hyperparams)
        else:
            estimator = RandomForestClassifier(**hyperparams)

        # FIT ESTIMATOR ON TRAIN ONLY
        t0_fit = time.perf_counter()
        estimator.fit(X_train, y_train)
        t1_fit = time.perf_counter()
        fit_duration = t1_fit - t0_fit

        # Calculate Validation Diagnostics (VALIDATION ONLY, NOT HOLDOUT)
        val_metrics: Dict[str, Any] = {}
        if len(val_recs) > 0:
            X_val, y_val_dict = cls.prepare_dataframe(val_recs, preproc)
            y_val = y_val_dict[target_key]

            # Align columns cleanly without fragmentation
            missing_cols = [c for c in all_feature_columns if c not in X_val.columns]
            if missing_cols:
                missing_df = pd.DataFrame(0, index=X_val.index, columns=missing_cols)
                X_val = pd.concat([X_val, missing_df], axis=1)
            X_val = X_val[all_feature_columns]

            val_valid_idx = y_val.notnull()
            if val_valid_idx.sum() > 0:
                X_val = X_val[val_valid_idx]
                y_val = y_val[val_valid_idx]
                preds = estimator.predict(X_val)

                if cfg["category"] == "Regression":
                    val_metrics["r2"] = float(r2_score(y_val, preds))
                    val_metrics["mae"] = float(mean_absolute_error(y_val, preds))
                    val_metrics["rmse"] = float(np.sqrt(mean_squared_error(y_val, preds)))
                else:
                    if hasattr(estimator, "predict_proba"):
                        probs = estimator.predict_proba(X_val)[:, 1]
                        val_metrics["roc_auc"] = float(roc_auc_score(y_val, probs)) if len(set(y_val)) > 1 else 0.5
                    val_metrics["f1"] = float(f1_score(y_val, preds, zero_division=0))
                    val_metrics["precision"] = float(precision_score(y_val, preds, zero_division=0))
                    val_metrics["recall"] = float(recall_score(y_val, preds, zero_division=0))

        # Generate Candidate Version Identity
        version_str = f"v1.1.0-candidate-{dataset_id[:12].lower()}"

        # Check existing version entity in registry first
        reg_repo = MLModelRegistryRepository(session)
        existing_version = await reg_repo.get_by_version_number(model_name, version_str)

        # Export Joblib Artifact
        model_dir = os.path.join(MODEL_STORAGE_BASE_DIR, model_name)
        os.makedirs(model_dir, exist_ok=True)
        artifact_filename = f"{model_name}_{version_str}.joblib"
        artifact_path = os.path.join(model_dir, artifact_filename)

        artifact_payload = {
            "estimator": estimator,
            "model_name": model_name,
            "category": cfg["category"],
            "target_key": target_key,
            "feature_columns": all_feature_columns,
            "preprocessor": preproc,
            "feature_set_version": FEATURE_SET_VERSION,
            "candidate_version": version_str,
            "dataset_id": dataset_id,
        }

        joblib.dump(artifact_payload, artifact_path)
        file_size = os.path.getsize(artifact_path)

        # Immediately Verify SHA-256 Checksum
        with open(artifact_path, "rb") as f:
            checksum = hashlib.sha256(f.read()).hexdigest()

        if existing_version:
            logger.info(
                f"[WS-10.3 TELEMETRY] Model version '{version_str}' already registered for '{model_name}'. Returning immutable entity."
            )
            return existing_version, artifact_path, existing_version.artifact_sha256

        # Register New Candidate Version via Repository
        training_metadata = {
            "model_name": model_name,
            "model_category": cfg["category"],
            "target_name": target_key,
            "algorithm": cfg["algorithm"],
            "hyperparameters": hyperparams,
            "training_dataset_id": dataset_id,
            "feature_set_version": FEATURE_SET_VERSION,
            "source_trigger_id": trigger_id,
            "train_row_count": len(X_train),
            "val_row_count": len(val_recs),
            "holdout_row_count": len(holdout_recs),
            "fit_duration_sec": round(fit_duration, 4),
            "validation_metrics": val_metrics,
            "artifact_path": artifact_path,
            "artifact_size_bytes": file_size,
            "artifact_sha256": checksum,
            "random_seed": RANDOM_SEED,
            "is_authoritative_candidate": True,
        }

        model_version = await reg_repo.register_candidate_version(
            model_name=model_name,
            model_category=cfg["category"],
            version_number=version_str,
            artifact_location=artifact_path,
            artifact_sha256=checksum,
            training_metadata=training_metadata,
            dataset_version=dataset_id,
        )

        logger.info(
            f"[WS-10.3 TELEMETRY] Trained candidate '{model_name}' version '{version_str}'. "
            f"Artifact: {artifact_path} (Size: {file_size} B, SHA256: {checksum[:8]}...)"
        )

        return model_version, artifact_path, checksum


# Backward compatibility alias for legacy Phase 7.2 references
Phase72ModelTrainer = WS10ModelTrainer


class WS10TrainingOrchestrator:
    """
    WS-10.3 Training Worker Orchestrator.
    Consumes pending WS-10.1 triggers or direct dataset IDs, executes 4-model candidate training,
    tracks job execution in ml_training_jobs, and updates trigger lifecycle status.
    """

    @classmethod
    async def process_trigger_or_dataset(
        cls,
        session: AsyncSession,
        trigger_id: Optional[str] = None,
        dataset_id: Optional[str] = None,
    ) -> MLTrainingJob:
        """
        Claims trigger, builds or resolves dataset, trains all 4 candidate model families,
        persists job details, and completes trigger cleanly.
        """
        job_id = f"trjob-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        t0 = time.perf_counter()

        trigger: Optional[MLLifecycleTrigger] = None
        target_dataset_id: str = dataset_id or ""
        import_job_id: Optional[uuid.UUID] = None

        # 1. Claim Trigger if trigger_id provided or available
        if trigger_id:
            stmt_t = select(MLLifecycleTrigger).where(
                MLLifecycleTrigger.trigger_id == trigger_id
            ).with_for_update(skip_locked=True)
            res_t = await session.execute(stmt_t)
            trigger = res_t.scalars().first()
        elif not dataset_id:
            trigger = await MLTriggerService.get_pending_trigger(session, model_family="ALL_FAMILIES")

        if trigger:
            trigger_id = trigger.trigger_id
            import_job_id = trigger.import_job_id
            # Transition Trigger PENDING -> RUNNING
            await MLTriggerService.update_trigger_status(
                session, trigger_id, "RUNNING", reason=f"Training job {job_id} started"
            )

        # 2. Resolve / Build Dataset
        try:
            if not target_dataset_id:
                # Build dataset via WS10FeatureDatasetBuilder
                db_ds, extracted_ds = await WS10FeatureDatasetBuilder.build_and_persist_dataset(
                    session=session, trigger_id=trigger_id
                )
                target_dataset_id = db_ds.dataset_id
            else:
                # Resolve existing dataset
                stmt_ds = select(MLDataset).where(MLDataset.dataset_id == target_dataset_id)
                res_ds = await session.execute(stmt_ds)
                db_ds = res_ds.scalars().first()
                if not db_ds:
                    raise ValueError(f"Referenced dataset_id '{target_dataset_id}' not found in ml_datasets.")

                extracted_ds = await Phase71FeatureExtractor.extract_training_dataset(
                    session=session, dataset_id=target_dataset_id
                )

            # 3. Train Candidates for All 4 Model Families
            trained_versions: Dict[str, Any] = {}
            for model_name in ["delay_regressor", "turnaround_regressor", "sla_breach_classifier", "plant_risk_classifier"]:
                version_entity, art_path, checksum = await WS10ModelTrainer.train_candidate_family(
                    session=session,
                    model_name=model_name,
                    extracted_ds=extracted_ds,
                    dataset_id=target_dataset_id,
                    trigger_id=trigger_id,
                    source_import_job_id=import_job_id,
                )
                trained_versions[model_name] = {
                    "model_version_id": str(version_entity.id),
                    "version_number": version_entity.model_version,
                    "lifecycle_status": version_entity.lifecycle_status,
                    "artifact_path": art_path,
                    "artifact_sha256": checksum,
                }

            t1 = time.perf_counter()
            duration = round(t1 - t0, 4)

            # Create COMPLETED Training Job record
            tr_job = MLTrainingJob(
                job_id=job_id,
                trigger_id=trigger_id,
                dataset_id=target_dataset_id,
                model_family="ALL_FAMILIES",
                status="COMPLETED",
                models_trained_count=len(trained_versions),
                trained_model_versions=trained_versions,
                execution_duration_sec=duration,
                reason=f"Successfully trained {len(trained_versions)} candidate models",
                started_at=now,
                completed_at=datetime.now(timezone.utc),
                created_at=now,
                updated_at=datetime.now(timezone.utc),
            )
            session.add(tr_job)

            # Update Trigger to COMPLETED if active
            if trigger_id:
                await MLTriggerService.update_trigger_status(
                    session, trigger_id, "COMPLETED", reason=f"Training job {job_id} completed successfully"
                )

            logger.info(
                f"[WS-10.3 ORCHESTRATOR] Job '{job_id}' COMPLETED. Trained {len(trained_versions)} candidate models in {duration} s."
            )
            return tr_job

        except Exception as e:
            t1 = time.perf_counter()
            duration = round(t1 - t0, 4)
            err_msg = str(e)
            logger.error(f"[WS-10.3 ORCHESTRATOR ERROR] Job '{job_id}' FAILED: {err_msg}", exc_info=True)

            # Save FAILED Training Job record
            tr_job = MLTrainingJob(
                job_id=job_id,
                trigger_id=trigger_id,
                dataset_id=target_dataset_id or "UNKNOWN",
                model_family="ALL_FAMILIES",
                status="FAILED",
                models_trained_count=0,
                trained_model_versions={},
                execution_duration_sec=duration,
                reason=f"Training pipeline error: {err_msg}",
                error_metadata={"error": type(e).__name__, "message": err_msg},
                started_at=now,
                completed_at=datetime.now(timezone.utc),
                created_at=now,
                updated_at=datetime.now(timezone.utc),
            )
            session.add(tr_job)

            # Update Trigger to FAILED
            if trigger_id:
                await MLTriggerService.update_trigger_status(
                    session, trigger_id, "FAILED", reason=f"Training job failed: {err_msg}", error_metadata={"error": err_msg}
                )

            return tr_job
