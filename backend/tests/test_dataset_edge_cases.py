import pytest
from app.modules.erp.api.jobs import classify_dataset_file


def test_matching_prefixes():
    period1, label1, role1 = classify_dataset_file("05. T1 Mar-Apr 26.xlsx", {"dispatches_inserted": 6834, "dispatches_updated": 0})
    period2, label2, role2 = classify_dataset_file("05. Trip drum March & April 26.xlsx", {"dispatches_inserted": 0, "dispatches_updated": 6834})

    assert period1 == period2 == "2026-MAR-APR"
    assert role1 == "ERP Dispatches"
    assert role2 == "Trip drum Telemetry" or role2 == "Trip Drum Telemetry"


def test_missing_or_different_prefixes():
    # Edge case 1: No numeric prefix on drum file
    p1, _, r1 = classify_dataset_file("05. T1 Mar-Apr 26.xlsx")
    p2, _, r2 = classify_dataset_file("Trip drum March & April 26.xlsx")
    assert p1 == p2 == "2026-MAR-APR"
    assert r1 == "ERP Dispatches"
    assert r2 == "Trip Drum Telemetry"

    # Edge case 2: Totally different numeric prefixes
    p3, _, _ = classify_dataset_file("02. T1 Jan-Feb 26.xlsx")
    p4, _, _ = classify_dataset_file("99. Trip drum January & February 26.xlsx")
    assert p3 == p4 == "2026-JAN-FEB"

    # Edge case 3: 2025 multi-month notation
    p5, _, _ = classify_dataset_file("01. T1 Jul-Aug 25.xlsx")
    p6, _, _ = classify_dataset_file("Trip drum July & August 25.xlsx")
    assert p5 == p6 == "2025-JUL-AUG"


def test_lineage_overrides_filename():
    # Database lineage shows updates only -> Drum Telemetry even if name doesn't contain 'drum'
    _, _, role_upd = classify_dataset_file("file_without_drum_in_name.xlsx", {"dispatches_inserted": 0, "dispatches_updated": 500})
    assert role_upd == "Trip Drum Telemetry"

    # Database lineage shows inserts only -> ERP Dispatches
    _, _, role_ins = classify_dataset_file("file_with_drum_word_in_title.xlsx", {"dispatches_inserted": 500, "dispatches_updated": 0})
    assert role_ins == "ERP Dispatches"
