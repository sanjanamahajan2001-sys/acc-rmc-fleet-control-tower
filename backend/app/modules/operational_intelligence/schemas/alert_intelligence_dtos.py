"""
WS-09 Section 02 Operational Alert Intelligence DTO Schemas
Defines structured response DTOs for Section 02 Alert Intelligence canvas.
"""

from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field


class AlertSummaryCountsDTO(BaseModel):
    total_active: int = Field(..., description="Count of alerts with status IN ('OPEN', 'ACKNOWLEDGED')")
    open_count: int = Field(..., description="Count of alerts with status = 'OPEN'")
    acknowledged_count: int = Field(..., description="Count of alerts with status = 'ACKNOWLEDGED'")
    critical_count: int = Field(..., description="Count of active alerts with severity = 'CRITICAL'")
    warning_count: int = Field(..., description="Count of active alerts with severity = 'WARNING'")
    info_count: int = Field(..., description="Count of active alerts with severity = 'INFO'")


class AlertSeverityDistributionItemDTO(BaseModel):
    severity: str = Field(..., description="CRITICAL | WARNING | INFO")
    count: int = Field(..., description="Number of active alerts")
    percentage: float = Field(..., description="Percentage of active alerts")


class AlertCategoryDistributionItemDTO(BaseModel):
    alert_type: str = Field(..., description="Unique alert rule key e.g. PLANT_HOLDING_BOTTLENECK")
    label: str = Field(..., description="Human readable alert type label")
    severity: str = Field(..., description="Primary severity level")
    count: int = Field(..., description="Count of active alerts in this category")
    percentage: float = Field(..., description="Percentage relative to total active alerts")


class AlertConcentrationItemDTO(BaseModel):
    group_type: str = Field(..., description="PLANT | CUSTOMER")
    group_code: str = Field(..., description="Plant code or Customer code")
    group_name: str = Field(..., description="Plant name or Customer name")
    critical_count: int = Field(..., description="Critical alert count")
    warning_count: int = Field(..., description="Warning alert count")
    total_count: int = Field(..., description="Total active alerts count for group")


class PriorityAlertItemDTO(BaseModel):
    id: str = Field(..., description="Alert UUID string")
    alert_type: str = Field(..., description="Alert rule type key")
    severity: str = Field(..., description="CRITICAL | WARNING | INFO")
    status: str = Field(..., description="OPEN | ACKNOWLEDGED")
    plant_id: str = Field(..., description="Plant code")
    customer_id: str = Field(..., description="Customer code")
    metric_name: Optional[str] = Field(default=None, description="Associated metric e.g. t2a_holding_mins")
    actual_value: Optional[float] = Field(default=None, description="Observed actual metric value")
    threshold_value: Optional[float] = Field(default=None, description="Rule threshold value")
    unit: Optional[str] = Field(default=None, description="Metric unit e.g. mins")
    business_impact: Optional[str] = Field(default=None, description="Calculated business impact note")
    detected_at: str = Field(..., description="ISO 8601 detection timestamp")


class OperationalAlertIntelligenceResponseDTO(BaseModel):
    summary: AlertSummaryCountsDTO
    severity_distribution: List[AlertSeverityDistributionItemDTO]
    top_categories: List[AlertCategoryDistributionItemDTO]
    plant_concentration: List[AlertConcentrationItemDTO]
    customer_concentration: List[AlertConcentrationItemDTO]
    priority_alerts: List[PriorityAlertItemDTO]
    calculation_status: str = Field(default="SUCCESS", description="SUCCESS | NO_RECORDS | NOT_CONFIGURED | ERROR")
    calculation_notes: str = Field(..., description="PostgreSQL provenance and lineage note")
