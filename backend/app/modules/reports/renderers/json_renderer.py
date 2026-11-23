import json
from typing import Any
import re
from datetime import datetime
from app.modules.reports.schemas.dispatch_analysis_canonical import CanonicalDispatchAnalysisReport

def format_report_date(val: str | None) -> str:
    """
    Formats a date string or ISO timestamp into DD:MM:YYYY format.
    Preserves original string if unparseable or empty.
    Examples:
      '2026-08-05' -> '05:08:2026'
      '2026-08-21T10:15:30Z' -> '21:08:2026'
      '2026/08/21' -> '21:08:2026'
    """
    if not val or not isinstance(val, str):
        return str(val or "")

    val_clean = val.strip()
    if not val_clean:
        return ""

    # Match ISO YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS
    iso_match = re.match(r"^(\d{4})[-/](\d{2})[-/](\d{2})", val_clean)
    if iso_match:
        year, month, day = iso_match.groups()
        return f"{day}:{month}:{year}"

    # Match DD-MM-YYYY or DD/MM/YYYY
    dmy_match = re.match(r"^(\d{2})[-/](\d{2})[-/](\d{4})", val_clean)
    if dmy_match:
        day, month, year = dmy_match.groups()
        return f"{day}:{month}:{year}"

    try:
        dt = datetime.fromisoformat(val_clean.replace("Z", "+00:00"))
        return dt.strftime("%d:%m:%Y")
    except Exception:
        return val_clean


STATUS_PDF_COLORS = {
    # SUCCESS / DARK GREEN
    "COMPLETED": {"bg": "#DCFCE7", "fg": "#14532D", "border": "#86EFAC"},
    "SLA COMPLETED": {"bg": "#DCFCE7", "fg": "#14532D", "border": "#86EFAC"},
    "WITHIN_SLA": {"bg": "#DCFCE7", "fg": "#14532D", "border": "#86EFAC"},
    "OPTIMAL": {"bg": "#DCFCE7", "fg": "#14532D", "border": "#86EFAC"},
    "ACTIVE": {"bg": "#DCFCE7", "fg": "#14532D", "border": "#86EFAC"},
    "PROMOTED": {"bg": "#DCFCE7", "fg": "#14532D", "border": "#86EFAC"},
    "EXECUTED": {"bg": "#DCFCE7", "fg": "#14532D", "border": "#86EFAC"},
    "SUCCESS": {"bg": "#DCFCE7", "fg": "#14532D", "border": "#86EFAC"},
    "GRADE A": {"bg": "#DCFCE7", "fg": "#14532D", "border": "#86EFAC"},
    "GRADE_A": {"bg": "#DCFCE7", "fg": "#14532D", "border": "#86EFAC"},
    "AUTHORITATIVE": {"bg": "#DCFCE7", "fg": "#14532D", "border": "#86EFAC"},
    "LOW": {"bg": "#DCFCE7", "fg": "#14532D", "border": "#86EFAC"},

    # DELAYED / RED / CRITICAL
    "DELAYED": {"bg": "#FEE2E2", "fg": "#7F1D1D", "border": "#FCA5A5"},
    "SLA DELAYED": {"bg": "#FEE2E2", "fg": "#7F1D1D", "border": "#FCA5A5"},
    "FAILED": {"bg": "#FEE2E2", "fg": "#7F1D1D", "border": "#FCA5A5"},
    "CRITICAL": {"bg": "#FEE2E2", "fg": "#7F1D1D", "border": "#FCA5A5"},
    "HIGH": {"bg": "#FEE2E2", "fg": "#7F1D1D", "border": "#FCA5A5"},
    "REJECTED": {"bg": "#FEE2E2", "fg": "#7F1D1D", "border": "#FCA5A5"},
    "HIGH_RISK": {"bg": "#FEE2E2", "fg": "#7F1D1D", "border": "#FCA5A5"},
    "SCOPE_VALIDATION_FAILED": {"bg": "#FEE2E2", "fg": "#7F1D1D", "border": "#FCA5A5"},

    # WARNING / AMBER / PENDING / IN_PROGRESS / ATTENTION
    "WARNING": {"bg": "#FEF3C7", "fg": "#78350F", "border": "#FDE68A"},
    "ATTENTION": {"bg": "#FEF3C7", "fg": "#78350F", "border": "#FDE68A"},
    "MEDIUM": {"bg": "#FEF3C7", "fg": "#78350F", "border": "#FDE68A"},
    "PENDING": {"bg": "#FEF3C7", "fg": "#78350F", "border": "#FDE68A"},
    "IN_PROGRESS": {"bg": "#FEF3C7", "fg": "#78350F", "border": "#FDE68A"},
    "DEFERRED": {"bg": "#FEF3C7", "fg": "#78350F", "border": "#FDE68A"},
    "RECOMMENDED": {"bg": "#FEF3C7", "fg": "#78350F", "border": "#FDE68A"},
    "IN_TRANSIT": {"bg": "#FEF3C7", "fg": "#78350F", "border": "#FDE68A"},
    "AT_RISK": {"bg": "#FEF3C7", "fg": "#78350F", "border": "#FDE68A"},
    "QUEUED": {"bg": "#FEF3C7", "fg": "#78350F", "border": "#FDE68A"},
    "GRADE B": {"bg": "#FEF3C7", "fg": "#78350F", "border": "#FDE68A"},
    "GRADE_B": {"bg": "#FEF3C7", "fg": "#78350F", "border": "#FDE68A"},

    # NEUTRAL / MUTED
    "NO_DATA": {"bg": "#F1F5F9", "fg": "#475569", "border": "#CBD5E1"},
    "PURGED": {"bg": "#F1F5F9", "fg": "#475569", "border": "#CBD5E1"},
    "INFO": {"bg": "#E0F2FE", "fg": "#075985", "border": "#BAE6FD"},
    "OPEN": {"bg": "#FEF3C7", "fg": "#78350F", "border": "#FDE68A"},
}


def get_status_pdf_style(status: str) -> dict:
    """Returns background and text color dict for PDF paragraph styling."""
    key = str(status or "").upper().strip()
    return STATUS_PDF_COLORS.get(key, {"bg": "#F1F5F9", "fg": "#334155", "border": "#CBD5E1"})


STATUS_XLSX_COLORS = {
    # SUCCESS / DARK GREEN
    "COMPLETED": {"fill": "DCFCE7", "font": "14532D"},
    "SLA COMPLETED": {"fill": "DCFCE7", "font": "14532D"},
    "WITHIN_SLA": {"fill": "DCFCE7", "font": "14532D"},
    "OPTIMAL": {"fill": "DCFCE7", "font": "14532D"},
    "ACTIVE": {"fill": "DCFCE7", "font": "14532D"},
    "PROMOTED": {"fill": "DCFCE7", "font": "14532D"},
    "EXECUTED": {"fill": "DCFCE7", "font": "14532D"},
    "SUCCESS": {"fill": "DCFCE7", "font": "14532D"},
    "GRADE A": {"fill": "DCFCE7", "font": "14532D"},
    "GRADE_A": {"fill": "DCFCE7", "font": "14532D"},
    "AUTHORITATIVE": {"fill": "DCFCE7", "font": "14532D"},
    "LOW": {"fill": "DCFCE7", "font": "14532D"},

    # DELAYED / RED / CRITICAL
    "DELAYED": {"fill": "FEE2E2", "font": "7F1D1D"},
    "SLA DELAYED": {"fill": "FEE2E2", "font": "7F1D1D"},
    "FAILED": {"fill": "FEE2E2", "font": "7F1D1D"},
    "CRITICAL": {"fill": "FEE2E2", "font": "7F1D1D"},
    "HIGH": {"fill": "FEE2E2", "font": "7F1D1D"},
    "REJECTED": {"fill": "FEE2E2", "font": "7F1D1D"},
    "HIGH_RISK": {"fill": "FEE2E2", "font": "7F1D1D"},
    "SCOPE_VALIDATION_FAILED": {"fill": "FEE2E2", "font": "7F1D1D"},

    # WARNING / AMBER / PENDING / IN_PROGRESS / ATTENTION
    "WARNING": {"fill": "FEF3C7", "font": "78350F"},
    "ATTENTION": {"fill": "FEF3C7", "font": "78350F"},
    "MEDIUM": {"fill": "FEF3C7", "font": "78350F"},
    "PENDING": {"fill": "FEF3C7", "font": "78350F"},
    "IN_PROGRESS": {"fill": "FEF3C7", "font": "78350F"},
    "DEFERRED": {"fill": "FEF3C7", "font": "78350F"},
    "RECOMMENDED": {"fill": "FEF3C7", "font": "78350F"},
    "IN_TRANSIT": {"fill": "FEF3C7", "font": "78350F"},
    "AT_RISK": {"fill": "FEF3C7", "font": "78350F"},
    "QUEUED": {"fill": "FEF3C7", "font": "78350F"},
    "GRADE B": {"fill": "FEF3C7", "font": "78350F"},
    "GRADE_B": {"fill": "FEF3C7", "font": "78350F"},

    # NEUTRAL / MUTED
    "NO_DATA": {"fill": "F1F5F9", "font": "334155"},
    "PURGED": {"fill": "F1F5F9", "font": "334155"},
    "INFO": {"fill": "E0F2FE", "font": "075985"},
    "OPEN": {"fill": "FEF3C7", "font": "78350F"},
}


def get_status_xlsx_style(status: str) -> dict:
    """Returns fill and font hex color dict for OpenPyXL styling."""
    key = str(status or "").upper().strip()
    return STATUS_XLSX_COLORS.get(key, {"fill": "F1F5F9", "font": "334155"})



class JSONReportRenderer:
    @staticmethod
    def render(report: CanonicalDispatchAnalysisReport) -> bytes:
        data_dict = report.model_dump(mode="json")
        json_str = json.dumps(data_dict, indent=2, ensure_ascii=False)
        return json_str.encode("utf-8")

