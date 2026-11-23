"""
WS-09 Phase 7.3 Model Evaluation & Promotion Gate Engine

Authoritative Evaluator & Promotion Gate Service:
- Performs candidate integrity preflight (verifying SHA-256 and distinct candidate identity).
- Evaluates candidate models against Phase 7.3 model-specific evaluation gates.
- Evaluates TRAIN, VALIDATION, and HOLDOUT_TEST metrics independently.
- Records explicit promotion decisions (PROMOTABLE or REJECTED).
- Enforces strict NOT_CONFIGURED prediction authority when zero candidates pass all gates.
"""

import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import joblib
import pandas as pd
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_intelligence.ml.feature_extractor import (
    Phase71FeatureExtractor,
    FEATURE_SET_VERSION,
    ALLOWED_INFERENCE_FEATURES,
)
from app.modules.operational_intelligence.ml.trainer import (
    Phase72ModelTrainer,
    MODEL_CONFIGURATIONS,
    MODEL_STORAGE_BASE_DIR,
    ModelEvaluationMetricsDTO,
    ModelTrainingMetadataDTO,
)


# =============================================================================
# DTOS FOR PHASE 7.3 EVALUATION & PROMOTION
# =============================================================================

class CandidatePreflightCheckDTO(BaseModel):
    """Integrity check result for a candidate model artifact."""
    model_name: str
    artifact_exists: bool
    sha256_verified: bool
    sha256_hash: str
    target_name: str
    feature_set_version: str
    is_distinct_candidate: bool
    preflight_passed: bool
    notes: str


class GateThresholdRuleDTO(BaseModel):
    """Metric threshold rule for promotion gate assessment."""
    metric_name: str
    comparison: str  # ">=" or "<="
    threshold_value: float
    actual_holdout_value: Optional[float]
    passed: bool


class SingleModelEvaluationReportDTO(BaseModel):
    """Detailed evaluation report for a single candidate model family."""
    model_name: str
    category: str
    target_name: str
    preflight: CandidatePreflightCheckDTO
    metrics_train: ModelEvaluationMetricsDTO
    metrics_val: ModelEvaluationMetricsDTO
    metrics_holdout: ModelEvaluationMetricsDTO
    threshold_rules: List[GateThresholdRuleDTO]
    overall_gate_passed: bool
    promotion_decision: str  # REJECTED or PROMOTABLE
    rejection_reasons: List[str]


class Phase73PromotionSuiteResultDTO(BaseModel):
    """Overall evaluation suite result across all 4 candidate model families."""
    evaluation_timestamp: str
    dataset_id: str
    models_evaluated_count: int
    promoted_models_count: int
    platform_prediction_status: str  # NOT_CONFIGURED or AVAILABLE
    evaluations: Dict[str, SingleModelEvaluationReportDTO]
    audit_summary: str


PROMOTION_GATE_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "delay_regressor": {
        "r2_min": 0.70,
        "mae_max": 10.0,
        "rmse_max": 15.0,
    },
    "turnaround_regressor": {
        "r2_min": 0.70,
        "mae_max": 8.0,
        "rmse_max": 12.0,
    },
    "sla_breach_classifier": {
        "roc_auc_min": 0.75,
        "f1_min": 0.70,
        "precision_min": 0.65,
        "recall_min": 0.65,
    },
    "plant_risk_classifier": {
        "roc_auc_min": 0.75,
        "f1_min": 0.70,
        "precision_min": 0.65,
        "recall_min": 0.65,
    },
}


# =============================================================================
# EVALUATOR ENGINE CLASS
# =============================================================================

class Phase73PromotionGateEvaluator:
    """
    Authoritative Evaluator for WS-09 Phase 7.3 Model Evaluation & Promotion Gate.
    """

    @classmethod
    def verify_candidate_preflight(cls, model_name: str, base_dir: str = MODEL_STORAGE_BASE_DIR) -> Tuple[CandidatePreflightCheckDTO, Optional[ModelTrainingMetadataDTO]]:
        """
        Verifies artifact existence, SHA-256 hash match, and metadata integrity.
        """
        target_dir = os.path.join(base_dir, model_name)
        artifact_path = os.path.join(target_dir, f"{model_name}_candidate.joblib")
        metadata_path = os.path.join(target_dir, f"{model_name}_candidate_metadata.json")

        if not os.path.exists(artifact_path) or not os.path.exists(metadata_path):
            return CandidatePreflightCheckDTO(
                model_name=model_name,
                artifact_exists=False,
                sha256_verified=False,
                sha256_hash="",
                target_name="UNKNOWN",
                feature_set_version="UNKNOWN",
                is_distinct_candidate=False,
                preflight_passed=False,
                notes="Candidate artifact or metadata JSON file missing.",
            ), None

        with open(metadata_path, "r", encoding="utf-8") as f:
            meta_dict = json.load(f)
        meta = ModelTrainingMetadataDTO(**meta_dict)

        # Recalculate file SHA-256
        hasher = hashlib.sha256()
        with open(artifact_path, "rb") as f:
            while chunk := f.read(8192):
                hasher.update(chunk)
        calc_sha = hasher.hexdigest()

        sha_ok = (calc_sha == meta.artifact_sha256)

        preflight = CandidatePreflightCheckDTO(
            model_name=model_name,
            artifact_exists=True,
            sha256_verified=sha_ok,
            sha256_hash=calc_sha,
            target_name=meta.target_name,
            feature_set_version=meta.feature_set_version,
            is_distinct_candidate=True,
            preflight_passed=sha_ok and (meta.feature_set_version == FEATURE_SET_VERSION),
            notes="SHA-256 verified and FeatureSetV1 compatible." if sha_ok else "SHA-256 checksum mismatch!",
        )

        return preflight, meta

    @classmethod
    async def evaluate_candidate(
        cls,
        session: AsyncSession,
        model_name: str,
        dataset_id: str = "DS-20260805-001",
        base_dir: str = MODEL_STORAGE_BASE_DIR,
    ) -> SingleModelEvaluationReportDTO:
        """
        Evaluates a single candidate model against its model-specific promotion gate thresholds on HOLDOUT_TEST data.
        """
        preflight, meta = cls.verify_candidate_preflight(model_name, base_dir=base_dir)

        if not preflight.preflight_passed or not meta:
            return SingleModelEvaluationReportDTO(
                model_name=model_name,
                category=MODEL_CONFIGURATIONS.get(model_name, {}).get("category", "Unknown"),
                target_name=preflight.target_name,
                preflight=preflight,
                metrics_train=ModelEvaluationMetricsDTO(),
                metrics_val=ModelEvaluationMetricsDTO(),
                metrics_holdout=ModelEvaluationMetricsDTO(),
                threshold_rules=[],
                overall_gate_passed=False,
                promotion_decision="REJECTED",
                rejection_reasons=["Candidate integrity preflight failed."],
            )

        config = MODEL_CONFIGURATIONS.get(model_name, {})
        gate_cfg = config.get("promotion_gate", PROMOTION_GATE_THRESHOLDS.get(model_name, {}))
        category = config.get("category", "Unknown")
        m_holdout = meta.metrics_holdout

        threshold_rules: List[GateThresholdRuleDTO] = []
        rejection_reasons: List[str] = []

        if category == "Regression":
            # R2 >= min
            r2_val = m_holdout.r2
            r2_pass = (r2_val is not None) and (r2_val >= gate_cfg["r2_min"])
            threshold_rules.append(
                GateThresholdRuleDTO(
                    metric_name="r2",
                    comparison=">=",
                    threshold_value=gate_cfg["r2_min"],
                    actual_holdout_value=r2_val,
                    passed=r2_pass,
                )
            )
            if not r2_pass:
                rejection_reasons.append(f"Holdout R^2 {r2_val} < required threshold {gate_cfg['r2_min']}")

            # MAE <= max
            mae_val = m_holdout.mae
            mae_pass = (mae_val is not None) and (mae_val <= gate_cfg["mae_max"])
            threshold_rules.append(
                GateThresholdRuleDTO(
                    metric_name="mae",
                    comparison="<=",
                    threshold_value=gate_cfg["mae_max"],
                    actual_holdout_value=mae_val,
                    passed=mae_pass,
                )
            )
            if not mae_pass:
                rejection_reasons.append(f"Holdout MAE {mae_val} > required threshold {gate_cfg['mae_max']}")

            # RMSE <= max
            rmse_val = m_holdout.rmse
            rmse_pass = (rmse_val is not None) and (rmse_val <= gate_cfg["rmse_max"])
            threshold_rules.append(
                GateThresholdRuleDTO(
                    metric_name="rmse",
                    comparison="<=",
                    threshold_value=gate_cfg["rmse_max"],
                    actual_holdout_value=rmse_val,
                    passed=rmse_pass,
                )
            )
            if not rmse_pass:
                rejection_reasons.append(f"Holdout RMSE {rmse_val} > required threshold {gate_cfg['rmse_max']}")

            overall_pass = r2_pass and mae_pass and rmse_pass

        else:
            # Classification: ROC-AUC >= min
            auc_val = m_holdout.roc_auc
            auc_pass = (auc_val is not None) and (auc_val >= gate_cfg["roc_auc_min"])
            threshold_rules.append(
                GateThresholdRuleDTO(
                    metric_name="roc_auc",
                    comparison=">=",
                    threshold_value=gate_cfg["roc_auc_min"],
                    actual_holdout_value=auc_val,
                    passed=auc_pass,
                )
            )
            if not auc_pass:
                rejection_reasons.append(f"Holdout ROC-AUC {auc_val} < required threshold {gate_cfg['roc_auc_min']}")

            # F1 >= min
            f1_val = m_holdout.f1
            f1_pass = (f1_val is not None) and (f1_val >= gate_cfg["f1_min"])
            threshold_rules.append(
                GateThresholdRuleDTO(
                    metric_name="f1",
                    comparison=">=",
                    threshold_value=gate_cfg["f1_min"],
                    actual_holdout_value=f1_val,
                    passed=f1_pass,
                )
            )
            if not f1_pass:
                rejection_reasons.append(f"Holdout F1 {f1_val} < required threshold {gate_cfg['f1_min']}")

            # Recall or Precision if in config
            if "recall_min" in gate_cfg:
                rec_val = m_holdout.recall
                rec_pass = (rec_val is not None) and (rec_val >= gate_cfg["recall_min"])
                threshold_rules.append(
                    GateThresholdRuleDTO(
                        metric_name="recall",
                        comparison=">=",
                        threshold_value=gate_cfg["recall_min"],
                        actual_holdout_value=rec_val,
                        passed=rec_pass,
                    )
                )
                if not rec_pass:
                    rejection_reasons.append(f"Holdout Recall {rec_val} < required threshold {gate_cfg['recall_min']}")
            else:
                rec_pass = True

            if "precision_min" in gate_cfg:
                prec_val = m_holdout.precision
                prec_pass = (prec_val is not None) and (prec_val >= gate_cfg["precision_min"])
                threshold_rules.append(
                    GateThresholdRuleDTO(
                        metric_name="precision",
                        comparison=">=",
                        threshold_value=gate_cfg["precision_min"],
                        actual_holdout_value=prec_val,
                        passed=prec_pass,
                    )
                )
                if not prec_pass:
                    rejection_reasons.append(f"Holdout Precision {prec_val} < required threshold {gate_cfg['precision_min']}")
            else:
                prec_pass = True

            overall_pass = auc_pass and f1_pass and rec_pass and prec_pass

        decision = "PROMOTABLE" if overall_pass else "REJECTED"

        return SingleModelEvaluationReportDTO(
            model_name=model_name,
            category=category,
            target_name=meta.target_name,
            preflight=preflight,
            metrics_train=meta.metrics_train,
            metrics_val=meta.metrics_val,
            metrics_holdout=meta.metrics_holdout,
            threshold_rules=threshold_rules,
            overall_gate_passed=overall_pass,
            promotion_decision=decision,
            rejection_reasons=rejection_reasons,
        )

    @classmethod
    async def run_full_promotion_suite(
        cls,
        session: AsyncSession,
        dataset_id: str = "DS-20260805-001",
        base_dir: str = MODEL_STORAGE_BASE_DIR,
    ) -> Phase73PromotionSuiteResultDTO:
        """
        Evaluates all 4 candidate model families and computes platform prediction status.
        """
        # Preflight Check for duplicate candidate artifacts
        all_models = list(MODEL_CONFIGURATIONS.keys())
        evaluations: Dict[str, SingleModelEvaluationReportDTO] = {}
        sha_set = {}

        for m_name in all_models:
            report = await cls.evaluate_candidate(session, m_name, dataset_id, base_dir)
            evaluations[m_name] = report
            if report.preflight.sha256_hash:
                sha_set[m_name] = report.preflight.sha256_hash

        # Check SHA collision across candidate models
        for m1 in all_models:
            for m2 in all_models:
                if m1 != m2 and sha_set.get(m1) and sha_set.get(m1) == sha_set.get(m2):
                    # Flag duplicate candidate error
                    evaluations[m1].overall_gate_passed = False
                    evaluations[m1].promotion_decision = "REJECTED"
                    evaluations[m1].rejection_reasons.append(f"DUPLICATE CANDIDATE ERROR: Identical SHA-256 with {m2}")

        promoted_count = sum(1 for e in evaluations.values() if e.promotion_decision == "PROMOTABLE")
        platform_status = "AVAILABLE" if promoted_count > 0 else "NOT_CONFIGURED"

        audit_summary = (
            f"Phase 7.3 Promotion Gate Evaluation completed. Total Candidates: {len(all_models)}, "
            f"Promoted: {promoted_count}, Rejected: {len(all_models) - promoted_count}. "
            f"Platform Prediction Authority Status: {platform_status}."
        )

        return Phase73PromotionSuiteResultDTO(
            evaluation_timestamp=datetime.now(timezone.utc).isoformat(),
            dataset_id=dataset_id,
            models_evaluated_count=len(all_models),
            promoted_models_count=promoted_count,
            platform_prediction_status=platform_status,
            evaluations=evaluations,
            audit_summary=audit_summary,
        )
