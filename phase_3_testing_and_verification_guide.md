# Phase 3 Testing & Verification Guide: Calculation Intelligence & Rate Authority Hardening

This guide describes how to run and verify Phase 3 automated tests across backend, frontend, and database environments.

---

## 1. Running Phase 3 Backend Pytest Suite

Targeting isolated test database `fleet_test`:

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
TEST_DATABASE_URL=postgresql+asyncpg://postgres:sanjana@localhost:5432/fleet_test PYTHONPATH=. pytest app/modules/operational_intelligence/tests/test_phase_3_calculation_intelligence.py -v
```

Expected Output:
```
app/modules/operational_intelligence/tests/test_phase_3_calculation_intelligence.py::test_phase_3_1_global_rate_resolution PASSED
app/modules/operational_intelligence/tests/test_phase_3_calculation_intelligence.py::test_phase_3_2_plant_override_precedence PASSED
app/modules/operational_intelligence/tests/test_phase_3_calculation_intelligence.py::test_phase_3_3_customer_contract_override_precedence PASSED
app/modules/operational_intelligence/tests/test_phase_3_calculation_intelligence.py::test_phase_3_4_missing_rate_not_configured PASSED
app/modules/operational_intelligence/tests/test_phase_3_calculation_intelligence.py::test_phase_3_5_decimal_formulas_and_precision PASSED
app/modules/operational_intelligence/tests/test_phase_3_calculation_intelligence.py::test_phase_3_6_predictive_service_financial_integration PASSED
============================== 6 passed in 2.55s ===============================
```

---

## 2. Running Phase 3 Frontend Vitest Suite

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/frontend
npx vitest run src/modules/predictive_intelligence/tests/phase3_calculation_intelligence.test.tsx
```

Expected Output:
```
✓ src/modules/predictive_intelligence/tests/phase3_calculation_intelligence.test.tsx (2 tests) 9ms
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
  "prediction_snapshots": 880,
  "authority_status": "AUTHORITATIVE",
  "test_fixture_snapshots": 0,
  "test_fixture_models_in_production": 0,
  "unknown_records": 0,
  "ws09_contracts_modified": false
}
```
