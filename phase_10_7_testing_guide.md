# WS-10.7 Testing & Verification Guide

This guide describes how to run backend integration tests, frontend Vitest UI tests, and production build verification for WS-10.7.

---

## 1. Running Backend Integration Test Suite

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
ALLOW_PRODUCTION_TESTING=true PYTHONPATH=. pytest app/modules/operational_intelligence/tests/test_ws_10_7_predictive_intelligence_api.py -v
```

Expected Output:
```
app/modules/operational_intelligence/tests/test_ws_10_7_predictive_intelligence_api.py::test_ws_10_7_api_not_configured_state PASSED
app/modules/operational_intelligence/tests/test_ws_10_7_predictive_intelligence_api.py::test_ws_10_7_api_no_data_state PASSED
app/modules/operational_intelligence/tests/test_ws_10_7_predictive_intelligence_api.py::test_ws_10_7_api_authoritative_state_and_four_families PASSED
app/modules/operational_intelligence/tests/test_ws_10_7_predictive_intelligence_api.py::test_ws_10_7_api_canonical_date_semantics PASSED
============================== 4 passed in 0.98s ===============================
```

---

## 2. Running Frontend Vitest Certification Suite

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/frontend
npm run test -- test_ws_10_7_predictive_intelligence_ui.test.tsx
```

Expected Output:
```
 ✓ src/modules/operational_intelligence/tests/test_ws_10_7_predictive_intelligence_ui.test.tsx (5 tests)
 Test Files  1 passed (1)
      Tests  5 passed (5)
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
✓ built in 10.71s
```

---

## 4. Running Machine-Readable Audit Verification

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
