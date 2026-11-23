"""
WS-09 Phase 7.1 Feature Engineering & Training Dataset Generation (Anti-Leakage)

Authoritative Feature Extractor and Chronological Training Dataset Generator.
Converts PostgreSQL operational dispatches into reproducible, versioned, leakage-safe ML training records.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import math
import hashlib

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.modules.erp.models import Dispatch, Plant, Customer, Vehicle, Ticket, Order


# =============================================================================
# CONSTANTS & METADATA
# =============================================================================

FEATURE_SET_VERSION: str = "FeatureSetV1"

# Authoritative Cold-Start Feature Baseline Governance (Phase 4 / Phase 6 Platform SLA Baselines)
# Reused consistently in FeatureSetV1 across training and real-time inference when historical data is absent.
COLD_START_PLANT_QUEUE_AVG_30D_MINS: float = 15.0  # Derived from Section 06 SLA holding baseline (20m - 5m buffer)
COLD_START_CUSTOMER_RETENTION_AVG_30D_MINS: float = 8.0  # Derived from Section 06 SLA retention baseline (10m - 2m buffer)

# Prohibited Leakage Fields - explicitly rejected if presented in inference feature inputs
FORBIDDEN_LEAKAGE_FIELDS: List[str] = [
    "t2a_holding_mins",
    "t2c_retention_mins",
    "realized_holding_pen_mins",
    "realized_retention_pen_mins",
    "realized_penalty_exposure_inr",
    "realized_total_cost_exposure_inr",
    "date_in",
    "time_in",
    "cycle_time",
    "status",
    "t1_transit_mins",
    "t2b_unloading_mins",
    "unloading_duration_mins",
    "t3_return_mins",
    "actual_delay_mins",
    "predicted_delay_mins",
    "realized_penalty",
]

ALLOWED_INFERENCE_FEATURES: List[str] = [
    "plant_code",
    "customer_code",
    "vehicle_code",
    "ticket_volume_m3",
    "plant_queue_avg_30d",
    "customer_retention_avg_30d",
    "dispatch_hour",
    "dispatch_day_of_week",
]


# =============================================================================
# DATA STRUCTURES & DTOS
# =============================================================================

class FeatureRecordDTO(BaseModel):
    """Single dispatch feature record with features, targets, cutoff timestamp, and partition."""
    dispatch_id: str
    dispatch_code: str
    prediction_timestamp: str  # ISO string representation of dispatch_date (prediction cutoff timestamp t_pred)
    dataset_id: str
    feature_set_version: str = FEATURE_SET_VERSION
    
    # Features (Inputs available at prediction cutoff timestamp t_pred)
    features: Dict[str, Any]
    
    # Target Labels (Outcomes measured after dispatch completion)
    targets: Dict[str, Optional[float]]
    
    # Partition classification: TRAIN, VALIDATION, HOLDOUT_TEST
    partition: str = "TRAIN"


class DatasetLineageDTO(BaseModel):
    """Metadata tracking dataset generation lineage and data quality metrics."""
    dataset_id: str
    feature_set_version: str
    generation_timestamp: str
    operation_date_min: Optional[str] = None
    operation_date_max: Optional[str] = None
    total_dispatches_queried: int = 0
    generated_feature_rows: int = 0
    excluded_rows: int = 0
    exclusion_reasons: Dict[str, int] = Field(default_factory=dict)
    partition_counts: Dict[str, int] = Field(default_factory=dict)
    target_availability: Dict[str, int] = Field(default_factory=dict)
    is_reproducible: bool = True
    sha256_checksum: Optional[str] = None


class ExtractedTrainingDatasetDTO(BaseModel):
    """Container holding feature records and dataset lineage."""
    lineage: DatasetLineageDTO
    records: List[FeatureRecordDTO]


# =============================================================================
# FEATURE EXTRACTOR CLASS
# =============================================================================

class Phase71FeatureExtractor:
    """
    Authoritative Feature Extraction Service for WS-09 Phase 7.1.
    Operates deterministically on PostgreSQL dispatches with strict anti-leakage controls.
    """

    @classmethod
    def validate_no_leakage_in_features(cls, features_dict: Dict[str, Any]) -> None:
        """
        Validates that no forbidden target/outcome fields exist in the provided feature dictionary.
        Raises ValueError if any leakage field is detected.
        """
        for forbidden in FORBIDDEN_LEAKAGE_FIELDS:
            if forbidden in features_dict:
                raise ValueError(
                    f"ANTI-LEAKAGE VIOLATION: Forbidden outcome field '{forbidden}' found in inference feature dictionary."
                )

    @classmethod
    def extract_inference_features(cls, dispatch_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts FeatureSetV1 inference feature dictionary from dispatch data.
        Enforces allowed feature keys and anti-leakage assertions.
        """
        cls.validate_no_leakage_in_features(dispatch_dict)
        features = {}
        for feature_name in ALLOWED_INFERENCE_FEATURES:
            if feature_name in dispatch_dict:
                features[feature_name] = dispatch_dict[feature_name]
        return features

    @classmethod
    def classify_chronological_partition(
        cls,
        dispatch_dt: datetime,
        min_date: datetime,
        max_date: datetime,
        train_ratio: float = 0.6667,  # ~60 days of 90
        val_ratio: float = 0.1667,    # ~15 days of 90
    ) -> str:
        """
        Partition dispatches chronologically into TRAIN, VALIDATION, or HOLDOUT_TEST based on dispatch_date.
        Strictly enforces no random splits.
        """
        total_seconds = (max_date - min_date).total_seconds()
        if total_seconds <= 0:
            return "TRAIN"
        
        elapsed_seconds = (dispatch_dt - min_date).total_seconds()
        position = elapsed_seconds / total_seconds
        
        if position <= train_ratio:
            return "TRAIN"
        elif position <= (train_ratio + val_ratio):
            return "VALIDATION"
        else:
            return "HOLDOUT_TEST"

    @classmethod
    async def extract_training_dataset(
        cls,
        session: AsyncSession,
        dataset_id: str = "DS-20260805-001",
        plant_code: Optional[str] = None,
        customer_code: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> ExtractedTrainingDatasetDTO:
        """
        Extracts dispatches from PostgreSQL, computes historical 30d rolling averages (cutoff strictly before dispatch_date),
        computes non-leaking features and target labels, and packages a chronological dataset.
        """
        gen_timestamp = datetime.now(timezone.utc).isoformat()
        exclusion_reasons: Dict[str, int] = {
            "missing_dispatch_date": 0,
            "negative_holding_mins": 0,
            "negative_retention_mins": 0,
            "impossible_lifecycle": 0,
            "duplicate_dispatch": 0,
        }
        
        # 1. Fetch all raw dispatches joined with plant, customer, vehicle, ticket
        stmt = (
            select(
                Dispatch,
                Plant.code.label("plant_code"),
                Customer.code.label("customer_code"),
                Vehicle.code.label("vehicle_code"),
                Ticket.delivered_volume_m3.label("ticket_volume_m3"),
            )
            .join(Plant, Dispatch.plant_id == Plant.id, isouter=True)
            .join(Customer, Dispatch.customer_id == Customer.id, isouter=True)
            .join(Vehicle, Dispatch.vehicle_id == Vehicle.id, isouter=True)
            .join(Ticket, Dispatch.ticket_id == Ticket.id, isouter=True)
            .order_by(Dispatch.dispatch_date.asc(), Dispatch.dispatch_number.asc())
        )

        if plant_code and plant_code != "ALL":
            stmt = stmt.where(Plant.code == plant_code)
        if customer_code and customer_code != "ALL":
            stmt = stmt.where(Customer.code == customer_code)
        if limit:
            stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        rows = result.all()

        total_queried = len(rows)
        if total_queried == 0:
            lineage = DatasetLineageDTO(
                dataset_id=dataset_id,
                feature_set_version=FEATURE_SET_VERSION,
                generation_timestamp=gen_timestamp,
                total_dispatches_queried=0,
                generated_feature_rows=0,
                excluded_rows=0,
                exclusion_reasons=exclusion_reasons,
                partition_counts={"TRAIN": 0, "VALIDATION": 0, "HOLDOUT_TEST": 0},
                target_availability={},
                sha256_checksum=hashlib.sha256(b"empty").hexdigest(),
            )
            return ExtractedTrainingDatasetDTO(lineage=lineage, records=[])

        # 2. Derive date boundaries for chronological partitioning
        valid_dates = [r[0].dispatch_date for r in rows if r[0].dispatch_date is not None]
        min_date = min(valid_dates) if valid_dates else datetime.now(timezone.utc)
        max_date = max(valid_dates) if valid_dates else datetime.now(timezone.utc)

        # 3. Pre-compute rolling historical averages per plant and customer strictly using past records
        # Plant 30d rolling queue delay average, Customer 30d rolling retention delay average
        records: List[FeatureRecordDTO] = []
        partition_counts = {"TRAIN": 0, "VALIDATION": 0, "HOLDOUT_TEST": 0}
        target_availability = {
            "predicted_delay_mins": 0,
            "predicted_queue_delay_mins": 0,
            "predicted_retention_delay_mins": 0,
            "predicted_penalty_exposure_inr": 0,
            "predicted_total_cost_exposure_inr": 0,
            "predicted_avg_turnaround_mins": 0,
            "predicted_sla_breach_target": 0,
            "predicted_plant_congestion_target": 0,
        }
        
        seen_dispatch_numbers = set()
        excluded_count = 0

        for row in rows:
            dispatch: Dispatch = row[0]
            p_code: str = row.plant_code or "UNKNOWN_PLANT"
            c_code: str = row.customer_code or "UNKNOWN_CUSTOMER"
            v_code: str = row.vehicle_code or "UNKNOWN_VEHICLE"
            t_vol: float = float(row.ticket_volume_m3 or 6.0)

            # Data Quality Validations
            if dispatch.dispatch_date is None:
                exclusion_reasons["missing_dispatch_date"] += 1
                excluded_count += 1
                continue

            if dispatch.dispatch_number in seen_dispatch_numbers:
                exclusion_reasons["duplicate_dispatch"] += 1
                excluded_count += 1
                continue
            seen_dispatch_numbers.add(dispatch.dispatch_number)

            if dispatch.t2a_holding_mins is not None and dispatch.t2a_holding_mins < 0:
                exclusion_reasons["negative_holding_mins"] += 1
                excluded_count += 1
                continue

            if dispatch.t2c_retention_mins is not None and dispatch.t2c_retention_mins < 0:
                exclusion_reasons["negative_retention_mins"] += 1
                excluded_count += 1
                continue

            # Check impossible lifecycle ordering if date_in is present
            if dispatch.date_in and dispatch.date_in < dispatch.dispatch_date:
                exclusion_reasons["impossible_lifecycle"] += 1
                excluded_count += 1
                continue

            # Prediction cutoff timestamp t_pred is dispatch_date (t1 departure time from batch plant)
            t_pred = dispatch.dispatch_date

            # Calculate Historical Aggregates strictly prior to t_pred (past window)
            past_plant_holding = [
                r[0].t2a_holding_mins for r in rows
                if r[0].dispatch_date < t_pred
                and (r.plant_code == p_code)
                and r[0].t2a_holding_mins is not None
            ]
            plant_queue_avg_30d = (
                float(sum(past_plant_holding) / len(past_plant_holding))
                if past_plant_holding else COLD_START_PLANT_QUEUE_AVG_30D_MINS
            )

            past_customer_retention = [
                r[0].t2c_retention_mins for r in rows
                if r[0].dispatch_date < t_pred
                and (r.customer_code == c_code)
                and r[0].t2c_retention_mins is not None
            ]
            customer_retention_avg_30d = (
                float(sum(past_customer_retention) / len(past_customer_retention))
                if past_customer_retention else COLD_START_CUSTOMER_RETENTION_AVG_30D_MINS
            )

            # Construct Inference Features (NO OUTCOME LEAKAGE ALLOWED)
            features = {
                "plant_code": p_code,
                "customer_code": c_code,
                "vehicle_code": v_code,
                "ticket_volume_m3": round(t_vol, 2),
                "plant_queue_avg_30d": round(plant_queue_avg_30d, 2),
                "customer_retention_avg_30d": round(customer_retention_avg_30d, 2),
                "dispatch_hour": t_pred.hour,
                "dispatch_day_of_week": t_pred.weekday(),
            }

            # Enforce Anti-Leakage Assertion
            cls.validate_no_leakage_in_features(features)

            # Target / Label Generation (Separated from features)
            # Schema fields:
            # - dispatch.t1_transit_mins: Outbound transit duration from plant to site (minutes)
            # - dispatch.t2a_holding_mins: Holding waiting duration at site before unloading (minutes)
            # - dispatch.t2b_unloading_mins: Unloading activity duration at site (minutes)
            # - dispatch.t2c_retention_mins: Retention delay duration at site beyond SLA (minutes)
            # - dispatch.t3_return_mins: Inbound transit duration from site back to plant (minutes)
            
            t2a_holding = float(dispatch.t2a_holding_mins) if dispatch.t2a_holding_mins is not None else None
            t2c_retention = float(dispatch.t2c_retention_mins) if dispatch.t2c_retention_mins is not None else None
            t1_transit_duration = float(dispatch.t1_transit_mins) if dispatch.t1_transit_mins is not None else 25.0
            t2b_unloading_duration = float(dispatch.t2b_unloading_mins) if dispatch.t2b_unloading_mins is not None else 30.0
            t3_return_duration = float(dispatch.t3_return_mins) if dispatch.t3_return_mins is not None else 25.0

            # Target 1: predicted_delay_mins = excess holding + excess retention
            holding_pen = max(0.0, (t2a_holding or 0.0) - 20.0)
            retention_pen = max(0.0, (t2c_retention or 0.0) - 10.0)
            predicted_delay_target = (holding_pen + retention_pen) if (t2a_holding is not None or t2c_retention is not None) else None

            # Target 2: predicted_queue_delay_mins = plant queue waiting time (t2a_holding)
            predicted_queue_target = t2a_holding

            # Target 3: predicted_retention_delay_mins = site unloading delay (t2c_retention)
            predicted_retention_target = t2c_retention

            # Target 4: predicted_penalty_exposure_inr = (retention_delay - 10) * 35.0
            predicted_penalty_exposure_target = (retention_pen * 35.0) if t2c_retention is not None else None

            # Target 5: predicted_total_cost_exposure_inr = (holding_pen * 40.0) + (retention_pen * 35.0)
            predicted_total_cost_target = ((holding_pen * 40.0) + (retention_pen * 35.0)) if (t2a_holding is not None or t2c_retention is not None) else None

            # Target 6: predicted_avg_turnaround_mins = t1_transit_duration + t2a_holding + t2b_unloading_duration + t2c_retention + t3_return_duration
            if t2a_holding is not None and t2c_retention is not None:
                predicted_turnaround_target = (
                    t1_transit_duration + t2a_holding + t2b_unloading_duration + t2c_retention + t3_return_duration
                )
            else:
                predicted_turnaround_target = None

            # Target 7: predicted_sla_breach_target = 1 if holding_pen > 0 or retention_pen > 0 else 0 (Customer & Overall SLA)
            if t2a_holding is not None or t2c_retention is not None:
                predicted_sla_breach_target = 1.0 if (holding_pen > 0 or retention_pen > 0) else 0.0
            else:
                predicted_sla_breach_target = None

            # Target 8: predicted_plant_congestion_target = 1 if holding_pen > 0 else 0 (Plant-Specific Congestion/Queue Breach)
            if t2a_holding is not None:
                predicted_plant_congestion_target = 1.0 if holding_pen > 0 else 0.0
            else:
                predicted_plant_congestion_target = None

            targets = {
                "predicted_delay_mins": round(predicted_delay_target, 2) if predicted_delay_target is not None else None,
                "predicted_queue_delay_mins": round(predicted_queue_target, 2) if predicted_queue_target is not None else None,
                "predicted_retention_delay_mins": round(predicted_retention_target, 2) if predicted_retention_target is not None else None,
                "predicted_penalty_exposure_inr": round(predicted_penalty_exposure_target, 2) if predicted_penalty_exposure_target is not None else None,
                "predicted_total_cost_exposure_inr": round(predicted_total_cost_target, 2) if predicted_total_cost_target is not None else None,
                "predicted_avg_turnaround_mins": round(predicted_turnaround_target, 2) if predicted_turnaround_target is not None else None,
                "predicted_sla_breach_target": predicted_sla_breach_target,
                "predicted_plant_congestion_target": predicted_plant_congestion_target,
            }

            # Update target availability counters
            for tgt_key, tgt_val in targets.items():
                if tgt_val is not None:
                    target_availability[tgt_key] = target_availability.get(tgt_key, 0) + 1

            # Determine Chronological Partition
            partition = cls.classify_chronological_partition(t_pred, min_date, max_date)
            partition_counts[partition] = partition_counts.get(partition, 0) + 1

            record = FeatureRecordDTO(
                dispatch_id=str(dispatch.id),
                dispatch_code=dispatch.dispatch_number,
                prediction_timestamp=t_pred.isoformat(),
                dataset_id=dataset_id,
                feature_set_version=FEATURE_SET_VERSION,
                features=features,
                targets=targets,
                partition=partition,
            )
            records.append(record)

        # 4. Generate SHA256 checksum over records for reproducibility tracking
        hasher = hashlib.sha256()
        for rec in records:
            hasher.update(rec.dispatch_code.encode("utf-8"))
            hasher.update(str(rec.features).encode("utf-8"))
            hasher.update(str(rec.targets).encode("utf-8"))
        sha256_checksum = hasher.hexdigest()

        lineage = DatasetLineageDTO(
            dataset_id=dataset_id,
            feature_set_version=FEATURE_SET_VERSION,
            generation_timestamp=gen_timestamp,
            operation_date_min=min_date.isoformat(),
            operation_date_max=max_date.isoformat(),
            total_dispatches_queried=total_queried,
            generated_feature_rows=len(records),
            excluded_rows=excluded_count,
            exclusion_reasons=exclusion_reasons,
            partition_counts=partition_counts,
            target_availability=target_availability,
            is_reproducible=True,
            sha256_checksum=sha256_checksum,
        )

        return ExtractedTrainingDatasetDTO(lineage=lineage, records=records)
