"""
Parser Diagnostic, Header Alias Registry, and DTO Definitions for ERP Workbook Parser Engine
"""

import re
from typing import Any, ClassVar

from pydantic import BaseModel, Field


class ParserDiagnostic(BaseModel):
    """
    Structured parser diagnostic message capturing warnings, errors, and sheet metadata.
    """

    workbook_name: str
    sheet_name: str | None = None
    row_number: int | None = None
    column_name: str | None = None
    severity: str = Field(default="WARNING", description="WARNING or ERROR")
    message: str


class ParserMetrics(BaseModel):
    """
    Performance and diagnostic metrics recorded during workbook parsing.
    """

    total_rows: int = 0
    processed_rows: int = 0
    blank_rows: int = 0
    skipped_rows: int = 0
    batch_count: int = 0
    elapsed_seconds: float = 0.0
    rows_per_second: float = 0.0
    peak_memory_mb: float = 0.0
    header_detection_duration_ms: float = 0.0
    discovered_sheets: list[str] = Field(default_factory=list)
    diagnostics: list[ParserDiagnostic] = Field(default_factory=list)


class ParsedRowDTO(BaseModel):
    """
    Generic canonical DTO representing a single normalized workbook row.
    """

    sheet_name: str
    row_number: int
    data: dict[str, Any]


class HeaderAliasRegistry:
    """
    Registry for normalizing varied Excel header titles into canonical entity attribute names.
    Supports regex normalization, whitespace stripping, and custom alias maps.
    """

    DEFAULT_ALIAS_MAP: ClassVar[dict[str, str]] = {
        # Plant
        "plant_code": "plant_code",
        "plant_name": "plant_name",
        "batch_plant": "plant_name",
        "plant_id": "plant_code",
        "plant": "plant_name",
        "unit": "plant_name",
        "location": "plant_name",
        # Ticket / Dispatch / Docket
        "ticket_no": "ticket_number",
        "ticket_number": "ticket_number",
        "ticket_id": "ticket_number",
        "ticketnum": "ticket_number",
        "docket_no": "ticket_number",
        "docket_number": "ticket_number",
        "sl_no": "ticket_number",
        "serial_no": "ticket_number",
        "dispatch_no": "dispatch_number",
        "dispatch_number": "dispatch_number",
        # Trip Aliases
        "trip_no": "trip_number",
        "trip_number": "trip_number",
        "trip_id": "trip_number",
        "trip": "trip_number",
        # Customer
        "customer": "customer_name",
        "customer_name": "customer_name",
        "customer_code": "customer_code",
        "customer_id": "customer_code",
        "client_name": "customer_name",
        "party_name": "customer_name",
        "client": "customer_name",
        # Vehicle & Driver
        "truck_no": "vehicle_code",
        "truck_number": "vehicle_code",
        "vehicle_id": "vehicle_code",
        "vehicle_code": "vehicle_code",
        "vehicle_no": "vehicle_code",
        "vehicle": "vehicle_code",
        "mixer_no": "vehicle_code",
        "tm_no": "vehicle_code",
        "license_plate": "license_plate",
        "driver_name": "driver_name",
        "driver": "driver_name",
        "driver_id": "employee_id",
        "employee_id": "employee_id",
        # Date Aliases
        "dispatch_date": "dispatch_date",
        "delivery_date": "dispatch_date",
        "ticket_date": "dispatch_date",
        "date": "dispatch_date",
        "chrg_date": "dispatch_date",
        "date_out": "dispatch_date",
        "date_in": "dispatch_date",
        "plant_out_date": "dispatch_date",
        # Product & Quantity
        "product_code": "product_code",
        "product_name": "product_name",
        "product": "product_name",
        "grade": "product_name",
        "mix_design": "product_name",
        "concrete_grade": "product_name",
        "quantity_m3": "volume_m3",
        "delivered_qty": "volume_m3",
        "volume_m3": "volume_m3",
        "volume": "volume_m3",
        "qty": "volume_m3",
        "qty_m3": "volume_m3",
        "sale_qty": "volume_m3",
        # Telemetry & Site Timestamps
        "address": "site_address",
        "unloading_place": "site_address",
        "site_name": "site_address",
        "destination": "site_address",
        "time_of_plant_out": "time_out",
        "plant_out_time": "time_out",
        "t1_plant_site": "t1_transit_mins",
        "t2a_holding_at_site": "t2a_holding_mins",
        "holding_at_site": "t2a_holding_mins",
        "t2b_unloading_at_site": "t2b_unloading_mins",
        "halt_at_site_during_unloading_process": "t2b_unloading_mins",
        "unloading_time": "unloading_duration_mins",
        "total_unloading_time": "unloading_duration_mins",
        "unloading_coordinates": "unloading_coordinates",
        "coordinates": "unloading_coordinates",
        "gps_coordinates": "unloading_coordinates",
        "site_coordinates": "unloading_coordinates",
        "t2c_retention_at_site": "t2c_retention_mins",
        "t3_site_plant": "t3_return_mins",
        "time_of_plant_in": "time_in",
        "plant_in_time": "time_in",
        "cycle_time": "cycle_time",
        "distance": "distance_km",
        "distance_travelled": "distance_km",
        "km_run": "distance_km",
    }

    def __init__(self, custom_alias_map: dict[str, str] | None = None):
        self.alias_map = self.DEFAULT_ALIAS_MAP.copy()
        if custom_alias_map:
            for raw_k, canonical_v in custom_alias_map.items():
                normalized_k = self.normalize_header_name(raw_k)
                self.alias_map[normalized_k] = canonical_v

    @staticmethod
    def normalize_header_name(raw_header: str) -> str:
        """
        Normalize raw cell string:
        Strips whitespace, lowers case, replaces special characters/spaces/hyphens with underscores.
        """
        if not raw_header:
            return ""
        text = str(raw_header).strip().lower()
        text = re.sub(r"[^a-z0-9]", "_", text)
        text = re.sub(r"_+", "_", text)
        return text.strip("_")

    def resolve_canonical_name(self, raw_header: str) -> str:
        """Resolve raw Excel header to canonical entity field name."""
        normalized = self.normalize_header_name(raw_header)
        return self.alias_map.get(normalized, normalized)
