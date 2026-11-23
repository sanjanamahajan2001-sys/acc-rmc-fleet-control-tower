"""
Fleet Utilization DTO Specifications
Workstream 2.8 Backend DTOs
"""

from typing import Literal
from pydantic import BaseModel, ConfigDict


class FleetSummaryDTO(BaseModel):
    total_active_vehicles: int
    vehicles_with_dispatches: int
    idle_vehicles: int
    fleet_utilization_pct: float
    avg_dispatches_per_vehicle: float
    avg_cycle_time_mins: float

    model_config = ConfigDict(frozen=True)


class VehicleProductivityItemDTO(BaseModel):
    vehicle_plate: str
    dispatch_count: int
    total_volume_m3: float
    avg_holding_mins: float
    avg_unloading_mins: float
    avg_retention_mins: float
    utilization_pct: float
    status: str

    model_config = ConfigDict(frozen=True)


class VehicleAlertDTO(BaseModel):
    vehicle_plate: str
    alert_type: str
    severity: Literal["HIGH", "MEDIUM", "LOW"]
    message: str

    model_config = ConfigDict(frozen=True)


class FleetUtilizationResponseDTO(BaseModel):
    summary: FleetSummaryDTO
    top_vehicles: list[VehicleProductivityItemDTO]
    alerts: list[VehicleAlertDTO]

    model_config = ConfigDict(frozen=True)
