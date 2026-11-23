"""
Diesel Economics Calculation Engine
Workstream 2.11 Fuel Loss & Overhead Economics Math
"""

from pydantic import BaseModel, ConfigDict


class DieselEconomicsDTO(BaseModel):
    """Canonical DTO representing fuel loss and monetary overhead economics."""

    holding_cost_inr: float = 0.0
    unloading_cost_inr: float = 0.0
    retention_cost_inr: float = 0.0
    total_cost_inr: float = 0.0
    holding_liters: float = 0.0
    unloading_liters: float = 0.0
    retention_liters: float = 0.0
    total_liters: float = 0.0
    diesel_price_per_liter: float = 95.94
    idle_burn_rate_l_per_min: float = 0.05  # 3.0 L/hr

    model_config = ConfigDict(frozen=True)


class DieselEconomicsService:
    """Decoupled Diesel Fuel Economics Calculation Engine."""

    DEFAULT_DIESEL_PRICE_PER_LITER: float = 95.94
    DEFAULT_IDLE_BURN_RATE_L_PER_MIN: float = 0.05  # 3.0 L/hr (0.05 L/min)

    @classmethod
    def calculate_diesel_economics(
        cls,
        total_excess_holding_mins: float,
        total_excess_unloading_mins: float,
        total_excess_retention_mins: float = 0.0,
        diesel_price: float | None = None,
        idle_burn_rate: float | None = None,
    ) -> DieselEconomicsDTO:
        """
        Computes diesel volume loss (L) and monetary overhead (INR ₹)
        based on exact client operational formulas:
          - Holding Liters = Excess Holding Mins * Burn Rate (0.05 L/min)
          - Holding INR = Holding Liters * Diesel Rate (95.94 ₹/L)
          - Unloading Liters = Excess Unloading Mins * Burn Rate (0.05 L/min)
          - Unloading INR = Unloading Liters * Diesel Rate (95.94 ₹/L)
          - Retention Liters = Excess Retention Mins * Burn Rate (0.05 L/min)
          - Retention INR = Retention Liters * Diesel Rate (95.94 ₹/L)
        """
        price = diesel_price if diesel_price is not None else cls.DEFAULT_DIESEL_PRICE_PER_LITER
        burn_rate = idle_burn_rate if idle_burn_rate is not None else cls.DEFAULT_IDLE_BURN_RATE_L_PER_MIN

        safe_excess_holding_mins = max(0.0, float(total_excess_holding_mins))
        safe_excess_unloading_mins = max(0.0, float(total_excess_unloading_mins))
        safe_excess_retention_mins = max(0.0, float(total_excess_retention_mins))

        holding_liters = safe_excess_holding_mins * burn_rate
        unloading_liters = safe_excess_unloading_mins * burn_rate
        retention_liters = safe_excess_retention_mins * burn_rate
        total_liters = holding_liters + unloading_liters + retention_liters

        holding_cost_inr = holding_liters * price
        unloading_cost_inr = unloading_liters * price
        retention_cost_inr = retention_liters * price
        total_cost_inr = holding_cost_inr + unloading_cost_inr + retention_cost_inr

        return DieselEconomicsDTO(
            holding_cost_inr=round(holding_cost_inr, 2),
            unloading_cost_inr=round(unloading_cost_inr, 2),
            retention_cost_inr=round(retention_cost_inr, 2),
            total_cost_inr=round(total_cost_inr, 2),
            holding_liters=round(holding_liters, 2),
            unloading_liters=round(unloading_liters, 2),
            retention_liters=round(retention_liters, 2),
            total_liters=round(total_liters, 2),
            diesel_price_per_liter=price,
            idle_burn_rate_l_per_min=burn_rate,
        )
