from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict

class FilterOptionDTO(BaseModel):
    id: str
    name: str
    code: Optional[str] = None
    model_config = ConfigDict(frozen=True)

class OperationalContextEnvelopeDTO(BaseModel):
    dataset_id: str
    snapshot_version: str
    operational_date: str
    plant_id: str
    customer_id: str
    dataset_type: str
    generated_at: str
    model_config = ConfigDict(frozen=True)

class ShellContextResponseDTO(BaseModel):
    context: OperationalContextEnvelopeDTO
    metadata: Dict[str, Any]
    available_plants: List[FilterOptionDTO]
    available_customers: List[FilterOptionDTO]
    model_config = ConfigDict(frozen=True)
