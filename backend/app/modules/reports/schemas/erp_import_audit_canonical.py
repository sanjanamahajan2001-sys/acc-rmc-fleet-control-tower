from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict
from app.modules.reports.schemas.report_schemas import ReportStatus


class ReportMetadataDTO(BaseModel):
    execution_id: str
    report_id: str = "erp_import_audit"
    report_name: str = "ERP Import Audit Report"
    generated_at: str = ""
    requested_by: str = "SYSTEM"


class ERPImportAuditKPISummary(BaseModel):
    total_import_jobs: int = 0
    total_rows_received: int = 0
    total_rows_processed: int = 0
    total_errors: int = 0
    successful_jobs_count: int = 0

    model_config = ConfigDict(frozen=False)


class ERPImportJobRecord(BaseModel):
    job_id: str
    job_number: str
    status: str
    provider: str = "ExcelERPProvider"
    file_name: str
    file_hash: str
    total_rows: int = 0
    processed_rows: int = 0
    error_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class CanonicalERPImportAuditReport(BaseModel):
    schema_version: str = "1.0"
    metadata: ReportMetadataDTO
    requested_scope: Dict[str, Any]
    effective_scope: Dict[str, Any]
    scope_fingerprint: str
    status: ReportStatus
    record_count: int
    kpis: ERPImportAuditKPISummary
    records: List[ERPImportJobRecord] = []
    exceptions: List[Dict[str, Any]] = []

    model_config = ConfigDict(frozen=False)
