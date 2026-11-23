# Fleet Control Tower — Reporting Subsystem Testing Guide (Phase 1)

## Running Phase 1 Reporting Tests

Execute the Phase 1 test suite inside the WSL virtual environment:

\\\ash
cd /home/sanjana/fleet-operational-intelligence-platform/backend
source venv/bin/activate
PYTHONPATH=. pytest app/modules/reports/tests/test_phase1_reporting_foundation.py -v
\\\

## Test Suite Scope
1. DTO Normalization & Validation
2. Scope Fingerprint Determinism & Variation Checks
3. Report Registry Catalog Definitions
4. Scope Authorization Checks
5. Database Migration Integrity
