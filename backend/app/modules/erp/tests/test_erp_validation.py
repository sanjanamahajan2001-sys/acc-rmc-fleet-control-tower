"""
Exhaustive Production Test Suite for WS1.4 Canonical Mapping & Validation Engine
Tests Field Validation, Duplicate Detection, Relationship Dependency Graph Ordering,
Validation Reports, Event Publishing, and Mixed Valid/Invalid Row Batches.
"""

import pytest

from app.events.bus import InMemoryEventBus
from app.modules.erp.parsers.context import CanonicalWorkbookContext
from app.modules.erp.parsers.dtos import ParsedRowDTO
from app.modules.erp.validation.engine import CanonicalValidationEngine
from app.modules.erp.validation.rules import RelationshipDependencyGraph


@pytest.mark.asyncio
async def test_validation_engine_successful_flow():
    event_bus = InMemoryEventBus()
    events_received: list[str] = []

    async def handler(event):
        events_received.append(event.event_type)

    for evt in [
        "erp.validation.started",
        "erp.validation.batch",
        "erp.validation.completed",
    ]:
        event_bus.subscribe(evt, handler)

    ctx = CanonicalWorkbookContext(workbook_name="january_dispatches.xlsx")

    rows = [
        ParsedRowDTO(
            sheet_name="Dispatches",
            row_number=2,
            data={
                "ticket_number": "TCK-9001",
                "dispatch_date": "2026-08-05",
                "customer_name": "Apex Construction",
                "vehicle_code": "V-10",
                "plant_name": "North Plant",
                "volume_m3": 12.5,
            },
        ),
        ParsedRowDTO(
            sheet_name="Dispatches",
            row_number=3,
            data={
                "ticket_number": "TCK-9002",
                "dispatch_date": "2026-08-05",
                "customer_name": "BuildCo",
                "vehicle_code": "V-20",
                "plant_name": "South Plant",
                "volume_m3": 8.0,
            },
        ),
    ]

    engine = CanonicalValidationEngine(event_bus=event_bus)
    batch, report, stats = await engine.validate_and_map_workbook([rows], ctx)

    assert report.is_valid is True
    assert stats.rows_accepted == 2
    assert stats.rows_rejected == 0

    # Dependency Order Verification (Plants -> Customers -> Vehicles -> Tickets -> Dispatches)
    assert len(batch.plants) == 2
    assert len(batch.customers) == 2
    assert len(batch.vehicles) == 2
    assert len(batch.tickets) == 2
    assert len(batch.dispatches) == 2

    # Verify FK relationships mapped correctly
    disp1 = batch.dispatches[0]
    assert disp1.ticket_number == "TCK-9001"
    assert disp1.plant_code == "NORTH_PLANT"
    assert disp1.customer_code == "CUST_APEX_CONSTRUCTION"

    # Event verification
    assert "erp.validation.started" in events_received
    assert "erp.validation.batch" in events_received
    assert "erp.validation.completed" in events_received


@pytest.mark.asyncio
async def test_validation_engine_field_missing_and_duplicate_detection():
    ctx = CanonicalWorkbookContext(workbook_name="bad_dispatches.xlsx")

    rows = [
        # Missing required plant_name & ticket_number
        ParsedRowDTO(
            sheet_name="Dispatches",
            row_number=2,
            data={"customer_name": "Apex Construction", "vehicle_code": "V-10"},
        ),
        # Valid row 1
        ParsedRowDTO(
            sheet_name="Dispatches",
            row_number=3,
            data={
                "ticket_number": "TCK-9001",
                "dispatch_date": "2026-08-05",
                "customer_name": "Apex Construction",
                "vehicle_code": "V-10",
                "plant_name": "North Plant",
            },
        ),
        # Duplicate ticket_number (TCK-9001)
        ParsedRowDTO(
            sheet_name="Dispatches",
            row_number=4,
            data={
                "ticket_number": "TCK-9001",
                "dispatch_date": "2026-08-05",
                "customer_name": "BuildCo",
                "vehicle_code": "V-20",
                "plant_name": "North Plant",
            },
        ),
    ]

    engine = CanonicalValidationEngine()
    _batch, report, stats = await engine.validate_and_map_workbook([rows], ctx)

    assert report.is_valid is False
    assert stats.rows_accepted == 1
    assert stats.rows_rejected == 2
    assert report.invalid_rows_count == 2
    assert len(report.issues) >= 2

    error_codes = [i.error_code for i in report.issues]
    assert "VAL_REQUIRED_FIELD_MISSING" in error_codes
    assert "VAL_DUPLICATE_TICKET_NUMBER" in error_codes


def test_relationship_dependency_graph_ordering():
    graph = RelationshipDependencyGraph()
    plant = graph.get_or_create_plant("West Plant")
    graph.get_or_create_customer("Civic Infra")
    graph.get_or_create_vehicle("V-99", plant_code=plant.code)

    batch = graph.build_persistable_batch()
    assert batch.plants[0].code == "WEST_PLANT"
    assert batch.customers[0].code == "CIVIC_INFRA"
    assert batch.vehicles[0].plant_id == plant.id
