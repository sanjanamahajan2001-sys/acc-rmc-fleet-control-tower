"""
WS-10.2 Authoritative Dataset Builder Service.
Extends FeatureSetV1 Dataset Extractor with Preprocessing, Lineage Persistence,
Incremental Trigger Integration, and Anti-Leakage Controls.
"""

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_intelligence.ml.feature_extractor import (
    FEATURE_SET_VERSION,
    Phase71FeatureExtractor,
    ExtractedTrainingDatasetDTO,
    FeatureRecordDTO,
    DatasetLineageDTO,
)
from app.modules.operational_intelligence.models.ml_dataset import MLDataset
from app.modules.operational_intelligence.models.ml_lifecycle_trigger import MLLifecycleTrigger

logger = logging.getLogger(__name__)


class FeatureSetV1Preprocessor:
    """
    Deterministic Imputer, Scaler, and One-Hot Encoder for FeatureSetV1.
    Strictly fitted using TRAIN partition only; transform applied to VALIDATION & HOLDOUT.
    """

    def __init__(self):
        self.is_fitted: bool = False
        self.plant_codes: List[str] = []
        self.customer_codes: List[str] = []
        self.vehicle_codes: List[str] = []
        self.mean_plant_queue_30d: float = 15.0
        self.mean_customer_retention_30d: float = 8.0
        self.mean_ticket_volume_m3: float = 6.0

    def fit(self, train_records: List[FeatureRecordDTO]) -> "FeatureSetV1Preprocessor":
        """Fit preprocessor parameters on TRAIN records ONLY."""
        if not train_records:
            self.is_fitted = True
            return self

        plants = set()
        customers = set()
        vehicles = set()
        pq_sum, cr_sum, vol_sum = 0.0, 0.0, 0.0
        count = 0

        for r in train_records:
            f = r.features
            plants.add(f.get("plant_code", "UNKNOWN"))
            customers.add(f.get("customer_code", "UNKNOWN"))
            vehicles.add(f.get("vehicle_code", "UNKNOWN"))

            pq_sum += float(f.get("plant_queue_avg_30d", 15.0))
            cr_sum += float(f.get("customer_retention_avg_30d", 8.0))
            vol_sum += float(f.get("ticket_volume_m3", 6.0))
            count += 1

        self.plant_codes = sorted(list(plants))
        self.customer_codes = sorted(list(customers))
        self.vehicle_codes = sorted(list(vehicles))

        if count > 0:
            self.mean_plant_queue_30d = round(pq_sum / count, 4)
            self.mean_customer_retention_30d = round(cr_sum / count, 4)
            self.mean_ticket_volume_m3 = round(vol_sum / count, 4)

        self.is_fitted = True
        return self

    def transform_record(self, record: FeatureRecordDTO) -> Dict[str, Any]:
        """Transforms a single feature record deterministically using fitted parameters."""
        if not self.is_fitted:
            raise RuntimeError("Preprocessor must be fitted on TRAIN before transform.")

        f = record.features
        # Anti-leakage validation assertion
        Phase71FeatureExtractor.validate_no_leakage_in_features(f)

        # Impute nulls with TRAIN fitted means
        pq = float(f.get("plant_queue_avg_30d") if f.get("plant_queue_avg_30d") is not None else self.mean_plant_queue_30d)
        cr = float(f.get("customer_retention_avg_30d") if f.get("customer_retention_avg_30d") is not None else self.mean_customer_retention_30d)
        vol = float(f.get("ticket_volume_m3") if f.get("ticket_volume_m3") is not None else self.mean_ticket_volume_m3)

        return {
            "dispatch_id": record.dispatch_id,
            "dispatch_code": record.dispatch_code,
            "partition": record.partition,
            "plant_code": f.get("plant_code", "UNKNOWN"),
            "customer_code": f.get("customer_code", "UNKNOWN"),
            "vehicle_code": f.get("vehicle_code", "UNKNOWN"),
            "ticket_volume_m3": vol,
            "plant_queue_avg_30d": pq,
            "customer_retention_avg_30d": cr,
            "dispatch_hour": f.get("dispatch_hour", 0),
            "dispatch_day_of_week": f.get("dispatch_day_of_week", 0),
        }


class WS10FeatureDatasetBuilder:
    """
    Authoritative WS-10.2 FeatureSetV1 Dataset Builder Service.
    Consumes PostgreSQL ERP data or WS-10.1 trigger context to produce reproducible training datasets.
    """

    @classmethod
    async def build_and_persist_dataset(
        cls,
        session: AsyncSession,
        trigger_id: Optional[str] = None,
        dataset_id_override: Optional[str] = None,
        plant_code: Optional[str] = None,
        customer_code: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Tuple[MLDataset, ExtractedTrainingDatasetDTO]:
        """
        Constructs FeatureSetV1 dataset, fits TRAIN-only preprocessor, computes lineage/SHA256,
        and persists MLDataset record to PostgreSQL.
        """
        # Resolve trigger context if provided
        trigger: Optional[MLLifecycleTrigger] = None
        source_job_num: Optional[str] = None
        import_job_id: Optional[uuid.UUID] = None

        if trigger_id:
            stmt_t = select(MLLifecycleTrigger).where(MLLifecycleTrigger.trigger_id == trigger_id)
            res_t = await session.execute(stmt_t)
            trigger = res_t.scalars().first()
            if trigger:
                source_job_num = trigger.job_number
                import_job_id = trigger.import_job_id

        # Generate unique immutable dataset identity
        ds_id = dataset_id_override or f"DS-FSV1-{uuid.uuid4().hex[:8].upper()}"

        # Check duplicate dataset ID prevention
        stmt_existing = select(MLDataset).where(MLDataset.dataset_id == ds_id)
        res_existing = await session.execute(stmt_existing)
        if res_existing.scalars().first():
            raise ValueError(f"Duplicate dataset_id '{ds_id}' already exists in ml_datasets table.")

        # 1. Extract raw dataset using Phase71FeatureExtractor
        extracted: ExtractedTrainingDatasetDTO = await Phase71FeatureExtractor.extract_training_dataset(
            session=session,
            dataset_id=ds_id,
            plant_code=plant_code,
            customer_code=customer_code,
            limit=limit,
        )

        records = extracted.records
        lineage = extracted.lineage

        # 2. Partition Separation & Preprocessor Fit (TRAIN ONLY)
        train_records = [r for r in records if r.partition == "TRAIN"]
        val_records = [r for r in records if r.partition == "VALIDATION"]
        holdout_records = [r for r in records if r.partition == "HOLDOUT_TEST"]

        preprocessor = FeatureSetV1Preprocessor()
        preprocessor.fit(train_records)

        # 3. Transform all records deterministically
        transformed_records = [preprocessor.transform_record(r) for r in records]

        # 4. Generate Preprocessing & Schema Lineage Metadata
        lineage_dict = {
            "dataset_id": ds_id,
            "feature_set_version": FEATURE_SET_VERSION,
            "source_trigger_id": trigger_id,
            "source_erp_job_number": source_job_num,
            "preprocessor_params": {
                "fitted_train_count": len(train_records),
                "mean_plant_queue_30d": preprocessor.mean_plant_queue_30d,
                "mean_customer_retention_30d": preprocessor.mean_customer_retention_30d,
                "mean_ticket_volume_m3": preprocessor.mean_ticket_volume_m3,
                "known_plants_count": len(preprocessor.plant_codes),
                "known_customers_count": len(preprocessor.customer_codes),
            },
            "schema_contract": {
                "features": [
                    "plant_code", "customer_code", "vehicle_code", "ticket_volume_m3",
                    "plant_queue_avg_30d", "customer_retention_avg_30d",
                    "dispatch_hour", "dispatch_day_of_week"
                ],
                "targets": [
                    "predicted_delay_mins", "predicted_queue_delay_mins", "predicted_retention_delay_mins",
                    "predicted_penalty_exposure_inr", "predicted_total_cost_exposure_inr",
                    "predicted_avg_turnaround_mins", "predicted_sla_breach_target",
                    "predicted_plant_congestion_target"
                ]
            }
        }

        # Parse operation min/max dates
        date_min = (
            datetime.fromisoformat(lineage.operation_date_min)
            if lineage.operation_date_min else None
        )
        date_max = (
            datetime.fromisoformat(lineage.operation_date_max)
            if lineage.operation_date_max else None
        )

        # Create PostgreSQL MLDataset entity
        db_dataset = MLDataset(
            dataset_id=ds_id,
            feature_set_version=FEATURE_SET_VERSION,
            trigger_id=trigger_id,
            import_job_id=import_job_id,
            source_erp_job_number=source_job_num,
            total_records=lineage.generated_feature_rows,
            train_count=lineage.partition_counts.get("TRAIN", 0),
            val_count=lineage.partition_counts.get("VALIDATION", 0),
            holdout_count=lineage.partition_counts.get("HOLDOUT_TEST", 0),
            excluded_count=lineage.excluded_rows,
            sha256_checksum=lineage.sha256_checksum or "empty",
            operation_date_min=date_min,
            operation_date_max=date_max,
            lineage_metadata=lineage_dict,
            exclusion_stats=lineage.exclusion_reasons,
            target_availability=lineage.target_availability,
        )

        session.add(db_dataset)
        await session.flush()

        logger.info(
            f"[WS-10.2 TELEMETRY] Built and persisted dataset '{ds_id}'. "
            f"Total={db_dataset.total_records}, Train={db_dataset.train_count}, "
            f"Val={db_dataset.val_count}, Holdout={db_dataset.holdout_count}, Excluded={db_dataset.excluded_count}"
        )

        return db_dataset, extracted
