"""
Pydantic Schemas for WS1.1 Canonical & Ingestion DTOs
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PlantSchema(BaseModel):
    id: UUID
    code: str
    name: str
    location: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CustomerSchema(BaseModel):
    id: UUID
    code: str
    name: str
    tax_id: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DispatchSchema(BaseModel):
    id: UUID
    dispatch_number: str
    ticket_id: UUID
    vehicle_id: UUID
    driver_id: UUID
    plant_id: UUID
    customer_id: UUID
    dispatch_date: datetime
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ImportJobSchema(BaseModel):
    id: UUID
    job_number: str
    status: str
    file_name: str
    file_hash: str
    total_rows: int
    processed_rows: int
    error_count: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
