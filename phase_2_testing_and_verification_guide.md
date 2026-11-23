# Phase 2 Testing & Verification Guide: Snapshot Integrity, Idempotency & Supersession

This guide describes how to run and verify Phase 2 automated tests across backend, frontend, and database environments.

---

## 1. Running Phase 2 Backend Pytest Suite

Targeting isolated test database `fleet_test`:

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
TEST_DATABASE_URL=postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test PYTHONPATH=. pytest app/modules/operational_intelligence/tests/test_phase_2_snapshot_integrity.py -v
```

Expected Output:
```
app/modules/operational_intelligence/tests/test_phase_2_snapshot_integrity.py::test_phase_2_stale_flag_and_supersession_link PASSED
app/modules/operational_intelligence/tests/test_phase_2_snapshot_integrity.py::test_phase_2_authority_resolution_excludes_stale_snapshots PASSED
app/modules/operational_intelligence/tests/test_phase_2_snapshot_integrity.py::test_phase_2_idempotent_retry_safety PASSED
app/modules/operational_intelligence/tests/test_phase_2_snapshot_integrity.py::test_phase_2_lineage_metadata_integrity PASSED
============================== 4 passed in 2.12s ===============================
```

---

## 2. Running Phase 2 Frontend Vitest Suite

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/frontend
npx vitest run src/modules/predictive_intelligence/tests/phase2_snapshot_integrity.test.tsx
```

Expected Output:
```
✓ src/modules/predictive_intelligence/tests/phase2_snapshot_integrity.test.tsx (2 tests) 7ms
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
  "rejected_models": 0,
  "prediction_snapshots": 880,
  "authority_status": "AUTHORITATIVE",
  "test_fixture_snapshots": 0,
  "test_fixture_models_in_production": 0,
  "unknown_records": 0,
  "ws09_contracts_modified": false
}
```
