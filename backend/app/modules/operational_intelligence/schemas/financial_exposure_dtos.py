"""
WS-09 Section 04 Financial Loss & SLA Risk Exposure DTO Schemas
Defines structured response DTOs for Section 04 Financial Exposure canvas.
"""

from typing import List
from pydantic import BaseModel, Field


class FinancialSummaryCountsDTO(BaseModel):
    total_financial_exposure_inr: float = Field(..., description="Total quantified financial exposure in INR")
    holding_delay_cost_inr: float = Field(..., description="Plant holding queue financial loss in INR")
    retention_sla_penalty_inr: float = Field(..., description="Customer site retention SLA penalty exposure in INR")
    idle_fuel_waste_inr: float = Field(..., description="Idle fuel waste exposure in INR")
    total_penalty_mins: float = Field(..., description="Sum of holding and retention penalty minutes")


class FinancialBreakdownItemDTO(BaseModel):
    category: str = Field(..., description="PLANT_HOLDING | CUSTOMER_RETENTION | IDLE_FUEL")
    label: str = Field(..., description="Human readable category label")
    penalty_mins: float = Field(..., description="Associated penalty minutes")
    cost_rate_per_min: float = Field(..., description="Configured cost rate per minute in INR")
    total_cost_inr: float = Field(..., description="Calculated total cost in INR")
    percentage: float = Field(..., description="Percentage relative to total exposure")


class EntityFinancialRiskItemDTO(BaseModel):
    entity_type: str = Field(..., description="PLANT | CUSTOMER")
    entity_code: str = Field(..., description="Plant or Customer code")
    entity_name: str = Field(..., description="Plant or Customer name")
    penalty_mins: float = Field(..., description="Total penalty minutes")
    financial_exposure_inr: float = Field(..., description="Total financial exposure in INR")


class OperationalFinancialExposureResponseDTO(BaseModel):
    summary: FinancialSummaryCountsDTO
    breakdown: List[FinancialBreakdownItemDTO]
    top_plant_risk: List[EntityFinancialRiskItemDTO]
    top_customer_risk: List[EntityFinancialRiskItemDTO]
    calculation_status: str = Field(default="SUCCESS", description="SUCCESS | NO_RECORDS | NOT_CONFIGURED | ERROR")
    calculation_notes: str = Field(..., description="Authoritative lineage and active filter context statement")
