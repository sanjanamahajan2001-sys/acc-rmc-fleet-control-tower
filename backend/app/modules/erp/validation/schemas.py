"""
Validation Report, Import Statistics, Validation Error Schemas, and Canonical Validation DTOs
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ValidationErrorCode(str, Enum):
    """
    Strongly typed Validation Error Codes for frontend localization, audit logs, filtering, and analytics.
    """

    MISSING_FIELD = "VAL_REQUIRED_FIELD_MISSING"
    DUPLICATE_TICKET = "VAL_DUPLICATE_TICKET_NUMBER"
    DUPLICATE_DISPATCH = "VAL_DUPLICATE_DISPATCH_NUMBER"
    DUPLICATE_INVOICE = "VAL_DUPLICATE_INVOICE_NUMBER"
    INVALID_CUSTOMER = "VAL_INVALID_CUSTOMER_REFERENCE"
    INVALID_VEHICLE = "VAL_INVALID_VEHICLE_CODE"
    INVALID_PLANT = "VAL_INVALID_PLANT_REFERENCE"
    INVALID_SITE = "VAL_INVALID_SITE_REFERENCE"
    INVALID_DATE = "VAL_INVALID_DATE_FORMAT"
    RANGE_OUT_OF_BOUNDS = "VAL_NUMERIC_RANGE_OUT_OF_BOUNDS"
    TYPE_CONVERSION_FAILED = "VAL_TYPE_CONVERSION_FAILED"
    GENERIC_ERROR = "VAL_GENERIC_ERROR"


class ValidationIssue(BaseModel):
    """
    Structured validation diagnostic report item for WS1.4 multi-layer validation engine.
    """

    workbook_name: str
    sheet_name: str | None = None
    row_number: int | None = None
    column_name: str | None = None
    severity: str = Field(default="ERROR", description="FATAL, ERROR, WARNING, or INFO")
    error_code: ValidationErrorCode = Field(default=ValidationErrorCode.GENERIC_ERROR)
    message: str
    suggested_correction: str | None = None


class ValidationReport(BaseModel):
    """
    Structured validation summary report generated post-validation.
    """

    import_job_id: str | None = None
    workbook_name: str
    total_rows_inspected: int = 0
    valid_rows_count: int = 0
    invalid_rows_count: int = 0
    duplicate_rows_count: int = 0
    warnings_count: int = 0
    errors_count: int = 0
    fatal_errors_count: int = 0
    is_valid: bool = True
    issues: list[ValidationIssue] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)


class ValidationStatistics(BaseModel):
    """
    Performance profiling statistics for validation & dependency resolution.
    """

    rows_processed: int = 0
    rows_accepted: int = 0
    rows_rejected: int = 0
    warnings_count: int = 0
    errors_count: int = 0
    duplicates_count: int = 0
    validation_duration_ms: float = 0.0
    relationship_resolution_duration_ms: float = 0.0


class PersistableBatchMetadata(BaseModel):
    """
    Metadata for tracking and auditing persistable batches during retries and transactional execution.
    """

    batch_uuid: str = Field(default_factory=lambda: str(uuid4()))
    import_job_id: str | None = None
    workbook_hash: str | None = None
    validation_version: str = "1.4.0"
    parser_version: str = "1.3.0"
    validation_duration_ms: float = 0.0
    mapping_duration_ms: float = 0.0
    total_row_count: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# CANONICAL IN-MEMORY VALIDATED DTOs (Independent of SQLAlchemy)
# =============================================================================


class BaseCanonicalEntity(BaseModel):
    is_generated: bool = False
    generation_reason: str | None = None
    source_lineage: dict[str, Any] | None = None
    model_config = ConfigDict(from_attributes=True)


class CanonicalPlantDTO(BaseCanonicalEntity):
    id: UUID = Field(default_factory=uuid4)
    code: str
    name: str
    location: str | None = None
    plant_type: str | None = "READY_MIX_BATCH"
    latitude: float | None = None
    longitude: float | None = None


class CanonicalSiteDTO(BaseCanonicalEntity):
    id: UUID = Field(default_factory=uuid4)
    code: str
    name: str
    plant_code: str
    plant_id: UUID | None = None
    original_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    geofence_radius_meters: float | None = 200.0


class CanonicalCustomerDTO(BaseCanonicalEntity):
    id: UUID = Field(default_factory=uuid4)
    code: str
    name: str
    tax_id: str | None = None
    original_erp_address: str | None = None
    normalized_address: str | None = None
    resolver_confidence: float | None = 1.0


class CanonicalVehicleDTO(BaseCanonicalEntity):
    id: UUID = Field(default_factory=uuid4)
    code: str
    license_plate: str | None = None
    plant_code: str | None = None
    plant_id: UUID | None = None
    capacity_m3: float | None = None
    vehicle_type: str | None = "MIXER_TRUCK"
    fleet_category: str | None = None
    ownership: str | None = "OWNED"


class CanonicalDriverDTO(BaseCanonicalEntity):
    id: UUID = Field(default_factory=uuid4)
    employee_id: str
    name: str
    license_number: str | None = None


class CanonicalOrderDTO(BaseCanonicalEntity):
    id: UUID = Field(default_factory=uuid4)
    order_number: str
    customer_code: str
    customer_id: UUID | None = None
    order_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CanonicalTicketDTO(BaseCanonicalEntity):
    id: UUID = Field(default_factory=uuid4)
    ticket_number: str
    order_number: str | None = None
    order_id: UUID | None = None
    ticket_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    volume_m3: float = 0.0


class CanonicalDispatchDTO(BaseCanonicalEntity):
    id: UUID = Field(default_factory=uuid4)
    dispatch_number: str
    ticket_number: str
    ticket_id: UUID | None = None
    vehicle_code: str
    vehicle_id: UUID | None = None
    driver_employee_id: str | None = None
    driver_id: UUID | None = None
    plant_code: str
    plant_id: UUID | None = None
    customer_code: str
    customer_id: UUID | None = None
    dispatch_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    time_out: str | None = None
    date_in: datetime | None = None
    time_in: str | None = None
    t1_transit_mins: float | None = None
    t2a_holding_mins: float | None = None
    t2b_unloading_mins: float | None = None
    unloading_duration_mins: float | None = None
    t2c_retention_mins: float | None = None
    t3_return_mins: float | None = None
    cycle_time: str | None = None
    distance_km: float | None = None
    volume_m3: float = 0.0
    status: str = "COMPLETED"
    import_batch_id: UUID | None = None
    parser_version: str | None = "v3.1.0"
    source_system: str | None = "ERP_REGISTER"
    excel_row: int | None = None
    checksum: str | None = None
    telemetry_matched: bool = False
    telemetry_match_score: float | None = 0.0


class CanonicalInvoiceDTO(BaseCanonicalEntity):
    id: UUID = Field(default_factory=uuid4)
    invoice_number: str
    dispatch_number: str
    dispatch_id: UUID | None = None
    customer_code: str
    customer_id: UUID | None = None
    total_amount: float = 0.0
    invoice_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CanonicalTripDTO(BaseCanonicalEntity):
    id: UUID = Field(default_factory=uuid4)
    trip_number: str
    dispatch_number: str
    dispatch_id: UUID | None = None
    vehicle_code: str
    vehicle_id: UUID | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    distance_km: float = 0.0


class PersistableBatch(BaseModel):
    """
    Dependency-ordered, fully validated canonical payload batch prepared for atomic UnitOfWork transaction commit.
    Includes PersistableBatchMetadata for auditability & retry tracking.
    """

    metadata: PersistableBatchMetadata = Field(default_factory=PersistableBatchMetadata)
    plants: list[CanonicalPlantDTO] = Field(default_factory=list)
    sites: list[CanonicalSiteDTO] = Field(default_factory=list)
    customers: list[CanonicalCustomerDTO] = Field(default_factory=list)
    vehicles: list[CanonicalVehicleDTO] = Field(default_factory=list)
    drivers: list[CanonicalDriverDTO] = Field(default_factory=list)
    orders: list[CanonicalOrderDTO] = Field(default_factory=list)
    tickets: list[CanonicalTicketDTO] = Field(default_factory=list)
    dispatches: list[CanonicalDispatchDTO] = Field(default_factory=list)
    invoices: list[CanonicalInvoiceDTO] = Field(default_factory=list)
    trips: list[CanonicalTripDTO] = Field(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)
