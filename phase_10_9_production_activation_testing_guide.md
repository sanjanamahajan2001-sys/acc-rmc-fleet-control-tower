# WS-10.9 Production Activation & Verification Guide

This guide describes how to run backend integration tests, production database audit checks, and UI lineage tracing for WS-10.9.

---

## 1. Running WS-10.9 Pytest Suite (Isolated Test Database)

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
TEST_DATABASE_URL=postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test PYTHONPATH=. pytest app/modules/operational_intelligence/tests/test_ws_10_9_production_activation.py -v
```

Expected Output:
```
app/modules/operational_intelligence/tests/test_ws_10_9_production_activation.py::test_ws_10_9_trigger_and_dataset_builder_integrity PASSED
app/modules/operational_intelligence/tests/test_ws_10_9_production_activation.py::test_ws_10_9_training_and_holdout_evaluation PASSED
app/modules/operational_intelligence/tests/test_ws_10_9_production_activation.py::test_ws_10_9_promotion_and_authoritative_inference PASSED
app/modules/operational_intelligence/tests/test_ws_10_9_production_activation.py::test_ws_10_9_api_dto_and_global_filters PASSED
app/modules/operational_intelligence/tests/test_ws_10_9_production_activation.py::test_ws_10_9_ws09_baseline_and_zero_pollution PASSED
============================== 5 passed in 36.12s ===============================
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
✓ built in 11.19s
```
