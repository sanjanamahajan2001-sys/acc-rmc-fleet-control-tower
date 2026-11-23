"""
ERP Canonical Models & Ingestion Metadata Database Schema
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional


from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import AuditEntity, BaseEntity, VersionedEntity

# =============================================================================
# 1. CANONICAL ENTITIES
# =============================================================================


class Plant(VersionedEntity):
    """Manufacturing or ready-mix batch plant entity."""

    __tablename__ = "plants"

    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plant_type: Mapped[str | None] = mapped_column(String(50), nullable=True, default="READY_MIX_BATCH")
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    sites: Mapped[list["Site"]] = relationship(
        "Site", back_populates="plant", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_plants_code_name", "code", "name"),)


class Site(VersionedEntity):
    """Construction or delivery job site."""

    __tablename__ = "sites"

    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    plant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    original_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    geofence_radius_meters: Mapped[float | None] = mapped_column(Float, nullable=True, default=200.0)

    plant: Mapped["Plant"] = relationship("Plant", back_populates="sites")

    __table_args__ = (Index("idx_sites_plant_code", "plant_id", "code"),)


class Customer(VersionedEntity):
    """B2B Customer or Contracting Organization."""

    __tablename__ = "customers"

    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tax_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    original_erp_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    normalized_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    resolver_confidence: Mapped[float | None] = mapped_column(Float, nullable=True, default=1.0)

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="customer")
    display_override: Mapped[Optional["CustomerDisplayOverride"]] = relationship(
        "CustomerDisplayOverride", back_populates="customer", uselist=False, cascade="all, delete-orphan", lazy="selectin"
    )



class CustomerDisplayOverride(VersionedEntity):
    """Administrator manual display name override for B2B Customer."""

    __tablename__ = "customer_display_overrides"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    override_name: Mapped[str] = mapped_column(String(255), nullable=False)
    override_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    updated_by_name: Mapped[str] = mapped_column(String(100), nullable=False, default="ADMIN")

    customer: Mapped["Customer"] = relationship("Customer", back_populates="display_override")



class Material(VersionedEntity):
    """Raw material / aggregate item."""


    __tablename__ = "materials"

    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)


class Product(VersionedEntity):
    """Finished product mix or concrete grade."""

    __tablename__ = "products"

    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    grade: Mapped[str | None] = mapped_column(String(100), nullable=True)


class Vehicle(VersionedEntity):
    """Fleet mixer truck or transport vehicle."""

    __tablename__ = "vehicles"

    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    license_plate: Mapped[str] = mapped_column(String(50), nullable=False)
    capacity_m3: Mapped[float | None] = mapped_column(Float, nullable=True)
    vehicle_type: Mapped[str | None] = mapped_column(String(50), nullable=True, default="MIXER_TRUCK")
    fleet_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ownership: Mapped[str | None] = mapped_column(String(50), nullable=True, default="OWNED")


class Driver(VersionedEntity):
    """Fleet operator / mixer driver."""

    __tablename__ = "drivers"

    employee_id: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    license_number: Mapped[str | None] = mapped_column(String(100), nullable=True)


class Route(VersionedEntity):
    """Transit route template between plant and delivery site."""

    __tablename__ = "routes"

    code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    origin_plant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    destination_site_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sites.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)


class Order(VersionedEntity):
    """Customer supply order."""

    __tablename__ = "orders"

    order_number: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    total_volume_m3: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    customer: Mapped["Customer"] = relationship("Customer", back_populates="orders")
    tickets: Mapped[list["Ticket"]] = relationship("Ticket", back_populates="order")

    __table_args__ = (Index("idx_orders_customer_date", "customer_id", "order_date"),)


class Ticket(VersionedEntity):
    """Batch plant delivery ticket."""

    __tablename__ = "tickets"

    ticket_number: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    plant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ticket_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    delivered_volume_m3: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )

    order: Mapped["Order"] = relationship("Order", back_populates="tickets")
    dispatches: Mapped[list["Dispatch"]] = relationship(
        "Dispatch", back_populates="ticket"
    )

    __table_args__ = (Index("idx_tickets_plant_date", "plant_id", "ticket_date"),)


class Dispatch(VersionedEntity):
    """Mixer dispatch operation transaction."""

    __tablename__ = "dispatches"

    dispatch_number: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drivers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    plant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    dispatch_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    time_out: Mapped[str | None] = mapped_column(String(20), nullable=True)
    date_in: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    time_in: Mapped[str | None] = mapped_column(String(20), nullable=True)
    t1_transit_mins: Mapped[float | None] = mapped_column(Float, nullable=True)
    t2a_holding_mins: Mapped[float | None] = mapped_column(Float, nullable=True)
    t2b_unloading_mins: Mapped[float | None] = mapped_column(Float, nullable=True)
    unloading_duration_mins: Mapped[float | None] = mapped_column(Float, nullable=True)
    t2c_retention_mins: Mapped[float | None] = mapped_column(Float, nullable=True)
    t3_return_mins: Mapped[float | None] = mapped_column(Float, nullable=True)
    cycle_time: Mapped[str | None] = mapped_column(String(20), nullable=True)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="DISPATCHED", index=True
    )
    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    parser_version: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default="v3.1.0"
    )
    source_system: Mapped[str | None] = mapped_column(
        String(100), nullable=True, default="ERP_REGISTER"
    )
    excel_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    telemetry_matched: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    telemetry_match_score: Mapped[float | None] = mapped_column(Float, nullable=True, default=0.0)

    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="dispatches")

    __table_args__ = (
        Index("idx_dispatches_plant_date", "plant_id", "dispatch_date"),
        Index("idx_dispatches_customer_date", "customer_id", "dispatch_date"),
    )


class Invoice(VersionedEntity):
    """Billing invoice entity."""

    __tablename__ = "invoices"

    invoice_number: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    invoice_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    total_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    __table_args__ = (
        Index("idx_invoices_customer_date", "customer_id", "invoice_date"),
    )


class Trip(VersionedEntity):
    """Mixer transit trip record."""

    __tablename__ = "trips"

    trip_number: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    dispatch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("dispatches.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    departure_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    arrival_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    plant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("plants.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sites.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    plant_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    site_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    site_out: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    plant_in: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cycle_time: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gps_quality: Mapped[float | None] = mapped_column(Float, nullable=True, default=1.0)
    correlation_score: Mapped[float | None] = mapped_column(Float, nullable=True, default=0.0)

    __table_args__ = (
        Index("idx_trips_dispatch_dept", "dispatch_id", "departure_time"),
    )


# =============================================================================
# 2. INGESTION METADATA ENTITIES
# =============================================================================


class ImportJob(VersionedEntity):
    """ERP Excel Import Job Execution Tracker."""

    __tablename__ = "import_jobs"

    job_number: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="QUEUED", index=True
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    stages: Mapped[list["ImportStage"]] = relationship(
        "ImportStage", back_populates="import_job", cascade="all, delete-orphan"
    )
    errors: Mapped[list["ImportError"]] = relationship(
        "ImportError", back_populates="import_job", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_import_jobs_status_created", "status", "created_at"),)


class WorkbookMetadata(AuditEntity):
    """Excel Workbook Header & Structure Inspection."""

    __tablename__ = "workbook_metadata"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sheet_names: Mapped[list[Any]] = mapped_column(JSON, nullable=False)
    schema_version: Mapped[str] = mapped_column(
        String(50), nullable=False, default="v1.0"
    )


class ImportAuditLog(AuditEntity):
    """Security & Operational Audit Log for Import Activity."""

    __tablename__ = "import_audit_logs"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class ImportStatistic(AuditEntity):
    """Job Execution Metrics and Performance Telemetry."""

    __tablename__ = "import_statistics"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rows_per_sec: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    peak_memory_mb: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class ImportStage(BaseEntity):
    """7-Stage Import Pipeline Execution Progress."""

    __tablename__ = "import_stages"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    import_job: Mapped["ImportJob"] = relationship("ImportJob", back_populates="stages")


class ImportError(BaseEntity):
    """Row or Validation Error Record."""

    __tablename__ = "import_errors"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    import_job: Mapped["ImportJob"] = relationship("ImportJob", back_populates="errors")


class ImportWarning(BaseEntity):
    """Row Warning Record."""

    __tablename__ = "import_warnings"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    warning_code: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)


class ImportFile(BaseEntity):
    """Uploaded Raw Binary File Reference."""

    __tablename__ = "import_files"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)


class ImportCheckpoint(BaseEntity):
    """Streaming Resumable Checkpoint."""

    __tablename__ = "import_checkpoints"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    last_processed_row: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checkpoint_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class ImportPerformanceMetrics(BaseEntity):
    """Real-time Ingestion Worker Performance Metrics."""

    __tablename__ = "import_performance_metrics"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cpu_usage_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    memory_usage_mb: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    io_write_mb: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class ImportEvent(BaseEntity):
    """Domain Event Dispatch Log for Ingestion Activity."""

    __tablename__ = "import_events"

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("import_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_name: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    dispatched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
