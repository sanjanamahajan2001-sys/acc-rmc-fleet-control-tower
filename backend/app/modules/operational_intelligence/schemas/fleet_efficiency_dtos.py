"""
WS-09 Section 05 Fleet & Plant Operational Efficiency DTO Schemas
Defines structured response DTOs for Section 05 Fleet & Plant Operational Efficiency canvas.
"""

from typing import List
from pydantic import BaseModel, Field


class FleetEfficiencySummaryCountsDTO(BaseModel):
    overall_efficiency_index: float = Field(..., description="Overall composite fleet operational efficiency index (0-100)")
    fleet_utilization_pct: float = Field(..., description="Active mixer truck utilization percentage")
    avg_turnaround_time_mins: float = Field(..., description="Average complete trip turnaround time in minutes")
    avg_holding_time_mins: float = Field(..., description="Average plant queue holding time in minutes")
    avg_retention_time_mins: float = Field(..., description="Average customer site retention time in minutes")
    turnaround_efficiency_pct: float = Field(..., description="Plant turnaround efficiency rating (0-100)")
    site_unloading_efficiency_pct: float = Field(..., description="Site unloading efficiency rating (0-100)")


class PlantEfficiencyItemDTO(BaseModel):
    plant_code: str = Field(..., description="Plant identifier code")
    plant_name: str = Field(..., description="Plant display name")
    active_vehicles: int = Field(..., description="Number of active mixer trucks assigned")
    total_dispatches: int = Field(..., description="Total completed dispatches")
    avg_holding_mins: float = Field(..., description="Average plant holding time in minutes")
    turnaround_efficiency_pct: float = Field(..., description="Plant turnaround efficiency rating (0-100)")
    efficiency_grade: str = Field(..., description="Good | Needs Improvement | Critical")


class CustomerEfficiencyItemDTO(BaseModel):
    customer_code: str = Field(..., description="Customer identifier code")
    customer_name: str = Field(..., description="Customer display name")
    total_trips: int = Field(..., description="Total delivered trips")
    avg_retention_mins: float = Field(..., description="Average site retention time in minutes")
    cei_score: float = Field(..., description="Customer Efficiency Index score (0-100)")
    efficiency_grade: str = Field(..., description="Good | Needs Improvement | Critical")


class OperationalFleetEfficiencyResponseDTO(BaseModel):
    summary: FleetEfficiencySummaryCountsDTO
    plant_efficiency: List[PlantEfficiencyItemDTO]
    customer_efficiency: List[CustomerEfficiencyItemDTO]
    calculation_status: str = Field(default="SUCCESS", description="SUCCESS | NO_RECORDS | NOT_CONFIGURED | ERROR")
    calculation_notes: str = Field(..., description="Authoritative lineage and active filter context statement")
