"""
Operational Intelligence Health DTOs
Phase 1 Operational Health & Executive Index Schema
"""

from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class HealthMetricDTO(BaseModel):
    key: str
    label: str
    current_value: float
    unit: str
    status: str  # 'OPTIMAL' | 'WARNING' | 'CRITICAL'
    target: Optional[float] = None
    threshold: Optional[float] = None
    variance: Optional[float] = None
    provenance_table: str
    provenance_formula: str

    model_config = ConfigDict(frozen=True)


class DatasetFreshnessDTO(BaseModel):
    dataset_id: str
    operational_date: str
    import_timestamp: str
    dataset_status: str
    total_dispatches: int
    total_trips: int

    model_config = ConfigDict(frozen=True)


class OperationalHealthResponseDTO(BaseModel):
    overall_health_score: Optional[float] = None  # None if unavailable/not-configured
    health_status: str  # 'HEALTHY' | 'DEGRADED' | 'CRITICAL' | 'UNAVAILABLE'
    freshness: DatasetFreshnessDTO
    metrics: List[HealthMetricDTO]
    calculation_status: str  # 'SUCCESS' | 'NO_RECORDS' | 'NOT_CONFIGURED' | 'ERROR'
    calculation_notes: str

    model_config = ConfigDict(frozen=True)
