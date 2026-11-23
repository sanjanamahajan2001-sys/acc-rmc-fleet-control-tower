# WS-10.10 Filter Correctness & Continuous Refresh Verification Guide

This guide describes how to verify continuous ML refresh, filter correctness, and production state safety for WS-10.10.

---

## 1. Running WS-10.10 Backend Pytest Suite (Isolated Test Database)

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
TEST_DATABASE_URL=postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test PYTHONPATH=. pytest app/modules/operational_intelligence/tests/test_ws_10_10_continuous_ml_refresh.py -v
```

Expected Output:
```
app/modules/operational_intelligence/tests/test_ws_10_10_continuous_ml_refresh.py::test_ws_10_10_new_erp_import_detection_and_trigger PASSED
app/modules/operational_intelligence/tests/test_ws_10_10_continuous_ml_refresh.py::test_ws_10_10_dataset_creation_and_immutability PASSED
app/modules/operational_intelligence/tests/test_ws_10_10_continuous_ml_refresh.py::test_ws_10_10_automatic_refresh_stops_at_promotion_eligibility PASSED
app/modules/operational_intelligence/tests/test_ws_10_10_continuous_ml_refresh.py::test_ws_10_10_explicit_governed_promotion_and_inference PASSED
app/modules/operational_intelligence/tests/test_ws_10_10_continuous_ml_refresh.py::test_ws_10_10_global_filters_and_authority_states PASSED
============================== 5 passed in 290.39s ===============================
```

---

## 2. Running Real Production State Audit

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
python3 audit_production_state.py
```

Expected Output:
```json
{
  "promoted_models": 4,
  "rejected_models": 4,
  "prediction_snapshots": 28,
  "authority_status": "AUTHORITATIVE",
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
✓ built in 10.66s
```
