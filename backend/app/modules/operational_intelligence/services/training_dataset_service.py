"""
WS-10 Phase 5.5 Historical Verified Dataset Builder Service
Enforces strict eligibility, leakage governance, quality gates, content hashing, and row-level lineage.
"""

import uuid
import hashlib
import json
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_intelligence.models.operational_outcome import OperationalOutcome
from app.modules.operational_intelligence.models.prediction_error import PredictionErrorRecord
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.training_dataset import (
    HistoricalTrainingDataset,
    HistoricalTrainingDatasetRow,
)
from app.modules.operational_intelligence.repositories.training_dataset_repository import TrainingDatasetRepository

# Non-negotiable Leakage Protection Contract
FORBIDDEN_LEAKAGE_FIELDS = {
    "t1_transit_mins",
    "t2b_unloading_mins",
    "actual_sla_breach_flag",
    "actual_plant_risk_class",
    "actual_financial_impact_inr",
    "actual_travel_time_mins",
    "actual_turnaround_time_mins",
    "realized_delay_mins",
    "realized_turnaround_mins",
}

DEFAULT_MIN_SAMPLE_COUNT = 10


class TrainingDatasetService:
    """Production-grade service for constructing versioned historical training datasets."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = TrainingDatasetRepository(session)

    @staticmethod
    def compute_dataset_content_hash(
        rows_data: List[Dict[str, Any]],
        model_family: str = "delay_regressor",
        feature_set_version: str = "FeatureSetV1",
        dataset_version: str = "v1.0.0",
        target_name: Optional[str] = None,
    ) -> str:
        """Deterministically calculate SHA-256 hash over model-family specific canonical representation."""
        sorted_rows = sorted(rows_data, key=lambda r: (str(r.get("outcome_id", "")), int(r.get("row_index", 0))))
        hash_payload = {
            "model_family": model_family,
            "feature_set_version": feature_set_version,
            "dataset_version": dataset_version,
            "target_name": target_name or model_family,
            "rows": sorted_rows,
        }
        canonical_str = json.dumps(hash_payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

    @staticmethod
    def construct_idempotency_key(
        model_family: str,
        feature_set_version: str,
        scope_type: str,
        scope_id: Optional[str],
        dataset_version: str,
        source_start: datetime,
        source_end: datetime,
        content_hash: str,
    ) -> str:
        """Construct deterministic idempotency key for dataset identity."""
        start_str = source_start.strftime("%Y%m%dT%H%M%SZ")
        end_str = source_end.strftime("%Y%m%dT%H%M%SZ")
        scope_str = scope_id or "GLOBAL"
        return f"IK-DS-{model_family}-{feature_set_version}-{scope_type}-{scope_str}-{dataset_version}-{start_str}-{end_str}-{content_hash[:12]}"

    async def generate_and_persist_dataset(
        self,
        model_family: str,
        source_time_range_start: datetime,
        source_time_range_end: datetime,
        evaluation_cutoff: datetime,
        model_version_id: Optional[str] = None,
        feature_set_version: str = "FeatureSetV1",
        scope_type: str = "GLOBAL",
        scope_id: Optional[str] = None,
        dataset_version: str = "v1.0.0",
        min_sample_count: int = DEFAULT_MIN_SAMPLE_COUNT,
        force_recompute: bool = False,
    ) -> HistoricalTrainingDataset:
        """
        Build, validate, hash, and persist an immutable historical training dataset.
        Enforces 100% data eligibility and quality gate governance.
        """
        # Ensure UTC timezone
        if source_time_range_start.tzinfo is None:
            source_time_range_start = source_time_range_start.replace(tzinfo=timezone.utc)
        if source_time_range_end.tzinfo is None:
            source_time_range_end = source_time_range_end.replace(tzinfo=timezone.utc)
        if evaluation_cutoff.tzinfo is None:
            evaluation_cutoff = evaluation_cutoff.replace(tzinfo=timezone.utc)

        # 1. Query Eligible Non-Superseded Verified Outcomes & Lineage
        stmt = (
            select(
                OperationalOutcome,
                PredictionErrorRecord,
                MLPredictionSnapshot,
                MLModelVersion,
            )
            .join(MLPredictionSnapshot, OperationalOutcome.prediction_snapshot_id == MLPredictionSnapshot.prediction_snapshot_id)
            .join(MLModelVersion, MLPredictionSnapshot.model_version_id == MLModelVersion.id)
            .outerjoin(PredictionErrorRecord, OperationalOutcome.outcome_id == PredictionErrorRecord.outcome_id)
            .where(
                # Outcome Eligibility
                OperationalOutcome.verification_status == "VERIFIED",
                OperationalOutcome.is_verified == True,
                OperationalOutcome.is_superseded == False,
                OperationalOutcome.created_at >= source_time_range_start,
                OperationalOutcome.created_at <= source_time_range_end,
                OperationalOutcome.created_at <= evaluation_cutoff,
                # Snapshot Authority
                MLPredictionSnapshot.is_stale == False,
                MLPredictionSnapshot.is_deleted == False,
                # Model Version Authority
                MLModelVersion.model_name == model_family,
                MLModelVersion.lifecycle_status == "PROMOTED",
                MLModelVersion.is_deleted == False,
            )
        )

        if model_version_id:
            stmt = stmt.where(MLModelVersion.id == model_version_id)

        # Exclude fixture/test data
        stmt = stmt.where(
            ~OperationalOutcome.outcome_id.like("%FIX%"),
            ~OperationalOutcome.outcome_id.like("%TEST%"),
            ~MLPredictionSnapshot.prediction_snapshot_id.like("%FIX%"),
            ~MLPredictionSnapshot.prediction_snapshot_id.like("%TEST%"),
        )

        stmt = stmt.order_by(OperationalOutcome.created_at.asc())
        result = await self.session.execute(stmt)
        query_rows = result.all()

        # 2. Process Rows & Enforce Leakage Guard
        prepared_dataset_rows: List[HistoricalTrainingDatasetRow] = []
        canonical_hash_items: List[Dict[str, Any]] = []
        source_outcome_ids: List[str] = []
        source_error_ids: List[str] = []
        source_snapshot_ids: List[str] = []

        leakage_violations_count = 0
        unknown_records_count = 0

        for idx, (outcome, err_rec, snapshot, model_ver) in enumerate(query_rows, start=1):
            source_outcome_ids.append(outcome.outcome_id)
            if snapshot.prediction_snapshot_id not in source_snapshot_ids:
                source_snapshot_ids.append(snapshot.prediction_snapshot_id)
            if err_rec and err_rec.error_record_id not in source_error_ids:
                source_error_ids.append(err_rec.error_record_id)

            # Check for unknown / unclassified records
            if not outcome.outcome_id or not snapshot.prediction_snapshot_id:
                unknown_records_count += 1
                continue

            # Extract features from snapshot input_features
            snapshot_features = dict(snapshot.input_features or {})
            
            # Check Leakage Guard
            found_forbidden = FORBIDDEN_LEAKAGE_FIELDS.intersection(set(snapshot_features.keys()))
            if found_forbidden:
                leakage_violations_count += 1
                continue

            # Construct Label based on Model Family
            label_json: Dict[str, Any] = {}
            label_numeric: Optional[Decimal] = None
            label_class: Optional[int] = None

            if model_family == "delay_regressor":
                label_val = float(outcome.actual_transit_mins or 0.0)
                label_numeric = Decimal(str(round(label_val, 4)))
                label_json = {"target_type": "continuous", "label_name": "actual_transit_mins", "value": label_val}
            elif model_family == "turnaround_regressor":
                label_val = float((outcome.actual_transit_mins or 0.0) + (outcome.actual_unloading_mins or 0.0))
                label_numeric = Decimal(str(round(label_val, 4)))
                label_json = {"target_type": "continuous", "label_name": "turnaround_mins", "value": label_val}
            elif model_family == "sla_breach_classifier":
                label_val = 1 if outcome.actual_sla_breach_flag else 0
                label_class = label_val
                label_numeric = Decimal(str(label_val))
                label_json = {"target_type": "binary", "label_name": "actual_sla_breach_flag", "value": label_val}
            elif model_family == "plant_risk_classifier":
                # Preserves 0 NORMAL, 1 MODERATE, 2 SEVERE (Multiclass)
                label_val = outcome.actual_plant_risk_class if outcome.actual_plant_risk_class is not None else 0
                label_class = label_val
                label_numeric = Decimal(str(label_val))
                label_json = {"target_type": "multiclass", "label_name": "actual_plant_risk_class", "value": label_val}
            else:
                label_val = float(outcome.actual_transit_mins or 0.0)
                label_numeric = Decimal(str(round(label_val, 4)))
                label_json = {"target_type": "continuous", "label_name": "value", "value": label_val}

            # Realized financial impact (preserving NULL!)
            financial_impact = outcome.actual_financial_impact_inr

            # Row Lineage Entity
            row_entity = HistoricalTrainingDatasetRow(
                row_index=idx,
                outcome_id=outcome.outcome_id,
                prediction_error_record_id=err_rec.error_record_id if err_rec else None,
                prediction_snapshot_id=snapshot.prediction_snapshot_id,
                model_version_id=str(model_ver.id),
                dispatch_id=str(outcome.dispatch_id) if outcome.dispatch_id else None,
                features_json=snapshot_features,
                label_json=label_json,
                label_numeric=label_numeric,
                label_class=label_class,
                realized_financial_impact_inr=financial_impact,
            )
            prepared_dataset_rows.append(row_entity)

            # Canonical Item for Content Hash
            canonical_hash_items.append({
                "row_index": idx,
                "outcome_id": outcome.outcome_id,
                "features": snapshot_features,
                "label": label_json,
            })

        # 3. Compute Content Hash & Idempotency Key
        content_hash = self.compute_dataset_content_hash(
            model_family=model_family,
            feature_set_version=feature_set_version,
            dataset_version=dataset_version,
            rows_data=canonical_hash_items,
        )
        idempotency_key = self.construct_idempotency_key(
            model_family=model_family,
            feature_set_version=feature_set_version,
            scope_type=scope_type,
            scope_id=scope_id,
            dataset_version=dataset_version,
            source_start=source_time_range_start,
            source_end=source_time_range_end,
            content_hash=content_hash,
        )

        # 4. Check Existing Dataset (Idempotency / Re-computation)
        existing_dataset = await self.repo.get_by_idempotency_key(idempotency_key)
        if existing_dataset and not force_recompute:
            return existing_dataset

        # Handle Supersession if force_recompute is True
        superseded_dataset_id: Optional[str] = None
        if existing_dataset and force_recompute:
            new_superseded_id = f"DS-{uuid.uuid4().hex[:8].upper()}"
            existing_dataset.is_superseded = True
            existing_dataset.superseded_by_dataset_id = new_superseded_id
            existing_dataset.idempotency_key = f"{existing_dataset.idempotency_key}-SUPERSEDE-{uuid.uuid4().hex[:6]}"
            superseded_dataset_id = new_superseded_id
            await self.session.flush()

        # 5. Evaluate Quality Gates
        total_rows = len(prepared_dataset_rows)
        quality_gate_passed = True
        rejection_reasons: List[str] = []

        if total_rows < min_sample_count:
            quality_gate_passed = False
            rejection_reasons.append(f"SAMPLE_COUNT_BELOW_MINIMUM: {total_rows} < {min_sample_count}")

        if leakage_violations_count > 0:
            quality_gate_passed = False
            rejection_reasons.append(f"LEAKAGE_VIOLATIONS_DETECTED: {leakage_violations_count}")

        if unknown_records_count > 0:
            quality_gate_passed = False
            rejection_reasons.append(f"UNKNOWN_RECORDS_DETECTED: {unknown_records_count}")

        dataset_status = "READY_FOR_TRAINING" if quality_gate_passed else "REJECTED"
        rejection_str = "; ".join(rejection_reasons) if rejection_reasons else None

        generated_dataset_id = f"DS-{uuid.uuid4().hex[:8].upper()}"

        # Capped Summary JSONB Lineage (Max 1000 IDs)
        capped_outcomes = source_outcome_ids[:1000]
        lineage_summary = {
            "source_outcome_ids": capped_outcomes,
            "truncated": len(source_outcome_ids) > 1000,
            "total_outcomes": len(source_outcome_ids),
            "total_errors": len(source_error_ids),
            "total_snapshots": len(source_snapshot_ids),
        }

        quality_metrics = {
            "min_sample_count": min_sample_count,
            "actual_row_count": total_rows,
            "leakage_violations_count": leakage_violations_count,
            "unknown_records_count": unknown_records_count,
            "quality_gate_passed": quality_gate_passed,
        }

        # 6. Create Dataset Entity
        dataset_entity = HistoricalTrainingDataset(
            dataset_id=generated_dataset_id,
            idempotency_key=idempotency_key,
            dataset_version=dataset_version,
            model_family=model_family,
            feature_set_version=feature_set_version,
            scope_type=scope_type,
            scope_id=scope_id,
            source_time_range_start=source_time_range_start,
            source_time_range_end=source_time_range_end,
            generation_timestamp=datetime.now(timezone.utc),
            evaluation_cutoff=evaluation_cutoff,
            total_row_count=total_rows,
            source_outcome_count=len(source_outcome_ids),
            source_error_count=len(source_error_ids),
            source_snapshot_count=len(source_snapshot_ids),
            validation_policy_version="WS55_QUALITY_GATE_V1",
            leakage_policy_version="FEATURE_SET_V1_STRICT_NO_LEAKAGE",
            code_version="v1.0.0-phase55-dataset-builder",
            dataset_content_hash=content_hash,
            dataset_status=dataset_status,
            quality_gate_passed=quality_gate_passed,
            rejection_reason=rejection_str,
            quality_metrics=quality_metrics,
            source_record_ids=lineage_summary,
            is_superseded=False,
        )

        return await self.repo.persist_dataset_with_rows(dataset_entity, prepared_dataset_rows)
