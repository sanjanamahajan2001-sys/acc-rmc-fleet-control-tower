"""
Canonical Workbook Context Definition for ERP Import Pipeline
Encapsulates workbook metadata, parser metrics, diagnostics, header mappings, sheet state, and job configuration.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.modules.erp.parsers.dtos import (
    HeaderAliasRegistry,
    ParserDiagnostic,
    ParserMetrics,
)


class CanonicalWorkbookContext(BaseModel):
    """
    Unified context envelope passed across Phase 1 pipeline stages:
    WS1.2 Storage -> WS1.3 Parser -> WS1.4 Validation/Mapping -> WS1.5 Worker Pipeline -> WS1.6 API
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Import Job Identifiers
    import_job_id: str | None = None
    job_number: str | None = None
    file_hash: str | None = None

    # Workbook File Metadata
    workbook_name: str
    file_path: str = ""
    file_size_bytes: int = 0
    mime_type: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    # Current Iterator State
    current_sheet: str | None = None
    current_row_index: int = 0
    total_sheets: int = 0
    discovered_sheets: list[str] = Field(default_factory=list)

    # Header & Alias Mappings
    header_mappings: dict[str, str] = Field(default_factory=dict)
    alias_registry: HeaderAliasRegistry = Field(default_factory=HeaderAliasRegistry)

    # Metrics & Diagnostics
    metrics: ParserMetrics = Field(default_factory=ParserMetrics)
    diagnostics: list[ParserDiagnostic] = Field(default_factory=list)

    # Processing Configuration & Stage Metadata
    batch_size: int = 1000
    config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_diagnostic(
        self,
        message: str,
        severity: str = "WARNING",
        sheet_name: str | None = None,
        row_number: int | None = None,
        column_name: str | None = None,
    ) -> None:
        """Helper method to append a structured diagnostic message."""
        diag = ParserDiagnostic(
            workbook_name=self.workbook_name,
            sheet_name=sheet_name or self.current_sheet,
            row_number=row_number or self.current_row_index,
            column_name=column_name,
            severity=severity,
            message=message,
        )
        self.diagnostics.append(diag)
        self.metrics.diagnostics.append(diag)
