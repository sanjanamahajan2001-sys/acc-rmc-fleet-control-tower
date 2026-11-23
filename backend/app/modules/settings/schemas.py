"""
Platform Configuration DTO Schemas
Workstream X.3 Production Schemas
"""

import datetime
import uuid
from typing import Any, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class ConfigurationCategoryDTO(BaseModel):
    id: Union[uuid.UUID, str]
    category_name: str
    display_name: str
    icon: str
    display_order: int
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PlatformConfigurationDTO(BaseModel):
    id: Union[uuid.UUID, str]
    domain: str
    category: str
    sub_category: Optional[str] = None
    key: str
    value: Any
    value_type: str
    unit: Optional[str] = None
    default_value: Optional[Any] = None
    editable: bool
    is_secret: bool
    requires_restart: bool
    validation_type: str
    validation_rules: Optional[dict[str, Any]] = None
    display_order: int
    description: Optional[str] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class UpdateConfigurationRequest(BaseModel):
    value: Any
    change_reason: Optional[str] = "Operational Setting Update"


class ConfigurationHistoryDTO(BaseModel):
    id: Union[uuid.UUID, str]
    configuration_id: Union[uuid.UUID, str]
    previous_value: Optional[Any] = None
    new_value: Any
    changed_by: str
    change_reason: Optional[str] = None
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class PlantContextDTO(BaseModel):
    """Read-only plant context associated with a B2B customer."""
    plant_id: uuid.UUID
    plant_code: str
    plant_name: str

    model_config = ConfigDict(from_attributes=True)


class CustomerSettingsDTO(BaseModel):
    """Customer display settings representation."""
    customer_id: uuid.UUID
    customer_code: str
    raw_customer_name: str
    effective_customer_name: str
    is_overridden: bool
    override_reason: Optional[str] = None
    updated_by_name: Optional[str] = None
    plants: list[PlantContextDTO] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class UpdateCustomerOverrideRequest(BaseModel):
    """Payload for creating or updating a customer display override."""
    override_name: str = Field(..., min_length=1, max_length=255, description="Non-empty display name")
    override_reason: Optional[str] = Field(default=None, max_length=500, description="Optional audit reason")


class CustomerOverrideMutationResponse(BaseModel):
    """Response payload for customer override creation/update/reset."""
    customer_id: uuid.UUID
    customer_code: str
    raw_customer_name: str
    effective_customer_name: str
    is_overridden: bool
    message: str

    model_config = ConfigDict(from_attributes=True)

