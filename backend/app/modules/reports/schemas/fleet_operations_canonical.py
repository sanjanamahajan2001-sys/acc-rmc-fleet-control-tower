from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict
from app.modules.reports.schemas.report_schemas import ReportStatus


class ReportMetadataDTO(BaseModel):
    execution_id: str
    report_id: str = "fleet_operations"
    report_name: str = "Fleet Operations Report"
    generated_at: str = ""
    requested_by: str = "SYSTEM"


class FleetOperationsKPIs(BaseModel):
    total_active_vehicles: int = 0
    vehicles_with_dispatches: int = 0
    idle_vehicles: int = 0
    fleet_utilization_pct: float = 0.0
    avg_dispatches_per_vehicle: float = 0.0
    avg_cycle_time_mins: float = 0.0

    model_config = ConfigDict(frozen=False)


class VehicleProductivityRecord(BaseModel):
    vehicle_plate: str
    dispatch_count: int
    total_volume_m3: float
    avg_holding_mins: float
    avg_unloading_mins: float
    avg_retention_mins: float
    utilization_pct: float
    status: str


class VehicleAlertRecord(BaseModel):
    vehicle_plate: str
    alert_type: str
    severity: str
    message: str


class CanonicalFleetOperationsReport(BaseModel):
    schema_version: str = "1.0"
    metadata: ReportMetadataDTO
    requested_scope: Dict[str, Any]
    effective_scope: Dict[str, Any]
    scope_fingerprint: str
    status: ReportStatus
    record_count: int
    kpis: FleetOperationsKPIs
    records: List[VehicleProductivityRecord] = []
    alerts: List[VehicleAlertRecord] = []
    exceptions: List[Dict[str, Any]] = []

    model_config = ConfigDict(frozen=False)
