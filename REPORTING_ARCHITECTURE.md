# Fleet Control Tower — Reporting Subsystem Architecture (Phase 1)

## 1. Overview

The Reporting & Export subsystem provides a unified backend foundation for querying, scoping, fingerprinting, and tracking report generation across the Fleet Operational Intelligence Platform.

Phase 1 establishes the baseline architecture, authorization rules, deterministic fingerprints, and execution audit database model without rendering PDF/XLSX/JSON artifacts (which are handled in Phase 2).

## 2. Frozen Architectural Flow

\\\	ext
Existing Fleet Control Tower Global Filters
                ↓
          Report Request DTO
                ↓
       Scope Normalization & DTO Validation
                ↓
        Scope Authorization Checks
                ↓
        Scope Resolution & Authority Mapping
                ↓
      Effective Scope + SHA-256 Fingerprint
                ↓
         Report Registry Lookup
                ↓
       Execution Audit Persistence (DB)
                ↓
          API Response
\\\

## 3. Core Components

### 3.1 DTO Contracts (\pp/modules/reports/schemas/report_schemas.py\)
- \ReportScopeDTO\: User filter inputs (\plant_id\, \customer_id\, \operation_date\, \shift\, \dataset_type\). Normalizes inputs to uppercase and default \ALL\ values.
- \AuthoritativeScopeDTO\: Backend-resolved effective scope including \esolved_dataset_id\, \calculation_timestamp\, and \scope_fingerprint\.
- \ReportRequestDTO\: Entry payload specifying target \eport_id\, desired \ormat\, filter \scope\, and user metadata.
- \ReportExecutionResponse\: Standardized response structure reflecting execution status, effective scope, fingerprint, and duration.

### 3.2 Scope Resolver Service (\pp/modules/reports/services/scope_resolver.py\)
- Normalizes filter parameters and resolves \ALL\ semantics against authorized entity lists.
- Enforces server-side backend dataset authority (\esolved_dataset_id\).
- Computes deterministic SHA-256 fingerprint from canonical JSON representation.

### 3.3 Report Registry (\pp/modules/reports/services/report_registry.py\)
- Maintains the catalog of 12 registered platform reports.
- Validates report definitions and supported formats/filters.

### 3.4 Execution Audit Model & Service (\pp/modules/reports/models/report_execution.py\ & \pp/modules/reports/services/report_service.py\)
- Persists report execution history in \	bl_report_execution_audit\.
- Tracks validation status, record counts, dataset references, and error details.
