"""
WS-06.4 Dispatch Optimization Solver Policy & Configurable Constraints.
Defines versioned solver configuration policies for candidate operational constraints
(departure spacing, plant holding queue capacity, customer retention limit, return continuity)
and objective function weighting policies.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class SolverConstraintPolicyDTO(BaseModel):
    """Configurable candidate constraint parameters for optimization solver."""
    min_departure_gap_mins: float = Field(
        default=12.0,
        description="PROPOSED CANDIDATE RULE: Minimum departure spacing gap between consecutive plant trips (mins)."
    )
    max_plant_queue_capacity: int = Field(
        default=3,
        description="PROPOSED CANDIDATE RULE: Maximum simulteneous trucks in plant holding queue per batching line."
    )
    max_customer_retention_mins: float = Field(
        default=10.0,
        description="PROPOSED CANDIDATE RULE: Maximum customer site retention duration before SLA penalty applies (mins)."
    )
    enforce_vehicle_return_continuity: bool = Field(
        default=True,
        description="AUTHENTICATED RULE: Vehicle cannot depart for Trip N+1 until Return(N) <= Departure(N+1)."
    )


class SolverObjectivePolicyDTO(BaseModel):
    """Configurable weights policy for candidate objective functions."""
    balanced_sla_weight: float = Field(default=0.50, description="Weight for SLA compliance in BALANCED_OPERATIONS")
    balanced_delay_weight: float = Field(default=0.35, description="Weight for delay reduction in BALANCED_OPERATIONS")
    balanced_das_weight: float = Field(default=0.15, description="Weight for DAS score in BALANCED_OPERATIONS")


class SolverConfigurationDTO(BaseModel):
    """Versioned solver configuration payload."""
    policy_version: str = Field(default="v1.0.0-PROPOSED", description="Solver policy specification version")
    constraints: SolverConstraintPolicyDTO = Field(default_factory=SolverConstraintPolicyDTO)
    objective_policy: SolverObjectivePolicyDTO = Field(default_factory=SolverObjectivePolicyDTO)
