from enum import Enum
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from app.modules.operational_dashboard.context.dtos import OperationalContextEnvelopeDTO


class KPIStatusEnum(str, Enum):
    OPTIMAL = "OPTIMAL"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    NEUTRAL = "NEUTRAL"


class AvailabilityEnum(str, Enum):
    AVAILABLE = "AVAILABLE"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    BASELINE_UNAVAILABLE = "BASELINE_UNAVAILABLE"
    NO_OBSERVATIONS = "NO_OBSERVATIONS"


class KPICardItemDTO(BaseModel):
    key: str = Field(..., description="Unique KPI identifier")
    label: str = Field(..., description="Human-readable KPI title")
    current_value: Optional[float] = Field(default=None, description="Calculated metric value or None if unavailable")
    unit: str = Field(..., description="Display unit (e.g. %, /100, Trips)")
    target: Optional[float] = Field(default=None, description="Target SLA benchmark")
    variance: Optional[float] = Field(default=None, description="Variance relative to target")
    status: KPIStatusEnum = Field(default=KPIStatusEnum.NEUTRAL, description="Performance status classification")
    availability: AvailabilityEnum = Field(default=AvailabilityEnum.AVAILABLE, description="Data contract availability status")
    total_volume_m3: Optional[float] = Field(default=None, description="Delivered concrete volume or None if unavailable")


class KPIRibbonContainerDTO(BaseModel):
    dispatch_accuracy: KPICardItemDTO
    swi: KPICardItemDTO
    dpi: KPICardItemDTO
    fui: KPICardItemDTO
    total_dispatches: KPICardItemDTO


class KPIRibbonResponseDTO(BaseModel):
    context: OperationalContextEnvelopeDTO
    kpis: KPIRibbonContainerDTO
