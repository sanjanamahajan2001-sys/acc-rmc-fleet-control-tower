"""
Abstract Base Excel Parser Adapter Interface
"""

import pathlib
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from app.modules.erp.parsers.dtos import ParsedRowDTO, ParserMetrics


class BaseWorkbookParser(ABC):
    """
    Abstract Base Workbook Parser interface.
    Supports memory-efficient streaming row iteration in configurable batches.
    """

    @abstractmethod
    def parse_workbook_batches(
        self,
        file_path: pathlib.Path,
        batch_size: int = 1000,
        sheet_filter: list[str] | None = None,
    ) -> AsyncGenerator[list[ParsedRowDTO], None]:
        """Stream parsed row DTOs in batches of size `batch_size`."""

    @abstractmethod
    def get_metrics(self) -> ParserMetrics:
        """Return parser metrics and diagnostics for the current parsing run."""
