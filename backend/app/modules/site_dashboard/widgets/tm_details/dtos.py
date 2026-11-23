"""
TM Details DTO Specifications
Workstream 2.6 Backend DTOs
"""

from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict


class TMDetailRowDTO(BaseModel):
    dispatch_id: str
    tm_no: str
    vehicle_plate: str
    plant_name: str
    customer_name: str
    dispatch_time: str
    site_in_time: str
    unload_start_time: str
    unload_end_time: str
    site_out_time: str
    holding_mins: float
    unloading_mins: float
    retention_mins: float
    total_site_mins: float
    dispatch_accuracy_pct: float
    operational_status: str
    sla_status: Literal["OPTIMAL", "WARNING", "CRITICAL", "DELAYED"]
    delay_classification: str

    model_config = ConfigDict(frozen=True)


class TMDetailsResponseDTO(BaseModel):
    total_count: int
    page: int
    page_size: int
    items: list[TMDetailRowDTO]

    model_config = ConfigDict(frozen=True)
