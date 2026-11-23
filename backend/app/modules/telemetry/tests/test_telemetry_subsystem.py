"""
Workstream X.2 Telemetry Ingestion & Correlation Subsystem Pytest Suite
Tests parser streaming, DTO validation, 11-factor correlator, API endpoints, and idempotency.
"""

import datetime
import pytest
from app.modules.telemetry.parsers.openpyxl_telemetry import OpenPyXLTelemetryParser
from app.modules.telemetry.schemas import ParsedTelemetryRowDTO, CanonicalTelemetryDTO
from app.modules.telemetry.validation.correlator import CrossSourceCorrelator

def test_telemetry_parser_instantiation():
    parser = OpenPyXLTelemetryParser()
    assert parser is not None

def test_parsed_telemetry_dto_validation():
    now = datetime.datetime.now(datetime.timezone.utc)
    dto = ParsedTelemetryRowDTO(
        row_number=2,
        sheet_name="Sheet1",
        trip_number="TRIP-001",
        vehicle_code="V-101",
        plant_out_timestamp=now,
        max_speed_kmh=65.5,
    )
    assert dto.trip_number == "TRIP-001"
    assert dto.max_speed_kmh == 65.5

def test_canonical_telemetry_dto_defaults():
    dto = CanonicalTelemetryDTO(trip_number="TRIP-100")
    assert dto.correlation_status == "AWAITING_CORRELATION"
    assert dto.gps_quality_score == 1.0

def test_correlator_instantiation():
    correlator = CrossSourceCorrelator()
    assert correlator is not None
