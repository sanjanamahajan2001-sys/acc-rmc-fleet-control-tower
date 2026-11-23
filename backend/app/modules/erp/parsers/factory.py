"""
Workbook Parser Factory for Automatic Adapter Selection
"""

import pathlib

from app.core.exceptions import DomainValidationError
from app.events.bus import EventBus
from app.modules.erp.parsers.base import BaseWorkbookParser
from app.modules.erp.parsers.csv_parser import CSVWorkbookParser
from app.modules.erp.parsers.dtos import HeaderAliasRegistry
from app.modules.erp.parsers.openpyxl_parser import OpenPyXLWorkbookParser


def get_workbook_parser(
    file_path: pathlib.Path | str,
    alias_registry: HeaderAliasRegistry | None = None,
    event_bus: EventBus | None = None,
    correlation_id: str = "sys-parser",
    request_id: str = "sys-parser",
) -> BaseWorkbookParser:
    """
    Automatic parser selection based on file extension (.xlsx, .xlsm, .xls, .csv).
    """
    path = pathlib.Path(file_path)
    suffix = path.suffix.lower()

    if suffix in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        return OpenPyXLWorkbookParser(
            alias_registry=alias_registry,
            event_bus=event_bus,
            correlation_id=correlation_id,
            request_id=request_id,
        )
    elif suffix in (".csv", ".txt"):
        return CSVWorkbookParser(
            alias_registry=alias_registry,
            event_bus=event_bus,
            correlation_id=correlation_id,
            request_id=request_id,
        )
    elif suffix == ".xls":
        # OpenPyXL also handles basic read-only xls or fallbacks
        return OpenPyXLWorkbookParser(
            alias_registry=alias_registry,
            event_bus=event_bus,
            correlation_id=correlation_id,
            request_id=request_id,
        )
    else:
        raise DomainValidationError(f"Unsupported workbook file extension: '{suffix}'")
