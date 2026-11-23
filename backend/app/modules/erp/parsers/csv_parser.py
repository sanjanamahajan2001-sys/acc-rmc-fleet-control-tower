"""
CSV Streaming Parser Adapter Implementation
"""

import csv
import pathlib
import time
from collections.abc import AsyncGenerator
from typing import Any

import aiofiles
import psutil

from app.events.bus import EventBus
from app.events.schema import BaseEvent
from app.modules.erp.parsers.base import BaseWorkbookParser
from app.modules.erp.parsers.dtos import (
    HeaderAliasRegistry,
    ParsedRowDTO,
    ParserDiagnostic,
    ParserMetrics,
)


class CSVWorkbookParser(BaseWorkbookParser):
    """
    Streaming CSV Parser Adapter for .csv files.
    """

    def __init__(
        self,
        alias_registry: HeaderAliasRegistry | None = None,
        event_bus: EventBus | None = None,
        correlation_id: str = "sys-parser",
        request_id: str = "sys-parser",
    ):
        self.alias_registry = alias_registry or HeaderAliasRegistry()
        self.event_bus = event_bus
        self.correlation_id = correlation_id
        self.request_id = request_id
        self.metrics = ParserMetrics()

    def get_metrics(self) -> ParserMetrics:
        return self.metrics

    async def _publish_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.event_bus:
            event = BaseEvent[dict[str, Any]](
                event_type=event_type,
                payload=payload,
                correlation_id=self.correlation_id,
                request_id=self.request_id,
            )
            await self.event_bus.publish(event)

    async def parse_workbook_batches(
        self,
        file_path: pathlib.Path,
        batch_size: int = 1000,
        sheet_filter: list[str] | None = None,
    ) -> AsyncGenerator[list[ParsedRowDTO], None]:
        start_time = time.time()
        self.metrics = ParserMetrics()
        file_name = file_path.name
        sheet_name = file_path.stem

        self.metrics.discovered_sheets = [sheet_name]
        await self._publish_event(
            "erp.parser.started", {"workbook_name": file_name, "batch_size": batch_size}
        )

        if not file_path.exists():
            diag = ParserDiagnostic(
                workbook_name=file_name,
                severity="ERROR",
                message=f"CSV file not found: {file_path}",
            )
            self.metrics.diagnostics.append(diag)
            await self._publish_event("erp.parser.failed", {"error": diag.message})
            return

        current_batch: list[ParsedRowDTO] = []
        row_idx = 0

        async with aiofiles.open(file_path, mode="r", encoding="utf-8-sig") as f:
            content = await f.read()
            lines = content.splitlines()

            reader = csv.reader(lines)
            header_row = next(reader, None)

            if not header_row:
                self.metrics.diagnostics.append(
                    ParserDiagnostic(
                        workbook_name=file_name,
                        sheet_name=sheet_name,
                        severity="WARNING",
                        message="Empty CSV file",
                    )
                )
                return

            canonical_headers = [
                self.alias_registry.resolve_canonical_name(h) for h in header_row
            ]
            await self._publish_event(
                "erp.parser.header_detected",
                {"sheet_name": sheet_name, "headers": canonical_headers},
            )

            row_idx = 1
            for raw_row in reader:
                row_idx += 1
                self.metrics.total_rows += 1

                if not raw_row or all(not str(v).strip() for v in raw_row):
                    self.metrics.blank_rows += 1
                    continue

                row_dict: dict[str, Any] = {}
                for col_idx, val in enumerate(raw_row):
                    if col_idx < len(canonical_headers):
                        h_name = canonical_headers[col_idx]
                        row_dict[h_name] = val

                current_batch.append(
                    ParsedRowDTO(
                        sheet_name=sheet_name, row_number=row_idx, data=row_dict
                    )
                )
                self.metrics.processed_rows += 1

                if len(current_batch) >= batch_size:
                    self.metrics.batch_count += 1
                    yield current_batch
                    current_batch = []

            if current_batch:
                self.metrics.batch_count += 1
                yield current_batch

        elapsed = time.time() - start_time
        self.metrics.elapsed_seconds = round(elapsed, 4)
        if elapsed > 0:
            self.metrics.rows_per_second = round(
                self.metrics.processed_rows / elapsed, 2
            )

        process = psutil.Process()
        self.metrics.peak_memory_mb = round(
            process.memory_info().rss / (1024 * 1024), 2
        )

        await self._publish_event(
            "erp.parser.completed", {"processed_rows": self.metrics.processed_rows}
        )
