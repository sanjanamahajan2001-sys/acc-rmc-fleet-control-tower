# WS-10.6 Production State Remediation & Testing Guide

This guide describes how to run the controlled production state remediation script, verify test database isolation, and audit database state.

---

## 1. Running Controlled Production Database Remediation

To perform a dry-run forensic audit:

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
python3 remediate_production_database_state.py --dry-run
```

To execute controlled transactional remediation:

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
python3 remediate_production_database_state.py --execute --confirm-production-remediation
```

Expected Output:
```
==========================================================
POST-REMEDIATION BASELINE VERIFICATION
==========================================================
  PROMOTED Models Count: 0 (Expected: 0)
  Protected WS-09 REJECTED Count: 4 (Expected: 4)
  Prediction Snapshots Count: 0 (Expected: 0)
  Prediction Authority Status: NOT_CONFIGURED
==========================================================
```

---

## 2. Running Post-Remediation Machine-Readable Audit

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

## 3. Running Zero Test Pollution Regression Test

```bash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
PYTHONPATH=. pytest app/modules/operational_intelligence/tests/test_ws_10_6_pollution_regression.py -v
```

Expected Output:
```
app/modules/operational_intelligence/tests/test_ws_10_6_pollution_regression.py::test_ws_10_6_zero_test_pollution_regression PASSED
```
