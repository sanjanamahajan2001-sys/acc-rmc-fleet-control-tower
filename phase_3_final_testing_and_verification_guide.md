# Phase 3 Final Testing & Verification Guide: Calculation Intelligence & Dimensional Correctness

This guide describes how to run and verify Phase 3 automated tests across backend, frontend, and database environments.

---

## 1. Running Phase 3 Backend Pytest Suite (21 Assertions)

Targeting isolated test database `fleet_test`:

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
TEST_DATABASE_URL=postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test PYTHONPATH=. pytest app/modules/operational_intelligence/tests/test_phase_3_calculation_intelligence.py -v
```

Expected Output:
```
============================== 21 passed in 7.39s ===============================
```

---

## 2. Running Full Regression Test Suites (Phases 1, 2 & 3)

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
TEST_DATABASE_URL=postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test PYTHONPATH=. pytest app/modules/operational_intelligence/tests/test_phase_1_automatic_erp_inference.py app/modules/operational_intelligence/tests/test_phase_2_snapshot_integrity.py app/modules/operational_intelligence/tests/test_phase_3_calculation_intelligence.py -v
```

Expected Output:
```
============================== 30 passed in 12.4s ===============================
```

---

## 3. Running Frontend Vitest Suites

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/frontend
npx vitest run src/modules/predictive_intelligence/tests/
```

Expected Output:
```
 Test Files  4 passed (4)
      Tests  7 passed (7)
```

---

## 4. Running Production Database Baseline Audit

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
  "prediction_snapshots": 880,
  "authority_status": "AUTHORITATIVE",
  "test_fixture_snapshots": 0,
  "test_fixture_models_in_production": 0,
  "unknown_records": 0,
  "ws09_contracts_modified": false
}
```
