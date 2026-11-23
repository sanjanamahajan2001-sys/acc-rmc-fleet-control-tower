# Phase 1 Testing & Verification Guide: Automatic ERP Inference Orchestration

This guide describes how to run and verify Phase 1 automated tests across backend, frontend, and database environments.

---

## 1. Running Phase 1 Backend Pytest Suite

Targeting isolated test database `fleet_test`:

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
TEST_DATABASE_URL=postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test PYTHONPATH=. pytest app/modules/operational_intelligence/tests/test_phase_1_automatic_erp_inference.py -v
```

Expected Output:
```
app/modules/operational_intelligence/tests/test_phase_1_automatic_erp_inference.py::test_phase_1_erp_completion_trigger_invokes_active_inference PASSED
app/modules/operational_intelligence/tests/test_phase_1_automatic_erp_inference.py::test_phase_1_active_model_selection_and_promoted_only PASSED
app/modules/operational_intelligence/tests/test_phase_1_automatic_erp_inference.py::test_phase_1_snapshot_persistence_and_lineage PASSED
app/modules/operational_intelligence/tests/test_phase_1_automatic_erp_inference.py::test_phase_1_real_data_purity_no_mock_strings PASSED
app/modules/operational_intelligence/tests/test_phase_1_automatic_erp_inference.py::test_phase_1_duplicate_event_retry_safety PASSED
============================== 5 passed in 3.21s ===============================
```

---

## 2. Running Phase 1 Frontend Vitest Suite

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/frontend
npx vitest run src/modules/predictive_intelligence/tests/phase1_predictive_intelligence.test.tsx
```

Expected Output:
```
✓ src/modules/predictive_intelligence/tests/phase1_predictive_intelligence.test.tsx (2 tests) 6ms
 Test Files  1 passed (1)
      Tests  2 passed (2)
```

---

## 3. Running Production Database Audit

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
  "prediction_snapshots": 480,
  "authority_status": "AUTHORITATIVE",
  "test_fixture_snapshots": 0,
  "test_fixture_models_in_production": 0,
  "unknown_records": 0,
  "ws09_contracts_modified": false
}
```
