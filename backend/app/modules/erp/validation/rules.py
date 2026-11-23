"""
Multi-Layer Validation Rules Subsystem: Field, Business Rule, Cross-Sheet, and Dependency Graph Validation
"""

import re
from datetime import datetime
from uuid import UUID

from app.modules.erp.parsers.dtos import ParsedRowDTO
from app.modules.erp.validation.schemas import (
    CanonicalCustomerDTO,
    CanonicalDispatchDTO,
    CanonicalDriverDTO,
    CanonicalInvoiceDTO,
    CanonicalOrderDTO,
    CanonicalPlantDTO,
    CanonicalSiteDTO,
    CanonicalTicketDTO,
    CanonicalTripDTO,
    CanonicalVehicleDTO,
    PersistableBatch,
    ValidationErrorCode,
    ValidationIssue,
)


class Layer1FieldValidator:
    """
    Layer 1: Field-level validation (Data types, required fields, formats, lengths, ranges).
    """

    @staticmethod
    def validate_dispatch_row(
        row: ParsedRowDTO, workbook_name: str
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        data = row.data

        # Parse and preserve actual workbook dispatch_date
        raw_date = data.get("dispatch_date")
        if raw_date is not None and str(raw_date).strip() != "":
            if isinstance(raw_date, datetime):
                data["dispatch_date"] = raw_date
            else:
                try:
                    data["dispatch_date"] = datetime.fromisoformat(
                        str(raw_date).strip()
                    )
                except (ValueError, TypeError):
                    data["dispatch_date"] = str(raw_date).strip()

        # Handle Trip No vs Ticket No domain distinction
        trip_num = data.get("trip_number")
        ticket_num = data.get("ticket_number")

        # Synthetic fallback ticket generation ONLY if no ticket identifier exists
        if not ticket_num:
            if trip_num:
                data["ticket_number"] = f"SYNTH-TCK-TRIP-{trip_num}"
            else:
                data["ticket_number"] = f"SYNTH-TCK-ROW-{row.row_number}"

        required_fields = [
            "ticket_number",
            "dispatch_date",
        ]
        for field in required_fields:
            val = data.get(field)
            if val is None or str(val).strip() == "":
                issues.append(
                    ValidationIssue(
                        workbook_name=workbook_name,
                        sheet_name=row.sheet_name,
                        row_number=row.row_number,
                        column_name=field,
                        severity="ERROR",
                        error_code=ValidationErrorCode.MISSING_FIELD,
                        message=f"Mandatory Tier 1 field '{field}' is missing or blank",
                        suggested_correction=f"Provide valid value for '{field}'",
                    )
                )

        # Tier 2 Business Recommended fields check (Generates Warning, Uses Canonical Fallback)
        recommended_fields = ["vehicle_code", "plant_name", "customer_name"]
        for field in recommended_fields:
            val = data.get(field)
            if val is None or str(val).strip() == "":
                issues.append(
                    ValidationIssue(
                        workbook_name=workbook_name,
                        sheet_name=row.sheet_name,
                        row_number=row.row_number,
                        column_name=field,
                        severity="WARNING",
                        error_code=ValidationErrorCode.MISSING_FIELD,
                        message=f"Tier 2 field '{field}' is missing; using canonical fallback",
                    )
                )

        # Volume range check
        volume = data.get("volume_m3")
        if volume is not None:
            try:
                v_float = float(volume)
                if v_float <= 0.0 or v_float > 100.0:
                    issues.append(
                        ValidationIssue(
                            workbook_name=workbook_name,
                            sheet_name=row.sheet_name,
                            row_number=row.row_number,
                            column_name="volume_m3",
                            severity="WARNING",
                            error_code=ValidationErrorCode.RANGE_OUT_OF_BOUNDS,
                            message=f"Dispatched volume '{v_float}' m3 is outside typical range (0.1 - 100.0 m3)",
                        )
                    )
            except (ValueError, TypeError):
                issues.append(
                    ValidationIssue(
                        workbook_name=workbook_name,
                        sheet_name=row.sheet_name,
                        row_number=row.row_number,
                        column_name="volume_m3",
                        severity="ERROR",
                        error_code=ValidationErrorCode.TYPE_CONVERSION_FAILED,
                        message=f"Invalid numeric value for volume_m3: '{volume}'",
                    )
                )

        return issues


class Layer2BusinessRuleValidator:
    """
    Layer 2: Business rule validation & duplicate detection.
    """

    def __init__(self) -> None:
        self.seen_tickets: set[str] = set()
        self.seen_dispatches: set[str] = set()
        self.seen_invoices: set[str] = set()

    def validate_duplicates(
        self,
        ticket_number: str | None,
        dispatch_number: str | None,
        row: ParsedRowDTO,
        workbook_name: str,
    ) -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []

        if ticket_number:
            if ticket_number in self.seen_tickets:
                issues.append(
                    ValidationIssue(
                        workbook_name=workbook_name,
                        sheet_name=row.sheet_name,
                        row_number=row.row_number,
                        column_name="ticket_number",
                        severity="ERROR",
                        error_code=ValidationErrorCode.DUPLICATE_TICKET,
                        message=f"Duplicate ticket number '{ticket_number}' detected in workbook",
                    )
                )
            else:
                self.seen_tickets.add(ticket_number)

        if dispatch_number:
            if dispatch_number in self.seen_dispatches:
                issues.append(
                    ValidationIssue(
                        workbook_name=workbook_name,
                        sheet_name=row.sheet_name,
                        row_number=row.row_number,
                        column_name="dispatch_number",
                        severity="ERROR",
                        error_code=ValidationErrorCode.DUPLICATE_DISPATCH,
                        message=f"Duplicate dispatch number '{dispatch_number}' detected in workbook",
                    )
                )
            else:
                self.seen_dispatches.add(dispatch_number)

        return issues


class RelationshipDependencyGraph:
    """
    Layer 3 & 4: Cross-sheet relationship resolution & dependency graph builder.
    Resolves foreign keys (Plant, Customer, Vehicle, Driver, Ticket, Dispatch) and orders entities for atomic persistence.
    """

    def __init__(self) -> None:
        self.plants_map: dict[str, CanonicalPlantDTO] = {}
        self.sites_map: dict[str, CanonicalSiteDTO] = {}
        self.customers_map: dict[str, CanonicalCustomerDTO] = {}
        self.vehicles_map: dict[str, CanonicalVehicleDTO] = {}
        self.drivers_map: dict[str, CanonicalDriverDTO] = {}
        self.orders_map: dict[str, CanonicalOrderDTO] = {}
        self.tickets_map: dict[str, CanonicalTicketDTO] = {}
        self.dispatches_map: dict[str, CanonicalDispatchDTO] = {}
        self.invoices_map: dict[str, CanonicalInvoiceDTO] = {}
        self.trips_map: dict[str, CanonicalTripDTO] = {}

    def get_or_create_plant(self, plant_name: str) -> CanonicalPlantDTO:
        code = re.sub(r"[^a-zA-Z0-9]", "_", plant_name).upper()
        if code not in self.plants_map:
            self.plants_map[code] = CanonicalPlantDTO(code=code, name=plant_name)
        return self.plants_map[code]

    def get_or_create_customer(self, customer_code: str | None = None, customer_name: str | None = None) -> CanonicalCustomerDTO:
        name_val = customer_name or customer_code or "DEFAULT_CUSTOMER"
        raw_code = customer_code if customer_code else f"CUST_{name_val}"
        code_val = re.sub(r'[^a-zA-Z0-9]', '_', raw_code).upper()
        if code_val not in self.customers_map:
            self.customers_map[code_val] = CanonicalCustomerDTO(
                code=code_val, name=name_val
            )
        return self.customers_map[code_val]

    def get_or_create_site(
        self,
        site_code: str,
        site_name: str,
        plant_code: str,
        plant_id: UUID | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> CanonicalSiteDTO:
        code = site_code if site_code else f"SITE_{re.sub(r'[^a-zA-Z0-9]', '_', site_name).upper()}"
        if code not in self.sites_map:
            self.sites_map[code] = CanonicalSiteDTO(
                code=code,
                name=site_name,
                plant_code=plant_code,
                plant_id=plant_id,
                latitude=latitude,
                longitude=longitude,
            )
        else:
            # If existing site record had NULL coords, populate if newly discovered in this row
            if self.sites_map[code].latitude is None and latitude is not None:
                self.sites_map[code].latitude = latitude
                self.sites_map[code].longitude = longitude
        return self.sites_map[code]

    def get_or_create_vehicle(
        self, vehicle_code: str, plant_code: str | None = None
    ) -> CanonicalVehicleDTO:
        code = vehicle_code.strip().upper()
        if code not in self.vehicles_map:
            plant = self.plants_map.get(plant_code) if plant_code else None
            self.vehicles_map[code] = CanonicalVehicleDTO(
                code=code,
                plant_code=plant_code or "DEFAULT",
                plant_id=plant.id if plant else None,
            )
        return self.vehicles_map[code]

    def get_or_create_order(
        self, customer_code: str, customer_id: UUID | None, order_date: datetime | None = None
    ) -> CanonicalOrderDTO:
        order_num = f"ORD_{customer_code}"
        if order_num not in self.orders_map:
            self.orders_map[order_num] = CanonicalOrderDTO(
                order_number=order_num,
                customer_code=customer_code,
                customer_id=customer_id,
                order_date=order_date or datetime.now(timezone.utc),
                is_generated=True,
                generation_reason="No ERP Order Number in Register; Anchored to Master Customer",
            )
        return self.orders_map[order_num]

    def get_or_create_driver(self, driver_name: str) -> CanonicalDriverDTO:
        emp_id = f"DRV_{re.sub(r'[^a-zA-Z0-9]', '_', driver_name).upper()}"
        is_synth = driver_name == "DEFAULT_DRIVER"
        if emp_id not in self.drivers_map:
            self.drivers_map[emp_id] = CanonicalDriverDTO(
                employee_id=emp_id,
                name=driver_name,
                is_generated=is_synth,
                generation_reason="Workbook contains no Driver column" if is_synth else None,
            )
        return self.drivers_map[emp_id]

    def build_persistable_batch(self) -> PersistableBatch:
        """
        Produce dependency-ordered batch ready for transaction commit:
        Plant -> Site -> Customer -> Vehicle -> Driver -> Order -> Ticket -> Dispatch -> Invoice -> Trip
        """
        return PersistableBatch(
            plants=list(self.plants_map.values()),
            sites=list(self.sites_map.values()),
            customers=list(self.customers_map.values()),
            vehicles=list(self.vehicles_map.values()),
            drivers=list(self.drivers_map.values()),
            orders=list(self.orders_map.values()),
            tickets=list(self.tickets_map.values()),
            dispatches=list(self.dispatches_map.values()),
            invoices=list(self.invoices_map.values()),
            trips=list(self.trips_map.values()),
        )
