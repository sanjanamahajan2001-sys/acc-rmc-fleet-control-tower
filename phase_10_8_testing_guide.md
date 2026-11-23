# WS-10.8 Testing & Verification Guide

This guide describes how to run backend integration tests, frontend production build verification, and production audit checks for WS-10.8.

---

## 1. Running E2E Lifecycle Test Suite (Isolated Test Database)

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
TEST_DATABASE_URL=postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test PYTHONPATH=. pytest app/modules/operational_intelligence/tests/test_ws_10_8_end_to_end_ml_lifecycle.py -v
```

Expected Output:
```
app/modules/operational_intelligence/tests/test_ws_10_8_end_to_end_ml_lifecycle.py::test_ws_10_8_e2e_lifecycle_not_configured_to_authoritative PASSED
app/modules/operational_intelligence/tests/test_ws_10_8_end_to_end_ml_lifecycle.py::test_ws_10_8_erp_import_cannot_bypass_controlled_promotion PASSED
app/modules/operational_intelligence/tests/test_ws_10_8_end_to_end_ml_lifecycle.py::test_ws_10_8_end_to_end_lineage_and_idempotency PASSED
app/modules/operational_intelligence/tests/test_ws_10_8_end_to_end_ml_lifecycle.py::test_ws_10_8_failure_boundary_and_artifact_mutation_protection PASSED
app/modules/operational_intelligence/tests/test_ws_10_8_end_to_end_ml_lifecycle.py::test_ws_10_8_ws09_historical_baseline_preservation PASSED
============================== 5 passed in 145.40s ===============================
```

---

## 2. Running Production Database Audit

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
python3 audit_production_state.py
```

Expected Output:
```json
{
  "promoted_models": 0,
  "rejected_models": 4,
  "prediction_snapshots": 0,
  "authority_status": "NOT_CONFIGURED",
  "test_fixture_snapshots": 0,
  "test_fixture_models_in_production": 0,
  "unknown_records": 0,
  "ws09_contracts_modified": false
}
```

---

## 3. Running Frontend Production Build

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/frontend
npm run build
```

Expected Output:
```
✓ 2470 modules transformed.
✓ built in 10.26s
```
