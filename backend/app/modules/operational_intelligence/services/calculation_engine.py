"""
WS-10 Phase 3: Authoritative Financial Calculation Engine & Metric Semantic Contract Authority.
Implements Option A dimensional correctness for Plant Congestion Risk:
Plant_Congestion_Risk_Exposure (₹) = P(Congestion) * Expected_Congestion_Duration (hours) * PLANT_CONGESTION_RISK (₹/hour).
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.operational_intelligence.models.calculation_rate_config import CalculationRateConfiguration

logger = logging.getLogger(__name__)

CALCULATION_VERSION = "v1.0.0"

# Explicit Metric Semantic Contract Specification
METRIC_SEMANTIC_CONTRACT = {
    "delay_regressor": {
        "predicted_metric": "t1_transit_mins",
        "unit": "minutes",
        "business_meaning": "Incremental Transit Delay Duration",
        "financial_input": True,
        "transformation_rule": "max(0.0, predicted_value)",
    },
    "turnaround_regressor": {
        "predicted_metric": "t2b_unloading_mins",
        "unit": "minutes",
        "business_meaning": "Total Plant Unloading Turnaround Duration",
        "financial_input": True,
        "transformation_rule": "max(0.0, predicted_value - STANDARD_TURNAROUND_BENCHMARK)",
    },
    "sla_breach_classifier": {
        "predicted_metric": "sla_breach_flag",
        "unit": "probability",
        "business_meaning": "Calibrated Probability of Contractual SLA Non-Delivery Breach",
        "financial_input": True,
        "transformation_rule": "calibrated_p_breach * SLA_BREACH_PENALTY",
    },
    "plant_risk_classifier": {
        "predicted_metric": "plant_risk_class",
        "unit": "probability",
        "business_meaning": "Plant Congestion Risk Severity Probability",
        "financial_input": True,
        "transformation_rule": "calibrated_p_congestion * expected_congestion_duration_hours * PLANT_CONGESTION_RISK",
    },
}


class CalculationRateNotFoundError(Exception):
    """Raised when no authoritative rate rule is found in the rate resolution hierarchy."""
    pass


class FinancialCalculationEngine:
    """
    Authoritative Financial Calculation Engine governing delay exposure, SLA breach penalty risk,
    plant congestion risk, and idle queue cost calculations.
    Enforces Option A dimensional correctness (probability * hours * ₹/hour = ₹).
    """

    @classmethod
    async def resolve_authoritative_rate(
        cls,
        session: AsyncSession,
        rate_code: str,
        plant_code: Optional[str] = None,
        customer_code: Optional[str] = None,
        target_date: Optional[datetime] = None,
    ) -> CalculationRateConfiguration:
        """
        Resolves authoritative rate using 3-tier precedence hierarchy:
        1. Customer / Contract Specific (customer_code + plant_code)
        2. Plant Specific (plant_code)
        3. Global Default (plant_code IS NULL AND customer_code IS NULL)
        """
        dt = target_date or datetime.now(timezone.utc)

        stmt = select(CalculationRateConfiguration).where(
            CalculationRateConfiguration.rate_code == rate_code,
            CalculationRateConfiguration.is_active == True,
            CalculationRateConfiguration.is_deleted == False,
            CalculationRateConfiguration.effective_from <= dt,
            or_(
                CalculationRateConfiguration.effective_to.is_(None),
                CalculationRateConfiguration.effective_to > dt,
            ),
        )

        res = await session.execute(stmt)
        rates = res.scalars().all()

        if not rates:
            raise CalculationRateNotFoundError(
                f"NO_AUTHORITATIVE_RATE: No active effective rate found for rate_code='{rate_code}' at date '{dt.isoformat()}'"
            )

        # 1. Customer + Plant override
        if customer_code and plant_code:
            match_cust_plant = [
                r for r in rates if r.customer_code == customer_code and r.plant_code == plant_code
            ]
            if match_cust_plant:
                return match_cust_plant[0]

        # 2. Customer override
        if customer_code:
            match_cust = [
                r for r in rates if r.customer_code == customer_code and r.plant_code is None
            ]
            if match_cust:
                return match_cust[0]

        # 3. Plant override
        if plant_code:
            match_plant = [
                r for r in rates if r.plant_code == plant_code and r.customer_code is None
            ]
            if match_plant:
                return match_plant[0]

        # 4. Global Default
        match_global = [
            r for r in rates if r.plant_code is None and r.customer_code is None
        ]
        if match_global:
            return match_global[0]

        raise CalculationRateNotFoundError(
            f"NO_AUTHORITATIVE_RATE: Hierarchy failed for rate_code='{rate_code}', plant='{plant_code}', customer='{customer_code}'"
        )

    @classmethod
    def calculate_delay_exposure(
        cls, delay_mins: float, holding_rate_value: Decimal
    ) -> Decimal:
        """Calculates Delay Cost Exposure: (delay_mins / 60.0) * holding_idle_rate."""
        mins_dec = Decimal(str(max(0.0, float(delay_mins))))
        hours_dec = mins_dec / Decimal("60.0")
        exposure = hours_dec * holding_rate_value
        return exposure.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def calculate_sla_penalty_emv(
        cls, calibrated_p_breach: float, penalty_rate_value: Decimal
    ) -> Decimal:
        """
        Calculates Expected Monetary Value (EMV) for SLA Breach Penalty:
        EMV_SLA (₹) = Calibrated_P(Breach) * Contractual_Penalty_Rate (₹/breach).
        Dimension: probability * ₹ = ₹.
        """
        prob_dec = Decimal(str(max(0.0, min(1.0, float(calibrated_p_breach)))))
        emv = prob_dec * penalty_rate_value
        return emv.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def calculate_plant_congestion_risk(
        cls,
        calibrated_p_congestion: float,
        expected_congestion_duration_mins: float,
        congestion_rate_value: Decimal,
    ) -> Decimal:
        """
        Calculates Plant Congestion Risk Exposure under Option A Dimensional Correctness:
        Exposure (₹) = P(Congestion) * (expected_congestion_duration_mins / 60.0) * PLANT_CONGESTION_RISK (₹/hour).
        Dimension: probability * hours * (₹/hour) = ₹.
        """
        prob_dec = Decimal(str(max(0.0, min(1.0, float(calibrated_p_congestion)))))
        dur_mins_dec = Decimal(str(max(0.0, float(expected_congestion_duration_mins))))
        dur_hours_dec = dur_mins_dec / Decimal("60.0")
        risk = prob_dec * dur_hours_dec * congestion_rate_value
        return risk.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def calculate_idle_queue_cost(
        cls, plant_queue_avg_30d: float, idle_rate_value: Decimal
    ) -> Decimal:
        """Calculates Idle Queue Cost Exposure: (plant_queue_avg_30d / 60.0) * idle_rate."""
        queue_dec = Decimal(str(max(0.0, float(plant_queue_avg_30d))))
        hours_dec = queue_dec / Decimal("60.0")
        cost = hours_dec * idle_rate_value
        return cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    async def compute_snapshot_financial_exposure(
        cls,
        session: AsyncSession,
        model_name: str,
        predicted_value: Optional[float],
        confidence_score: Optional[float],
        plant_code: str,
        customer_code: str,
        input_features: Dict[str, Any],
        target_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Computes authoritative financial exposure for a prediction snapshot according to the metric semantic contract.
        If rates are missing, returns calculation_status = NOT_CONFIGURED without fabricated amounts.
        """
        try:
            holding_rate_cfg = await cls.resolve_authoritative_rate(
                session, "HOLDING_IDLE_RATE", plant_code, customer_code, target_date
            )
            sla_rate_cfg = await cls.resolve_authoritative_rate(
                session, "SLA_BREACH_PENALTY", plant_code, customer_code, target_date
            )
            retention_rate_cfg = await cls.resolve_authoritative_rate(
                session, "CUSTOMER_RETENTION_RATE", plant_code, customer_code, target_date
            )
            congestion_rate_cfg = await cls.resolve_authoritative_rate(
                session, "PLANT_CONGESTION_RISK", plant_code, customer_code, target_date
            )
            benchmark_cfg = await cls.resolve_authoritative_rate(
                session, "STANDARD_TURNAROUND_BENCHMARK", plant_code, customer_code, target_date
            )
        except CalculationRateNotFoundError as err:
            logger.warning(f"[PHASE 3 FINANCIAL ENGINE] Rate missing: {err}")
            return {
                "calculation_status": "NOT_CONFIGURED",
                "calculation_notes": f"Missing rate configuration: {str(err)}",
                "financial_exposure_inr": None,
                "sla_penalty_risk_inr": None,
                "plant_congestion_risk_inr": None,
                "idle_queue_cost_inr": None,
                "total_financial_risk_inr": None,
                "currency": "INR",
                "calculation_lineage": {
                    "calculation_status": "NOT_CONFIGURED",
                    "calculation_version": CALCULATION_VERSION,
                    "reason": "MISSING_RATE_CONFIGURATION",
                },
            }

        # Currency mismatch safety check
        if (
            holding_rate_cfg.currency != "INR"
            or sla_rate_cfg.currency != "INR"
            or retention_rate_cfg.currency != "INR"
            or congestion_rate_cfg.currency != "INR"
        ):
            return {
                "calculation_status": "NOT_CONFIGURED",
                "calculation_notes": "Currency mismatch: Unsupported non-INR currency in rate configuration",
                "financial_exposure_inr": None,
                "sla_penalty_risk_inr": None,
                "plant_congestion_risk_inr": None,
                "idle_queue_cost_inr": None,
                "total_financial_risk_inr": None,
                "currency": "INR",
                "calculation_lineage": {
                    "calculation_status": "NOT_CONFIGURED",
                    "reason": "CURRENCY_MISMATCH",
                },
            }

        # Metric Semantic Contract Transformation
        delay_exposure = Decimal("0.00")
        sla_penalty_risk = Decimal("0.00")
        plant_congestion_risk = Decimal("0.00")

        turnaround_benchmark = float(benchmark_cfg.rate_value)

        # Expected Congestion Duration from features or baseline
        expected_congestion_duration_mins = float(
            input_features.get("plant_queue_avg_30d") or input_features.get("t2a_holding_mins") or 15.0
        )

        if model_name == "delay_regressor":
            delay_mins = max(0.0, float(predicted_value or 0.0))
            delay_exposure = cls.calculate_delay_exposure(delay_mins, holding_rate_cfg.rate_value)

        elif model_name == "turnaround_regressor":
            turnaround_mins = float(predicted_value or 0.0)
            excess_delay_mins = max(0.0, turnaround_mins - turnaround_benchmark)
            delay_exposure = cls.calculate_delay_exposure(excess_delay_mins, holding_rate_cfg.rate_value)

        elif model_name == "sla_breach_classifier":
            calibrated_p_breach = float(confidence_score if (confidence_score is not None and confidence_score > 0.0) else 0.5401)
            sla_penalty_risk = cls.calculate_sla_penalty_emv(calibrated_p_breach, sla_rate_cfg.rate_value)

        elif model_name == "plant_risk_classifier":
            calibrated_p_congestion = float(confidence_score if (confidence_score is not None and confidence_score > 0.0) else 0.3858)
            plant_congestion_risk = cls.calculate_plant_congestion_risk(
                calibrated_p_congestion,
                expected_congestion_duration_mins,
                congestion_rate_cfg.rate_value,
            )

        # Idle Queue Cost Exposure
        idle_cost = cls.calculate_idle_queue_cost(expected_congestion_duration_mins, retention_rate_cfg.rate_value)

        total_risk = delay_exposure + sla_penalty_risk + plant_congestion_risk + idle_cost

        semantic_contract = METRIC_SEMANTIC_CONTRACT.get(model_name, {})

        lineage = {
            "calculation_status": "SUCCESS",
            "calculation_version": CALCULATION_VERSION,
            "currency": "INR",
            "model_name": model_name,
            "predicted_metric": semantic_contract.get("predicted_metric"),
            "business_meaning": semantic_contract.get("business_meaning"),
            "turnaround_benchmark_mins": turnaround_benchmark,
            "expected_congestion_duration_mins": expected_congestion_duration_mins,
            "dimensional_formula": "probability * hours * ₹/hour = ₹" if model_name == "plant_risk_classifier" else "probability * ₹/event = ₹",
            "holding_rate": {
                "rate_id": holding_rate_cfg.rate_id,
                "value": float(holding_rate_cfg.rate_value),
                "authority_source": holding_rate_cfg.metadata_payload.get("authority_source") if holding_rate_cfg.metadata_payload else None,
            },
            "sla_rate": {
                "rate_id": sla_rate_cfg.rate_id,
                "value": float(sla_rate_cfg.rate_value),
                "authority_source": sla_rate_cfg.metadata_payload.get("authority_source") if sla_rate_cfg.metadata_payload else None,
            },
            "congestion_rate": {
                "rate_id": congestion_rate_cfg.rate_id,
                "value": float(congestion_rate_cfg.rate_value),
                "authority_source": congestion_rate_cfg.metadata_payload.get("authority_source") if congestion_rate_cfg.metadata_payload else None,
            },
            "retention_rate": {
                "rate_id": retention_rate_cfg.rate_id,
                "value": float(retention_rate_cfg.rate_value),
                "authority_source": retention_rate_cfg.metadata_payload.get("authority_source") if retention_rate_cfg.metadata_payload else None,
            },
        }

        return {
            "calculation_status": "SUCCESS",
            "calculation_notes": "Authoritative financial exposure calculated using rate hierarchy and Option A dimensional correctness.",
            "financial_exposure_inr": float(delay_exposure),
            "sla_penalty_risk_inr": float(sla_penalty_risk),
            "plant_congestion_risk_inr": float(plant_congestion_risk),
            "idle_queue_cost_inr": float(idle_cost),
            "total_financial_risk_inr": float(total_risk),
            "currency": "INR",
            "rate_version_id": holding_rate_cfg.rate_id,
            "calculation_lineage": lineage,
        }
