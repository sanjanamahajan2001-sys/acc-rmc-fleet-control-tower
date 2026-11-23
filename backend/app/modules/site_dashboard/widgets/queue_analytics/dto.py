"""
Queue Analytics DTO Specifications
Workstream 2.5 Backend DTOs
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.modules.site_dashboard.dto.canonical_dtos import DashboardQueueDTO, CauseItemDTO, QueuePointDTO


class QueueAnalyticsResponseDTO(BaseModel):
    queue: DashboardQueueDTO
    root_causes: list[CauseItemDTO]

    model_config = ConfigDict(frozen=True)
