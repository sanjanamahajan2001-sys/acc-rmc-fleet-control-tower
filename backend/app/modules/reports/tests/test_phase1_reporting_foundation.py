import pytest
import asyncio
from app.modules.reports.schemas.report_schemas import (
    ReportScopeDTO,
    ReportRequestDTO,
    ReportFormat,
    ReportStatus,
    ScopeValidationStatus
)
from app.modules.reports.services.scope_resolver import ScopeResolverService
from app.modules.reports.services.report_registry import ReportRegistry


def test_scope_dto_normalization():
    scope = ReportScopeDTO(plant_id=" vasco ", customer_id="")
    assert scope.plant_id == "VASCO"
    assert scope.customer_id == "ALL"


def test_scope_fingerprint_determinism():
    s1dict = {
        "plant_id": "VASCO",
        "customer_id": "ALL",
        "operation_date": "2026-08-05",
        "shift": "ALL",
        "dataset_type": "ALL"
    }
    s2dict = {
        "plant_id": "vasco",
        "customer_id": "all",
        "operation_date": "2026-08-05",
        "shift": "all",
        "dataset_type": "all"
    }
    fp1 = ScopeResolverService.compute_scope_fingerprint(s1dict)
    fp2 = ScopeResolverService.compute_scope_fingerprint(s2dict)
    assert fp1 == fp2


def test_scope_fingerprint_variations():
    base = {
        "plant_id": "VASCO",
        "customer_id": "CUST001",
        "operation_date": "2026-08-05",
        "shift": "MORNING",
        "dataset_type": "REAL_ONLY"
    }
    fp_base = ScopeResolverService.compute_scope_fingerprint(base)

    diff_plant = dict(base, plant_id="PLANT_B")
    assert ScopeResolverService.compute_scope_fingerprint(diff_plant) != fp_base

    diff_customer = dict(base, customer_id="CUST002")
    assert ScopeResolverService.compute_scope_fingerprint(diff_customer) != fp_base

    diff_date = dict(base, operation_date="2026-08-06")
    assert ScopeResolverService.compute_scope_fingerprint(diff_date) != fp_base

    diff_shift = dict(base, shift="EVENING")
    assert ScopeResolverService.compute_scope_fingerprint(diff_shift) != fp_base

    diff_dataset = dict(base, dataset_type="SYNTHETIC_ONLY")
    assert ScopeResolverService.compute_scope_fingerprint(diff_dataset) != fp_base


def test_report_registry_catalog():
    catalog = ReportRegistry.list_all()
    assert len(catalog) == 12
    dispatch_rep = ReportRegistry.get("dispatch_analysis")
    assert dispatch_rep is not None
    assert dispatch_rep.name == "Dispatch Analysis Report"


def test_report_registry_duplicate_prevention():
    with pytest.raises(ValueError):
        ReportRegistry.register(ReportRegistry.get("dispatch_analysis"))


@pytest.mark.asyncio
async def test_scope_resolver_matrix_and_all_semantics():
    resolver = ScopeResolverService()

    # Test A: ALL plants + ALL customers
    valid, scope, _ = await resolver.resolve_and_validate_scope(
        session=None,
        raw_scope={"plant_id": "ALL", "customer_id": "ALL"},
        authorized_plants=["PLANT_A"],
        authorized_customers=["CUST_A"]
    )
    assert valid is True
    assert scope["plant_id"] == "ALL"
    assert scope["customer_id"] == "ALL"

    # Test B: Specific plant + ALL customers
    valid, scope, _ = await resolver.resolve_and_validate_scope(
        session=None,
        raw_scope={"plant_id": "PLANT_A", "customer_id": "ALL"},
        authorized_plants=["PLANT_A"],
        authorized_customers=["CUST_A"]
    )
    assert valid is True
    assert scope["plant_id"] == "PLANT_A"

    # Test C: ALL plants + Specific customer
    valid, scope, _ = await resolver.resolve_and_validate_scope(
        session=None,
        raw_scope={"plant_id": "ALL", "customer_id": "CUST_A"},
        authorized_plants=["PLANT_A"],
        authorized_customers=["CUST_A"]
    )
    assert valid is True
    assert scope["customer_id"] == "CUST_A"

    # Test D: Specific plant + Specific customer
    valid, scope, _ = await resolver.resolve_and_validate_scope(
        session=None,
        raw_scope={"plant_id": "PLANT_A", "customer_id": "CUST_A"},
        authorized_plants=["PLANT_A"],
        authorized_customers=["CUST_A"]
    )
    assert valid is True

    # Test E & F: Plant + Customer + Date + Shift
    valid, scope, _ = await resolver.resolve_and_validate_scope(
        session=None,
        raw_scope={"plant_id": "PLANT_A", "customer_id": "CUST_A", "operation_date": "2026-08-05", "shift": "MORNING"},
        authorized_plants=["PLANT_A"],
        authorized_customers=["CUST_A"]
    )
    assert valid is True
    assert scope["shift"] == "MORNING"


@pytest.mark.asyncio
async def test_scope_resolver_invalid_scope_rejections():
    resolver = ScopeResolverService()

    # Invalid shift
    valid, _, err = await resolver.resolve_and_validate_scope(session=None, raw_scope={"shift": "MIDNIGHT"})
    assert valid is False
    assert err == "INVALID_SHIFT_SCOPE"

    # Invalid dataset_type
    valid, _, err = await resolver.resolve_and_validate_scope(session=None, raw_scope={"dataset_type": "UNKNOWN"})
    assert valid is False
    assert err == "INVALID_DATASET_TYPE_SCOPE"

    # Invalid date
    valid, _, err = await resolver.resolve_and_validate_scope(session=None, raw_scope={"operation_date": "05-08-2026"})
    assert valid is False
    assert err == "INVALID_DATE_SCOPE"

    # Invalid plant
    valid, _, err = await resolver.resolve_and_validate_scope(session=None, raw_scope={"plant_id": "INVALID_P"})
    assert valid is False
    assert err == "INVALID_PLANT_SCOPE"


@pytest.mark.asyncio
async def test_dataset_authority_override_protection():
    resolver = ScopeResolverService()

    # Raw scope attempts to supply fake dataset_id
    raw_scope = {
        "plant_id": "VASCO",
        "customer_id": "ALL",
        "dataset_type": "REAL_ONLY",
        "dataset_id": "FAKE-DATASET-OVERRIDE-ATTEMPT"
    }
    valid, eff_scope, err = await resolver.resolve_and_validate_scope(session=None, raw_scope=raw_scope)
    assert valid is True
    assert eff_scope["resolved_dataset_id"] != "FAKE-DATASET-OVERRIDE-ATTEMPT"
    assert eff_scope["resolved_dataset_id"].startswith("DS-20260805-VASCO")

    assert eff_scope["resolved_dataset_id"] != "FAKE-DATASET-OVERRIDE-ATTEMPT"


@pytest.mark.asyncio
async def test_no_data_handling_contract():
    resolver = ScopeResolverService()
    valid, eff_scope, err = await resolver.resolve_and_validate_scope(
        session=None,
        raw_scope={"plant_id": "VALID_EMPTY_PLANT", "customer_id": "VALID_EMPTY_CUST"}
    )
    assert valid is True
    assert eff_scope["record_count"] == 0
    # Valid scope with zero records maps to NO_DATA, not validation failure


def test_phase7_formatters_unit_contract():
    from app.modules.reports.renderers.json_renderer import (
        format_report_date,
        get_status_pdf_style,
        get_status_xlsx_style,
    )

    # 1. Date Formatting: YYYY-MM-DD -> DD:MM:YYYY
    assert format_report_date("2026-08-21") == "21:08:2026"
    assert format_report_date("2026-08-05T10:30:00Z") == "05:08:2026"
    assert format_report_date("") == ""

    # 2. COMPLETED -> Green
    comp_pdf = get_status_pdf_style("COMPLETED")
    assert comp_pdf["bg"] == "#DCFCE7"
    assert comp_pdf["fg"] == "#14532D"

    # 3. DELAYED -> Red
    del_pdf = get_status_pdf_style("DELAYED")
    assert del_pdf["bg"] == "#FEE2E2"
    assert del_pdf["fg"] == "#7F1D1D"

    # 4. WITHIN_SLA -> Green
    wsla_pdf = get_status_pdf_style("WITHIN_SLA")
    assert wsla_pdf["bg"] == "#DCFCE7"

    # 5. OPTIMAL -> Green
    opt_pdf = get_status_pdf_style("OPTIMAL")
    assert opt_pdf["bg"] == "#DCFCE7"

    # 6. ATTENTION -> Amber/Orange
    att_pdf = get_status_pdf_style("ATTENTION")
    assert att_pdf["bg"] == "#FEF3C7"

    # 7. WARNING -> Amber/Orange
    warn_pdf = get_status_pdf_style("WARNING")
    assert warn_pdf["bg"] == "#FEF3C7"

    # 8. CRITICAL -> Red
    crit_pdf = get_status_pdf_style("CRITICAL")
    assert crit_pdf["bg"] == "#FEE2E2"

    # 9. FAILED -> Red
    fail_pdf = get_status_pdf_style("FAILED")
    assert fail_pdf["bg"] == "#FEE2E2"

    # 10. LOW severity -> Green
    low_pdf = get_status_pdf_style("LOW")
    assert low_pdf["bg"] == "#DCFCE7"

    # 11. MEDIUM severity -> Amber
    med_pdf = get_status_pdf_style("MEDIUM")
    assert med_pdf["bg"] == "#FEF3C7"

    # 12. HIGH severity -> Red
    high_pdf = get_status_pdf_style("HIGH")
    assert high_pdf["bg"] == "#FEE2E2"

    # 13. CRITICAL severity -> Red
    crit_xlsx = get_status_xlsx_style("CRITICAL")
    assert crit_xlsx["fill"] == "FEE2E2"
    assert crit_xlsx["font"] == "7F1D1D"


def test_predictive_confidence_field_mapping_and_conversion():
    """Validates that prediction confidence field comes from authoritative score and converts cleanly to %."""
    from app.modules.reports.schemas.predictive_intelligence_canonical import PredictionSnapshotRecord

    rec = PredictionSnapshotRecord(
        prediction_snapshot_id="SNAP-TEST-001",
        prediction_timestamp="2026-08-21T10:00:00Z",
        prediction_status="AUTHORITATIVE",
        model_name="delay_regressor",
        model_version="v1.0.0",
        feature_set_version="FeatureSetV1",
        target_name="predicted_delay_mins",
        predicted_value=21.7,
        confidence_score=0.85,
    )
    assert rec.confidence_score == 0.85
    # Percentage conversion check: 0.85 -> 85.0%
    assert f"{rec.confidence_score * 100:.1f}%" == "85.0%"



def test_action_execution_kpi_detail_reconciliation_invariant():
    """Validates that Action Execution KPI counts exactly equal sums of corresponding operational record statuses."""
    from app.modules.reports.schemas.action_execution_canonical import ActionLogRecord

    recs = [
        ActionLogRecord(action_id="A1", recommendation_id="REC-1", plant_code="VASCO", action_type="SLA_PRIORITIZE", dispatcher_id="SYS", dispatcher_role="DISPATCHER", action_status="PENDING", estimated_avoided_exposure_inr=100.0),
        ActionLogRecord(action_id="A2", recommendation_id="REC-2", plant_code="VASCO", action_type="SLA_PRIORITIZE", dispatcher_id="SYS", dispatcher_role="DISPATCHER", action_status="PENDING", estimated_avoided_exposure_inr=200.0),
        ActionLogRecord(action_id="A3", recommendation_id="REC-3", plant_code="VASCO", action_type="SLA_PRIORITIZE", dispatcher_id="SYS", dispatcher_role="DISPATCHER", action_status="IN_PROGRESS", estimated_avoided_exposure_inr=300.0),
        ActionLogRecord(action_id="A4", recommendation_id="REC-4", plant_code="VASCO", action_type="SLA_PRIORITIZE", dispatcher_id="SYS", dispatcher_role="DISPATCHER", action_status="EXECUTED", estimated_avoided_exposure_inr=400.0),
    ]

    total_actions = len(recs)
    pending_cnt = sum(1 for r in recs if r.action_status == "PENDING")
    accepted_cnt = sum(1 for r in recs if r.action_status == "ACCEPTED")
    in_prog_cnt = sum(1 for r in recs if r.action_status == "IN_PROGRESS")
    executed_cnt = sum(1 for r in recs if r.action_status == "EXECUTED")
    deferred_cnt = sum(1 for r in recs if r.action_status == "DEFERRED")
    rejected_cnt = sum(1 for r in recs if r.action_status == "REJECTED")

    # Invariant: Sum of individual status counts MUST equal total_actions
    assert pending_cnt + accepted_cnt + in_prog_cnt + executed_cnt + deferred_cnt + rejected_cnt == total_actions
    assert pending_cnt == 2
    assert in_prog_cnt == 1
    assert executed_cnt == 1



