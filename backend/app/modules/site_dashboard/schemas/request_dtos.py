"""
Dashboard Filter Metadata DTOs
Workstream 2.2 Correction DTOs
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict


class FilterOptionDTO(BaseModel):
    id: str
    name: str
    code: Optional[str] = None
    raw_customer_name: Optional[str] = None
    effective_customer_name: Optional[str] = None

    model_config = ConfigDict(frozen=True)


class ActiveDatasetInfoDTO(BaseModel):
    operational_date: str
    dataset_id: str
    import_timestamp: str
    calculation_timestamp: str
    total_dispatches: int
    total_trips: int
    dataset_status: str

    model_config = ConfigDict(frozen=True)


class DashboardFilterMetadataResponseDTO(BaseModel):
    plants: list[FilterOptionDTO] = []
    customers: list[FilterOptionDTO] = []
    dataset_info: ActiveDatasetInfoDTO

    model_config = ConfigDict(frozen=True)


class DashboardFilterParams(BaseModel):
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    plant_id: Optional[str] = None
    customer_id: Optional[str] = None
    dataset_type: str = "ALL"
    operation_date: Optional[str] = None
    dataset_id: Optional[str] = None
    search: Optional[str] = None
