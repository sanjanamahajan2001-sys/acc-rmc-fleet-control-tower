from sqlalchemy.ext.asyncio import AsyncSession
"""
WS-06.2 Backend Unit Test Suite for Dispatch Optimization Data Contracts & DTOs.
Tests DTO instantiation, enum validation, filter propagation, snapshot metadata,
scenario/objective decoupling, Gantt payloads, and error contract schemas.
"""

import pytest
from pydantic import ValidationError
from app.modules.operational_dashboard.widgets.dispatch_optimization.dtos import (
    OptimizationFilterParamsDTO,
    ObjectiveConfigDTO,
    OptimizationObjectiveEnum,
    OptimizationRunStatusEnum,
    ReadinessStatusEnum,
    OptimizationRunRequestDTO,
    OptimizationReadinessDTO,
    DataQualitySummaryDTO,
    OptimizationSnapshotMetadataDTO,
    MetricDeltaDTO,
    BeforeAfterImpactMatrixDTO,
    CandidateScenarioDTO,
    DispatchGanttItemDTO,
    OptimizationGanttResponseDTO,
    OptimizationRunResponseDTO,
    StandardAPIErrorDTO,
)


def test_filter_params_dto_defaults_and_scopes():
    # 1. Defaults
    filters = OptimizationFilterParamsDTO()
    assert filters.plant_id == "ALL"
    assert filters.customer_id == "ALL"
    assert filters.dataset_type == "REAL_ONLY"

    # 2. Specific scope
    custom_filters = OptimizationFilterParamsDTO(
    plant_id="ACC_KUNDAIM",
    customer_id="CUST_AARA_HOTELS",
    dataset_type="REAL_ONLY",
    )
    assert custom_filters.plant_id == "ACC_KUNDAIM"
    assert custom_filters.customer_id == "CUST_AARA_HOTELS"
    assert custom_filters.dataset_type == "REAL_ONLY"


def test_objective_enum_and_config():
    config = ObjectiveConfigDTO(
    objective_type=OptimizationObjectiveEnum.BALANCED_OPERATIONS,
    weights={"sla_weight": 0.50, "delay_weight": 0.35, "das_weight": 0.15},
    )
    assert config.objective_type == "BALANCED_OPERATIONS"
    assert config.weights["sla_weight"] == 0.50


def test_decoupled_scenario_id_and_objective():
    # Verify scenario_id is an opaque string/UUID and NOT bound to objective enum
    impact = BeforeAfterImpactMatrixDTO(
    sla_compliance=MetricDeltaDTO(
        metric_name="SLA Compliance", observed_baseline=54.3, optimized_value=78.5, net_delta=24.2, percentage_change=44.5, unit="%"
    ),
    dispatch_accuracy_das=MetricDeltaDTO(
        metric_name="DAS Score", observed_baseline=65.2, optimized_value=82.4, net_delta=17.2, percentage_change=26.3, unit="%"
    ),
    cumulative_delay_hours=MetricDeltaDTO(
        metric_name="Cumulative Delay", observed_baseline=1471.9, optimized_value=1059.4, net_delta=-412.5, percentage_change=-28.0, unit="hrs"
    ),
    plant_holding_delay_hours=MetricDeltaDTO(
        metric_name="Holding Delay", observed_baseline=202.1, optimized_value=78.4, net_delta=-123.7, percentage_change=-61.2, unit="hrs"
    ),
    site_retention_delay_hours=MetricDeltaDTO(
        metric_name="Retention Delay", observed_baseline=56.0, optimized_value=32.0, net_delta=-24.0, percentage_change=-42.8, unit="hrs"
    ),
    sequence_variance_delay_hours=MetricDeltaDTO(
        metric_name="Sequence Variance", observed_baseline=1213.8, optimized_value=949.0, net_delta=-264.8, percentage_change=-21.8, unit="hrs"
    ),
    )

    scenario = CandidateScenarioDTO(
    scenario_id="SCENARIO-UUID-9981-ALPHA",
    scenario_name="Balanced Fleet Trade-Off",
    objective_type=OptimizationObjectiveEnum.BALANCED_OPERATIONS,
    pareto_score=94.2,
    is_recommended=True,
    impact_matrix=impact,
    )

    assert scenario.scenario_id == "SCENARIO-UUID-9981-ALPHA"
    assert scenario.objective_type == OptimizationObjectiveEnum.BALANCED_OPERATIONS
    assert scenario.pareto_score == 94.2


def test_snapshot_metadata_dto_structure():
    snapshot = OptimizationSnapshotMetadataDTO(
    optimization_run_id="RUN-1001",
    snapshot_hash="a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
    ingestion_watermark="2025-06-20T12:00:00Z",
    dispatch_fingerprint_hash="f0e9d8c7b6a55432109876543210fedcba9876543210fedcba9876543210fedc",
    filter_scope=OptimizationFilterParamsDTO(plant_id="ACC_KUNDAIM"),
    generated_at="2025-06-20T12:05:00Z",
    )
    assert snapshot.optimization_run_id == "RUN-1001"
    assert len(snapshot.snapshot_hash) == 64


def test_gantt_item_and_response_dto():
    item = DispatchGanttItemDTO(
    dispatch_id="DISP-001",
    dispatch_number="SYNTH-TCK-TRIP-2754",
    vehicle_id="GA07F7626",
    plant_id="ACC_KUNDAIM",
    customer_id="CUST_AARA_HOTELS",
    raw_time_out="12:05",
    raw_time_in="14:30",
    baseline_time_out_iso="2025-06-20T12:05:00Z",
    baseline_time_in_iso="2025-06-20T14:30:00Z",
    recommended_time_out_iso="2025-06-20T12:17:00Z",
    recommended_time_in_iso="2025-06-20T14:42:00Z",
    time_shift_mins=12.0,
    t1_transit_mins=145.0,
    )
    gantt_resp = OptimizationGanttResponseDTO(
    optimization_run_id="RUN-1001",
    scenario_id="SCENARIO-UUID-9981-ALPHA",
    total_vehicles=1,
    total_dispatches=1,
    items=[item],
    )
    assert gantt_resp.total_vehicles == 1
    assert gantt_resp.items[0].time_shift_mins == 12.0


def test_standard_api_error_dto():
    err = StandardAPIErrorDTO(
    error_code="STALE_SNAPSHOT_CONFLICT",
    message="Operational data changed since this plan was generated.",
    status_code=409,
    )
    assert err.status_code == 409
    assert err.error_code == "STALE_SNAPSHOT_CONFLICT"
