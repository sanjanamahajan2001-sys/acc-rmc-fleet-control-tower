"""
OpenPyXL Streaming Excel Workbook Parser Adapter Implementation
"""

import datetime
import pathlib
import time
from collections.abc import AsyncGenerator
from typing import Any

import openpyxl
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


class OpenPyXLWorkbookParser(BaseWorkbookParser):
    """
    Streaming OpenPyXL Excel Parser Adapter (`read_only=True` mode).
    Streams rows in configurable batches without loading the entire workbook into memory.
    Targeted for 500,000+ rows under 512 MB peak RAM.
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
        workbook_name = file_path.name

        await self._publish_event(
            "erp.parser.started",
            {"workbook_name": workbook_name, "batch_size": batch_size},
        )

        if not file_path.exists():
            diag = ParserDiagnostic(
                workbook_name=workbook_name,
                severity="ERROR",
                message=f"Workbook file not found: {file_path}",
            )
            self.metrics.diagnostics.append(diag)
            await self._publish_event("erp.parser.failed", {"error": diag.message})
            return

        try:
            wb = openpyxl.load_workbook(
                filename=str(file_path), read_only=True, data_only=True
            )
        except Exception as e:  # noqa: BLE001
            diag = ParserDiagnostic(
                workbook_name=workbook_name,
                severity="ERROR",
                message=f"Corrupted or invalid Excel file: {e}",
            )
            self.metrics.diagnostics.append(diag)
            await self._publish_event("erp.parser.failed", {"error": diag.message})
            return

        sheet_names = wb.sheetnames
        self.metrics.discovered_sheets = sheet_names

        for name in sheet_names:
            await self._publish_event(
                "erp.parser.sheet_discovered", {"sheet_name": name}
            )

        for sheet_name in sheet_names:
            if sheet_filter and sheet_name not in sheet_filter:
                continue

            try:
                ws = wb[sheet_name]
            except Exception:  # noqa: BLE001, S112
                continue

            row_iter = ws.iter_rows(values_only=True)

            # Dynamic Smart Header Detection (Scans top 10 rows for table column headers)
            header_start_t = time.time()
            header_row: tuple[Any, ...] | None = None

            for raw_row in row_iter:
                if not raw_row or all(v is None for v in raw_row):
                    continue

                cell_texts = [
                    str(v).strip().lower()
                    for v in raw_row
                    if v is not None and str(v).strip() != ""
                ]
                # Must contain at least 3 columns and match key ERP header keywords
                if len(cell_texts) >= 3 and any(
                    kw in text
                    for text in cell_texts
                    for kw in (
                        "ticket",
                        "vehicle",
                        "truck",
                        "plant",
                        "date",
                        "customer",
                        "client",
                        "docket",
                        "sl",
                        "trip",
                    )
                ):
                    header_row = raw_row
                    break

            header_duration_ms = (time.time() - header_start_t) * 1000.0
            self.metrics.header_detection_duration_ms += header_duration_ms

            if not header_row:
                self.metrics.diagnostics.append(
                    ParserDiagnostic(
                        workbook_name=workbook_name,
                        sheet_name=sheet_name,
                        severity="WARNING",
                        message="Empty worksheet or missing header row",
                    )
                )
                continue

            # Normalize headers
            canonical_headers: list[str] = []
            seen_headers: set[str] = set()

            for col_idx, raw_val in enumerate(header_row):
                if raw_val is None:
                    header_name = f"column_{col_idx+1}"
                else:
                    header_name = self.alias_registry.resolve_canonical_name(
                        str(raw_val)
                    )

                if header_name in seen_headers:
                    self.metrics.diagnostics.append(
                        ParserDiagnostic(
                            workbook_name=workbook_name,
                            sheet_name=sheet_name,
                            row_number=1,
                            column_name=str(raw_val),
                            severity="WARNING",
                            message=f"Duplicate header detected and aliased: {header_name}",
                        )
                    )
                seen_headers.add(header_name)
                canonical_headers.append(header_name)

            await self._publish_event(
                "erp.parser.header_detected",
                {"sheet_name": sheet_name, "headers": canonical_headers},
            )

            # Stream Rows in Batches
            current_batch: list[ParsedRowDTO] = []
            row_idx = 1  # 1-indexed (header is row 1)

            for raw_row in row_iter:
                row_idx += 1
                self.metrics.total_rows += 1

                if not raw_row or all(v is None for v in raw_row):
                    self.metrics.blank_rows += 1
                    continue

                # Skip non-data subheader rows (descriptor titles/units under multi-line column headers)
                row_str_values = [
                    str(v).strip()
                    for v in raw_row
                    if v is not None and str(v).strip() != ""
                ]
                if not row_str_values:
                    self.metrics.blank_rows += 1
                    continue

                is_unit_or_subheader = any(
                    str(v).lower() in ("kms", "(km/h)", "km/h", "(both way)", "(hh:mm)", "hh:mm")
                    or any(u in str(v).lower() for u in ("unloading process", "retention at site", "halt at site"))
                    for v in row_str_values
                ) and not any(
                    isinstance(v, (datetime.datetime, datetime.date)) for v in raw_row
                )
                if is_unit_or_subheader:
                    self.metrics.skipped_rows += 1
                    continue

                row_dict: dict[str, Any] = {}
                for col_idx, val in enumerate(raw_row):
                    if col_idx < len(canonical_headers):
                        h_name = canonical_headers[col_idx]
                        row_dict[h_name] = val

                parsed_row = ParsedRowDTO(
                    sheet_name=sheet_name,
                    row_number=row_idx,
                    data=row_dict,
                )
                current_batch.append(parsed_row)
                self.metrics.processed_rows += 1

                if len(current_batch) >= batch_size:
                    self.metrics.batch_count += 1
                    await self._publish_event(
                        "erp.parser.batch_processed",
                        {
                            "sheet_name": sheet_name,
                            "batch_count": self.metrics.batch_count,
                            "batch_size": len(current_batch),
                        },
                    )
                    yield current_batch
                    current_batch = []

            if current_batch:
                self.metrics.batch_count += 1
                await self._publish_event(
                    "erp.parser.batch_processed",
                    {
                        "sheet_name": sheet_name,
                        "batch_count": self.metrics.batch_count,
                        "batch_size": len(current_batch),
                    },
                )
                yield current_batch

        wb.close()

        # Finalize Metrics
        elapsed = time.time() - start_time
        self.metrics.elapsed_seconds = round(elapsed, 4)
        if elapsed > 0:
            self.metrics.rows_per_second = round(
                self.metrics.processed_rows / elapsed, 2
            )

        # Track Peak Memory
        process = psutil.Process()
        self.metrics.peak_memory_mb = round(
            process.memory_info().rss / (1024 * 1024), 2
        )

        await self._publish_event(
            "erp.parser.completed",
            {
                "processed_rows": self.metrics.processed_rows,
                "elapsed_seconds": self.metrics.elapsed_seconds,
                "rows_per_second": self.metrics.rows_per_second,
                "peak_memory_mb": self.metrics.peak_memory_mb,
            },
        )
