"""
WS-09 Section 06 Cost & Exposure Intelligence Schema DTOs
Defines Pydantic data transfer objects for realized cost exposure, paginated high-cost operations,
plant & customer cost risk, model prediction provenance, and operational status separation.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class CostExposureSummaryDTO(BaseModel):
    """Realized operational financial exposure summary metrics (Phase 4 Authority)."""

    realized_cost_exposure_inr: float = Field(
        ..., description="Realized operational financial exposure in INR"
    )
    predicted_cost_exposure_inr: Optional[float] = Field(
        None, description="Predicted cost exposure from ML engine (None if NOT_CONFIGURED)"
    )
    holding_penalty_cost_inr: float = Field(
        ..., description="Plant holding queue financial loss in INR"
    )
    retention_sla_penalty_inr: float = Field(
        ..., description="Site retention SLA penalty in INR"
    )
    idle_fuel_waste_inr: float = Field(
        ..., description="Idle fuel waste in INR"
    )
    high_cost_operations_count: int = Field(
        ..., description="Count of dispatches with excess holding or retention penalties"
    )


class HighCostOperationItemDTO(BaseModel):
    """High-cost dispatch operation item."""

    dispatch_id: str = Field(..., description="Unique dispatch identifier")
    dispatch_code: str = Field(..., description="Human readable dispatch reference code")
    plant_code: str = Field(..., description="Origin plant code")
    customer_code: str = Field(..., description="Destination customer code")
    vehicle_code: str = Field(..., description="Assigned transport vehicle code")
    holding_penalty_mins: float = Field(..., description="Excess holding minutes above SLA baseline (20m)")
    retention_penalty_mins: float = Field(..., description="Excess retention minutes above SLA baseline (10m)")
    total_exposure_inr: float = Field(..., description="Total realized financial exposure for dispatch in INR")
    risk_level: str = Field(..., description="Risk level classification: Critical, High, or Moderate")


class PaginatedHighCostOperationsDTO(BaseModel):
    """Server-side paginated container for high-cost operations."""

    items: List[HighCostOperationItemDTO] = Field(..., description="List of high-cost operation items")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., description="Number of items per page")
    total_items: int = Field(..., description="Total matching high-cost operations count")
    total_pages: int = Field(..., description="Total pages available")


class PlantCostRiskItemDTO(BaseModel):
    """Plant operational cost risk concentration item."""

    plant_code: str = Field(..., description="Plant code")
    plant_name: str = Field(..., description="Plant display name")
    dispatches_count: int = Field(..., description="Total dispatches under current filter context")
    total_exposure_inr: float = Field(..., description="Total plant realized financial exposure in INR")
    exposure_percentage: float = Field(..., description="Percentage share of total filtered exposure (0.0 - 100.0)")


class CustomerCostRiskItemDTO(BaseModel):
    """Customer operational cost risk concentration item."""

    customer_code: str = Field(..., description="Customer code")
    customer_name: str = Field(..., description="Customer display name")
    delivered_trips: int = Field(..., description="Total delivered trips under current filter context")
    total_exposure_inr: float = Field(..., description="Total customer realized financial exposure in INR")
    exposure_percentage: float = Field(..., description="Percentage share of total filtered exposure (0.0 - 100.0)")


class PredictionProvenanceDTO(BaseModel):
    """Model prediction engine provenance and status metadata."""

    is_model_configured: bool = Field(
        False, description="Flag indicating whether Phase 5.4 ML model is configured"
    )
    prediction_status: str = Field(
        "NOT_CONFIGURED", description="Prediction status: AVAILABLE, NOT_CONFIGURED, or ERROR"
    )
    model_name: Optional[str] = Field(
        None, description="Trained model identifier if AVAILABLE"
    )
    model_version: Optional[str] = Field(
        None, description="Trained model version if AVAILABLE"
    )
    prediction_snapshot_id: Optional[str] = Field(
        None, description="Prediction snapshot identifier if AVAILABLE"
    )
    prediction_timestamp: Optional[str] = Field(
        None, description="Timestamp when prediction was generated"
    )
    confidence_score: Optional[float] = Field(
        None, description="Model prediction confidence score if AVAILABLE"
    )
    notes: str = Field(
        "Phase 5.4 ML Prediction Engine is not configured in current repository environment.",
        description="Explanatory notes regarding prediction provenance and status"
    )


class OperationalCostExposureResponseDTO(BaseModel):
    """Top-level response DTO for WS-09 Section 06 Cost & Exposure Intelligence."""

    summary: CostExposureSummaryDTO
    high_cost_operations: PaginatedHighCostOperationsDTO
    plant_cost_risk: List[PlantCostRiskItemDTO]
    customer_cost_risk: List[CustomerCostRiskItemDTO]
    provenance: PredictionProvenanceDTO
    calculation_status: str = Field(
        ..., description="Operational calculation status: SUCCESS, NO_RECORDS, or ERROR"
    )
    prediction_status: str = Field(
        ..., description="Prediction engine status: AVAILABLE, NOT_CONFIGURED, or ERROR"
    )
    calculation_notes: str = Field(
        ..., description="Authoritative calculation notes and data lineage summary"
    )
