# WS-10.7: Operational Predictive Intelligence UI & Live Authoritative Prediction Data Integration

## Executive Summary & Final Certification Decision
WS-10.7 has successfully connected the Predictive Intelligence frontend to the authoritative WS-10.6 inference/snapshot backend. All four authority states (`NOT_CONFIGURED`, `NO_DATA`, `AUTHORITATIVE`, `ERROR`) are cleanly rendered across the four approved model families without fake numbers, mock prediction arrays, or frontend fallback formulas.

**Final Certification Decision**: **WS-10.7 = CERTIFIED / FROZEN**

> **Current Production Machine-Readable Audit Baseline**:
> ```json
> {
>   "promoted_models": 0,
>   "rejected_models": 4,
>   "prediction_snapshots": 0,
>   "authority_status": "NOT_CONFIGURED",
>   "test_fixture_snapshots": 0,
>   "test_fixture_models_in_production": 0,
>   "unknown_records": 0,
>   "ws09_contracts_modified": false
> }
> ```

---

## 1. Architecture & Single-Point-of-Truth Model Authority

```
                 WS-10.6 Authoritative Prediction APIs
                                  │
                                  ▼
                        Frontend API / DTO Layer
                                  │
                                  ▼
                 Predictive Intelligence Data Service
                                  │
                                  ▼
                        Global Filter Context
                                  │
                                  ▼
                 Predictive Intelligence Workspace
                                  │
                                  ▼
            Operational Decision Intelligence / Prioritization UI
```

The backend remains the sole authority for:
- Promoted model resolution
- Prediction validity
- Snapshot lineage
- Model version
- Artifact identity
- Prediction timestamps
- Authority state (`NOT_CONFIGURED` / `NO_DATA` / `AUTHORITATIVE` / `ERROR`)

---

## 2. Four Required Frontend Authority States

1. **`NOT_CONFIGURED`**:
   - **Condition**: `PROMOTED = 0`.
   - **Display**: Displays prominent warning banner explaining no model has been legitimately promoted. Disables operational risk prioritization and shows `Prediction Authority NOT CONFIGURED`. Zero fake predictions displayed.
2. **`NO_DATA`**:
   - **Condition**: Promoted model exists (`PROMOTED > 0`), but zero snapshot matches exist for the selected global filters.
   - **Display**: Renders `"No prediction snapshots match the selected operational filters (NO_DATA)"`.
3. **`AUTHORITATIVE`**:
   - **Condition**: Active `PROMOTED` model exists AND authoritative prediction snapshots match the selected global filters.
   - **Display**: Renders real PostgreSQL-backed prediction values, model versions, confidence scores, and line-item details.
4. **`ERROR`**:
   - **Condition**: Backend API query failure or network error.
   - **Display**: Safely displays an operational error state banner. Never silently converts `ERROR` into `NO_DATA` or `NOT_CONFIGURED`.

---

## 3. Four Approved Model Family Integration

1. `delay_regressor`: Predicted delay (minutes), active model version, prediction timestamp.
2. `turnaround_regressor`: Predicted average turnaround (minutes), active model version, prediction timestamp.
3. `sla_breach_classifier`: SLA breach risk probability (%), active model version, prediction timestamp.
4. `plant_risk_classifier`: Plant congestion risk prediction (%), active model version, prediction timestamp.

---

## 4. Global Filter Integration & Canonical Date Semantics

- Respects global operational filters: `operation_date`, `plant_id`, `customer_id`, `dataset_type`, `dataset_id`.
- **Canonical Date Distinction**:
  - `operation_date`: Canonical business date (e.g. `2026-08-05`).
  - `prediction_timestamp`: Actual inference execution timestamp (e.g. `2026-08-18T10:15:30Z`).

---

## 5. Prediction Snapshot Lineage & Interactive Drill-Down Modal

Every displayed prediction preserves complete backend lineage:
- `prediction_snapshot_id`
- `model_name` & `model_version`
- `artifact_sha256`
- `feature_set_version` (`FeatureSetV1`)
- `operation_date` & `prediction_timestamp`
- `dispatch_code`, `plant_code`, `customer_code`, `vehicle_code`
- Raw `input_features` & `prediction_outputs`

---

## 6. Verification & Certification Evidence

| Certification Gate | Result | Status |
| :--- | :--- | :--- |
| Backend API Integration Test Suite | 4/4 PASS | ✅ VERIFIED |
| Frontend Vitest Certification Suite | 5/5 PASS | ✅ VERIFIED |
| Production Build (`npm run build`) | Built in 10.71s | ✅ VERIFIED |
| Zero Test Pollution Regression | PASS | ✅ VERIFIED |
| Machine-Readable Audit State | `PROMOTED = 0`, `snapshots = 0`, `authority_status = NOT_CONFIGURED` | ✅ VERIFIED |
| Frozen WS-09 Authority Contracts | Unmodified (`ws09_contracts_modified = false`) | ✅ VERIFIED |
