"""
Canonical Mapping & Validation Engine Orchestrator
Consumes ParsedRowDTO batches and CanonicalWorkbookContext, executes multi-layer validation,
resolves entity relationships, and produces a validated PersistableBatch and ValidationReport.
"""

import re
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from app.events.bus import EventBus
from app.events.schema import BaseEvent
from app.modules.erp.parsers.context import CanonicalWorkbookContext
from app.modules.erp.parsers.dtos import ParsedRowDTO
from app.modules.erp.validation.address_engine import AddressResolutionEngine
from app.modules.erp.validation.rules import (
    Layer1FieldValidator,
    Layer2BusinessRuleValidator,
    RelationshipDependencyGraph,
)
from app.modules.erp.validation.schemas import (
    CanonicalDispatchDTO,
    CanonicalTicketDTO,
    CanonicalTripDTO,
    PersistableBatch,
    ValidationErrorCode,
    ValidationIssue,
    ValidationReport,
    ValidationStatistics,
)


class CanonicalValidationEngine:
    """
    Main Orchestrator for Phase 1 WS1.4 Validation & Canonical Mapping.
    """

    def __init__(
        self,
        event_bus: EventBus | None = None,
        correlation_id: str = "sys-val",
        request_id: str = "sys-val",
    ):
        self.event_bus = event_bus
        self.correlation_id = correlation_id
        self.request_id = request_id

    async def _publish_event(self, event_type: str, payload: dict[str, Any]) -> None:
        if self.event_bus:
            event = BaseEvent[dict[str, Any]](
                event_type=event_type,
                payload=payload,
                correlation_id=self.correlation_id,
                request_id=self.request_id,
            )
            await self.event_bus.publish(event)

    async def validate_and_map_workbook(
        self,
        row_batches: list[list[ParsedRowDTO]],
        ctx: CanonicalWorkbookContext,
    ) -> tuple[PersistableBatch, ValidationReport, ValidationStatistics]:
        """
        Validate parsed rows, map into canonical DTOs, resolve dependencies, and generate report.
        """
        start_time = time.time()
        await self._publish_event(
            "erp.validation.started", {"workbook_name": ctx.workbook_name}
        )

        field_validator = Layer1FieldValidator()
        rule_validator = Layer2BusinessRuleValidator()
        dep_graph = RelationshipDependencyGraph()

        report = ValidationReport(
            import_job_id=ctx.import_job_id,
            workbook_name=ctx.workbook_name,
        )
        stats = ValidationStatistics()

        all_issues: list[ValidationIssue] = []
        valid_rows_count = 0
        invalid_rows_count = 0
        duplicate_rows_count = 0

        # Layer 1 & Layer 2 Validation Pass
        for batch_idx, batch in enumerate(row_batches):
            await self._publish_event(
                "erp.validation.batch",
                {"batch_index": batch_idx, "batch_size": len(batch)},
            )

            for row in batch:
                stats.rows_processed += 1
                report.total_rows_inspected += 1
                row_issues: list[ValidationIssue] = []

                # Layer 1 Field Validation
                field_issues = field_validator.validate_dispatch_row(
                    row, ctx.workbook_name
                )
                row_issues.extend(field_issues)

                ticket_no = row.data.get("ticket_number")
                dispatch_no = row.data.get("dispatch_number") or ticket_no

                # Layer 2 Duplicate Detection
                dup_issues = rule_validator.validate_duplicates(
                    ticket_no, dispatch_no, row, ctx.workbook_name
                )
                row_issues.extend(dup_issues)

                if any(
                    i.error_code
                    in (
                        ValidationErrorCode.DUPLICATE_TICKET,
                        ValidationErrorCode.DUPLICATE_DISPATCH,
                        ValidationErrorCode.DUPLICATE_INVOICE,
                    )
                    for i in dup_issues
                ):
                    duplicate_rows_count += 1

                # Check if row has severe errors
                has_fatal = any(i.severity in ("FATAL", "ERROR") for i in row_issues)

                if has_fatal:
                    invalid_rows_count += 1
                    stats.rows_rejected += 1
                    all_issues.extend(row_issues)

                    for issue in row_issues:
                        if issue.severity == "WARNING":
                            stats.warnings_count += 1
                        else:
                            stats.errors_count += 1
                            await self._publish_event(
                                (
                                    "erp.validation.warning"
                                    if issue.severity == "WARNING"
                                    else "erp.validation.failed"
                                ),
                                {
                                    "error_code": issue.error_code.value,
                                    "message": issue.message,
                                },
                            )
                else:
                    valid_rows_count += 1
                    stats.rows_accepted += 1

                    # Canonical Mapping & Relationship Resolution using AddressResolutionEngine
                    plant_name = str(row.data.get("plant_name", "DEFAULT_PLANT"))
                    vehicle_code = str(row.data.get("vehicle_code", "DEFAULT_VEHICLE"))
                    volume_m3 = float(row.data.get("volume_m3") or 0.0)
                    driver_name = str(row.data.get("driver_name", "DEFAULT_DRIVER"))

                    # Resolve Address / Location text into Customer and Site
                    raw_addr = row.data.get("site_address") or row.data.get("customer_name") or row.data.get("party_name")
                    resolved_ent = AddressResolutionEngine.resolve_address(raw_addr)

                    # Extract parsed dispatch_date
                    dispatch_date_val = row.data.get("dispatch_date")
                    parsed_dt = (
                        dispatch_date_val
                        if isinstance(dispatch_date_val, datetime)
                        else datetime.now(timezone.utc)
                    )

                    # Lineage Source Payload
                    lineage_payload = {
                        "workbook_name": ctx.workbook_name,
                        "sheet_name": row.sheet_name,
                        "row_number": row.row_number,
                        "source_columns": list(row.data.keys()),
                        "confidence_score": resolved_ent.confidence_score,
                    }

                    plant = dep_graph.get_or_create_plant(plant_name)
                    plant.source_lineage = lineage_payload

                    customer = dep_graph.get_or_create_customer(resolved_ent.customer_code, resolved_ent.customer_name)
                    customer.is_generated = resolved_ent.customer_code == "DEFAULT_CUSTOMER"
                    if customer.is_generated:
                        customer.generation_reason = "Empty ERP Address cell"
                    customer.original_erp_address = raw_addr
                    customer.normalized_address = resolved_ent.customer_name
                    customer.resolver_confidence = resolved_ent.confidence_score
                    customer.source_lineage = lineage_payload

                    # Safe coordinate extraction from row data (e.g. Unloading Coordinates)
                    raw_coords = row.data.get("unloading_coordinates") or row.data.get("coordinates") or row.data.get("gps_coordinates")
                    parsed_lat, parsed_lon = None, None
                    if raw_coords is not None:
                        s_coords = str(raw_coords).strip()
                        if s_coords and s_coords.upper() not in ("NAN", "NONE", "NULL"):
                            coord_match = re.search(r"([-+]?\d{1,2}\.\d+)\s*[/,\s]\s*([-+]?\d{1,3}\.\d+)", s_coords)
                            if coord_match:
                                try:
                                    c_lat = float(coord_match.group(1))
                                    c_lon = float(coord_match.group(2))
                                    if -90.0 <= c_lat <= 90.0 and -180.0 <= c_lon <= 180.0:
                                        parsed_lat, parsed_lon = c_lat, c_lon
                                except ValueError:
                                    pass

                    site = dep_graph.get_or_create_site(
                        resolved_ent.site_code,
                        resolved_ent.site_name,
                        plant_code=plant.code,
                        plant_id=plant.id,
                        latitude=parsed_lat,
                        longitude=parsed_lon,
                    )
                    site.original_address = raw_addr
                    site.geofence_radius_meters = 200.0
                    site.source_lineage = lineage_payload

                    vehicle = dep_graph.get_or_create_vehicle(
                        vehicle_code, plant_code=plant.code
                    )
                    vehicle.vehicle_type = "MIXER_TRUCK"
                    vehicle.ownership = "OWNED"
                    vehicle.source_lineage = lineage_payload

                    order = dep_graph.get_or_create_order(customer.code, customer.id, order_date=parsed_dt)
                    order.source_lineage = lineage_payload

                    driver = dep_graph.get_or_create_driver(driver_name)
                    driver.source_lineage = lineage_payload

                    # Build Ticket DTO
                    is_tck_synth = str(ticket_no).startswith("SYNTH-TCK")
                    ticket = CanonicalTicketDTO(
                        ticket_number=str(ticket_no),
                        order_number=order.order_number,
                        order_id=order.id,
                        ticket_date=parsed_dt,
                        volume_m3=volume_m3,
                        is_generated=is_tck_synth,
                        generation_reason="ERP Ticket Number Blank; Generated from Trip/Row ID" if is_tck_synth else None,
                        source_lineage=lineage_payload,
                    )
                    dep_graph.tickets_map[ticket.ticket_number] = ticket

                    # Extract telemetry metrics from row.data
                    time_out_val = str(row.data.get("time_out")) if row.data.get("time_out") else None
                    time_in_val = str(row.data.get("time_in")) if row.data.get("time_in") else None
                    cycle_time_val = str(row.data.get("cycle_time")) if row.data.get("cycle_time") else None
                    
                    def safe_float(v: Any) -> float | None:
                        if v is None: return None
                        try: return float(v)
                        except (ValueError, TypeError): return None

                    t1_val = safe_float(row.data.get("t1_transit_mins"))
                    t2a_val = safe_float(row.data.get("t2a_holding_mins"))
                    t2b_val = safe_float(row.data.get("t2b_unloading_mins"))
                    unloading_dur_val = safe_float(row.data.get("unloading_duration_mins"))
                    t2c_val = safe_float(row.data.get("t2c_retention_mins"))
                    t3_val = safe_float(row.data.get("t3_return_mins"))
                    dist_val = safe_float(row.data.get("distance_km"))

                    dispatch = CanonicalDispatchDTO(
                        dispatch_number=str(dispatch_no),
                        ticket_number=ticket.ticket_number,
                        ticket_id=ticket.id,
                        vehicle_code=vehicle.code,
                        vehicle_id=vehicle.id,
                        driver_employee_id=driver.employee_id,
                        driver_id=driver.id,
                        plant_code=plant.code,
                        plant_id=plant.id,
                        customer_code=customer.code,
                        customer_id=customer.id,
                        dispatch_date=parsed_dt,
                        time_out=time_out_val,
                        time_in=time_in_val,
                        t1_transit_mins=t1_val,
                        t2a_holding_mins=t2a_val,
                        t2b_unloading_mins=t2b_val,
                        unloading_duration_mins=unloading_dur_val,
                        t2c_retention_mins=t2c_val,
                        t3_return_mins=t3_val,
                        cycle_time=cycle_time_val,
                        distance_km=dist_val,
                        volume_m3=volume_m3,
                        is_generated=False,
                        source_lineage=lineage_payload,
                        import_batch_id=UUID(ctx.import_job_id) if ctx.import_job_id and len(ctx.import_job_id) == 36 else None,
                        parser_version="v3.1.0",
                        source_system="ERP_REGISTER",
                        excel_row=row.row_number,
                        checksum=ctx.file_hash,
                    )
                    dep_graph.dispatches_map[dispatch.dispatch_number] = dispatch

                    # Also populate dedicated Trip record if trip_no is present
                    trip_dto = CanonicalTripDTO(
                        trip_number=str(dispatch_no),
                        dispatch_number=dispatch.dispatch_number,
                        dispatch_id=dispatch.id,
                        vehicle_code=vehicle.code,
                        vehicle_id=vehicle.id,
                        start_time=parsed_dt,
                        distance_km=dist_val or 0.0,
                        is_generated=False,
                        source_lineage=lineage_payload,
                    )
                    dep_graph.trips_map[trip_dto.trip_number] = trip_dto

        # Build Final Dependency-Ordered Persistable Batch
        rel_start_t = time.time()
        persistable_batch = dep_graph.build_persistable_batch()
        stats.relationship_resolution_duration_ms = (time.time() - rel_start_t) * 1000.0

        # Finalize Metadata on PersistableBatch
        elapsed_ms = (time.time() - start_time) * 1000.0
        persistable_batch.metadata.import_job_id = ctx.import_job_id
        persistable_batch.metadata.workbook_hash = ctx.file_hash
        persistable_batch.metadata.validation_duration_ms = elapsed_ms
        persistable_batch.metadata.mapping_duration_ms = (
            stats.relationship_resolution_duration_ms
        )
        persistable_batch.metadata.total_row_count = stats.rows_accepted

        # Finalize Report & Statistics
        elapsed_ms = (time.time() - start_time) * 1000.0
        stats.validation_duration_ms = elapsed_ms
        stats.duplicates_count = duplicate_rows_count

        report.valid_rows_count = valid_rows_count
        report.invalid_rows_count = invalid_rows_count
        report.duplicate_rows_count = duplicate_rows_count
        report.warnings_count = stats.warnings_count
        report.errors_count = stats.errors_count
        report.issues = all_issues
        report.is_valid = invalid_rows_count == 0

        if not report.is_valid:
            report.suggested_actions.append(
                "Fix invalid mandatory fields and resolve duplicate ticket numbers."
            )

        await self._publish_event(
            "erp.validation.completed",
            {
                "is_valid": report.is_valid,
                "rows_processed": stats.rows_processed,
                "rows_accepted": stats.rows_accepted,
                "rows_rejected": stats.rows_rejected,
            },
        )

        return persistable_batch, report, stats
