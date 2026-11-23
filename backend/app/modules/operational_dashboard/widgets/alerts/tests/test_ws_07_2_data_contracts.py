"""
WS-07.2 Backend PyTest Comprehensive Unit & Integration Test Suite for Operational Alerts Data Contracts.
"""
import uuid
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError
from sqlalchemy import text

from app.modules.operational_dashboard.widgets.alerts.dtos import (
    OperationalAlertItemDTO,
    AlertSummaryDTO,
    OperationalDatasetContextDTO,
    AlertAcknowledgeRequestDTO,
    AlertResolveRequestDTO,
    AlertSeverityEnum,
    AlertStatusEnum,
)

# -----------------------------------------------------------------------------
# DTO VALIDATION TESTS MATRIX
# -----------------------------------------------------------------------------

def test_dto_valid_payloads():
    """Test all valid DTO payload instantiations."""
    alert_dto = OperationalAlertItemDTO(
        id=uuid.uuid4(),
        alert_fingerprint="f" * 64,
        alert_type="SITE_RETENTION_EXCESSIVE",
        severity=AlertSeverityEnum.WARNING,
        status=AlertStatusEnum.OPEN,
        plant_id="ACC_KUNDAIM",
        customer_id="CUST_AARA_HOTELS",
        dataset_id="DS-20260805-001",
        metric_name="t2c_retention_mins",
        actual_value=25.0,
        threshold_value=20.0,
        unit="mins",
        business_impact="Site retention delay",
        evidence_json={"actual": 25.0},
        recommended_action="Review site unloading",
        detected_at=datetime.now(timezone.utc),
        evaluated_at=datetime.now(timezone.utc),
    )
    assert alert_dto.severity == AlertSeverityEnum.WARNING

    dataset_context = OperationalDatasetContextDTO(
        operational_date="2025-08-15",
        total_dispatches=1174,
        last_imported_at="2026-08-13T19:13:27Z",
        dataset_id="DS-20260805-001",
        status="ACTIVE_PRODUCTION",
    )
    summary_dto = AlertSummaryDTO(
        total_active_alerts=42,
        critical_count=12,
        warning_count=28,
        info_count=2,
        acknowledged_count=5,
        dataset_context=dataset_context,
    )
    assert summary_dto.total_active_alerts == 42

    ack_req = AlertAcknowledgeRequestDTO(acknowledged_by="Operator_A", notes="Notified supervisor")
    assert ack_req.acknowledged_by == "Operator_A"

    res_req = AlertResolveRequestDTO(resolved_by="Operator_B", resolution_reason="Queue cleared")
    assert res_req.resolved_by == "Operator_B"

def test_dto_invalid_payload_fingerprint_length():
    """Test rejection of non-64 hex char fingerprints."""
    with pytest.raises(ValidationError):
        OperationalAlertItemDTO(
            id=uuid.uuid4(),
            alert_fingerprint="short_hash",
            alert_type="INVALID",
            severity=AlertSeverityEnum.CRITICAL,
            status=AlertStatusEnum.OPEN,
            plant_id="ACC_VASCO",
            customer_id="CUST_TEST",
            dataset_id="DS-001",
            metric_name="test",
            actual_value=1.0,
            threshold_value=1.0,
            unit="mins",
            business_impact="test",
            recommended_action="test",
            detected_at=datetime.now(timezone.utc),
            evaluated_at=datetime.now(timezone.utc),
        )

def test_dto_invalid_payload_severity_enum():
    """Test rejection of invalid severity enum value."""
    with pytest.raises(ValidationError):
        OperationalAlertItemDTO(
            id=uuid.uuid4(),
            alert_fingerprint="a" * 64,
            alert_type="TEST",
            severity="INVALID_SEVERITY", # Invalid
            status=AlertStatusEnum.OPEN,
            plant_id="ACC_VASCO",
            customer_id="CUST_TEST",
            dataset_id="DS-001",
            metric_name="test",
            actual_value=1.0,
            threshold_value=1.0,
            unit="mins",
            business_impact="test",
            recommended_action="test",
            detected_at=datetime.now(timezone.utc),
            evaluated_at=datetime.now(timezone.utc),
        )

def test_dto_invalid_payload_status_enum():
    """Test rejection of invalid status enum value."""
    with pytest.raises(ValidationError):
        OperationalAlertItemDTO(
            id=uuid.uuid4(),
            alert_fingerprint="b" * 64,
            alert_type="TEST",
            severity=AlertSeverityEnum.INFO,
            status="INVALID_STATUS", # Invalid
            plant_id="ACC_VASCO",
            customer_id="CUST_TEST",
            dataset_id="DS-001",
            metric_name="test",
            actual_value=1.0,
            threshold_value=1.0,
            unit="mins",
            business_impact="test",
            recommended_action="test",
            detected_at=datetime.now(timezone.utc),
            evaluated_at=datetime.now(timezone.utc),
        )

def test_dto_invalid_payload_acknowledge_request():
    """Test rejection of empty/oversized acknowledge request payloads."""
    # Empty author
    with pytest.raises(ValidationError):
        AlertAcknowledgeRequestDTO(acknowledged_by="")
    
    # Oversized notes (>500 chars)
    with pytest.raises(ValidationError):
        AlertAcknowledgeRequestDTO(acknowledged_by="Operator_A", notes="x" * 501)

def test_dto_invalid_payload_resolve_request():
    """Test rejection of empty resolve request payloads."""
    # Empty resolver
    with pytest.raises(ValidationError):
        AlertResolveRequestDTO(resolved_by="", resolution_reason="Queue cleared")

    # Empty resolution reason
    with pytest.raises(ValidationError):
        AlertResolveRequestDTO(resolved_by="Operator_B", resolution_reason="")
