"""
Exhaustive Production Test & Stress Suite for WS1.3 Excel Parser Engine
Tests OpenPyXL & CSV streaming parsers, header alias normalization, 100k+ row synthetic benchmarking,
diagnostics generation, event publishing, and peak memory tracking (< 512 MB).
"""

import pathlib

import openpyxl
import pytest

from app.events.bus import InMemoryEventBus
from app.modules.erp.parsers.dtos import HeaderAliasRegistry
from app.modules.erp.parsers.factory import get_workbook_parser
from app.modules.erp.parsers.openpyxl_parser import OpenPyXLWorkbookParser

# =============================================================================
# 1. HEADER NORMALIZATION & ALIAS TESTS
# =============================================================================


def test_header_alias_registry_normalization():
    registry = HeaderAliasRegistry()

    assert registry.normalize_header_name("  Ticket No.  ") == "ticket_no"
    assert registry.normalize_header_name("DISPATCH-DATE!!!") == "dispatch_date"
    assert registry.normalize_header_name("Customer Name (B2B)") == "customer_name_b2b"

    assert registry.resolve_canonical_name("Ticket No.") == "ticket_number"
    assert registry.resolve_canonical_name("Ticket_ID") == "ticket_number"
    assert registry.resolve_canonical_name("Truck Number") == "vehicle_code"
    assert registry.resolve_canonical_name("Dispatch Date") == "dispatch_date"


# =============================================================================
# 2. OPENPYXL STREAMING PARSER TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_openpyxl_parser_small_workbook(tmp_path: pathlib.Path):
    wb_path = tmp_path / "test_dispatches.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Dispatches"

    # Header
    ws.append(
        [
            "Ticket No.",
            "Dispatch Date",
            "Customer Name",
            "Truck Number",
            "Quantity (m3)",
        ]
    )
    # Rows
    ws.append(["TCK-1001", "2026-08-05", "Apex Construction", "V-10", 10.0])
    ws.append(["TCK-1002", "2026-08-05", "BuildCo", "V-20", 12.5])
    ws.append([None, None, None, None, None])  # Blank row
    ws.append(["TCK-1003", "2026-08-05", "Civic Infra", "V-30", 8.0])

    wb.save(str(wb_path))
    wb.close()

    event_bus = InMemoryEventBus()
    events_received: list[str] = []

    async def event_handler(event):
        events_received.append(event.event_type)

    for event_name in [
        "erp.parser.started",
        "erp.parser.sheet_discovered",
        "erp.parser.header_detected",
        "erp.parser.batch_processed",
        "erp.parser.completed",
    ]:
        event_bus.subscribe(event_name, event_handler)

    parser = get_workbook_parser(wb_path, event_bus=event_bus)
    batches = []
    async for batch in parser.parse_workbook_batches(wb_path, batch_size=2):
        batches.append(batch)

    assert len(batches) == 2  # 3 valid rows split into batches of 2
    total_parsed = sum(len(b) for b in batches)
    assert total_parsed == 3

    # Check canonical DTO row data
    row1_data = batches[0][0].data
    assert row1_data["ticket_number"] == "TCK-1001"
    assert row1_data["dispatch_date"] == "2026-08-05"
    assert row1_data["customer_name"] == "Apex Construction"
    assert row1_data["vehicle_code"] == "V-10"

    metrics = parser.get_metrics()
    assert metrics.total_rows == 4  # 3 valid + 1 blank
    assert metrics.processed_rows == 3
    assert metrics.blank_rows == 1
    assert metrics.peak_memory_mb > 0.0

    # Event verification
    assert "erp.parser.started" in events_received
    assert "erp.parser.sheet_discovered" in events_received
    assert "erp.parser.header_detected" in events_received
    assert "erp.parser.batch_processed" in events_received
    assert "erp.parser.completed" in events_received


@pytest.mark.asyncio
async def test_csv_parser_streaming(tmp_path: pathlib.Path):
    csv_path = tmp_path / "test_data.csv"
    csv_content = (
        "Ticket Number,Dispatch Date,Customer,Plant Name,Volume\n"
        "TCK-2001,2026-08-05,Acme Ltd,Vasco Plant,15.0\n"
        "TCK-2002,2026-08-05,Beta Corp,Vasco Plant,20.0\n"
    )
    csv_path.write_text(csv_content, encoding="utf-8")

    parser = get_workbook_parser(csv_path)
    batches = []
    async for batch in parser.parse_workbook_batches(csv_path, batch_size=10):
        batches.append(batch)

    assert len(batches) == 1
    assert len(batches[0]) == 2
    assert batches[0][0].data["ticket_number"] == "TCK-2001"
    assert batches[0][0].data["customer_name"] == "Acme Ltd"


# =============================================================================
# 3. 100,000 ROW STRESS BENCHMARK & MEMORY PROFILING TEST
# =============================================================================


@pytest.mark.asyncio
async def test_openpyxl_parser_100k_row_benchmark(tmp_path: pathlib.Path):
    """
    Synthetic benchmark generating and parsing 100,000 rows.
    Verifies memory remains under 512 MB RSS RAM.
    """
    wb_path = tmp_path / "stress_100k.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "BulkDispatches"

    ws.append(
        [
            "Ticket No.",
            "Dispatch Date",
            "Customer Name",
            "Truck Number",
            "Quantity (m3)",
        ]
    )
    for i in range(100_000):
        ws.append(
            [
                f"TCK-{i:06d}",
                "2026-08-05",
                f"Customer_{i % 50}",
                f"V-{i % 100}",
                10.0 + (i % 5),
            ]
        )

    wb.save(str(wb_path))
    wb.close()

    parser = OpenPyXLWorkbookParser()
    processed_count = 0

    async for batch in parser.parse_workbook_batches(wb_path, batch_size=10_000):
        processed_count += len(batch)

    assert processed_count == 100_000

    metrics = parser.get_metrics()
    assert metrics.processed_rows == 100_000
    assert metrics.peak_memory_mb < 512.0  # Must be strictly under 512 MB Peak RAM
    assert metrics.rows_per_second > 1000.0  # High-throughput streaming
