# Fleet Control Tower — Reporting API Guide (Phase 1)

## Base Path
\GET/POST /v1/reports\

## Endpoints

### 1. List Registered Reports
- **Route**: \GET /v1/reports\
- **Response**: List of report definitions in catalog.

### 2. Get Report Metadata
- **Route**: \GET /v1/reports/{report_id}\
- **Errors**: \404 Not Found\ if report ID is unknown.

### 3. Generate Report Request (Execution Initiation)
- **Route**: \POST /v1/reports/generate\
- **Payload**:
\\\json
{
  
