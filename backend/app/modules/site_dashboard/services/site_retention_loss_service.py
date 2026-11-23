"""
Site Retention (>10 mins) Loss Service
Workstream 2.13 Per-Client Retention Exposure Engine
"""

from typing import Dict, Any, List
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.erp.models import Dispatch, Customer, CustomerDisplayOverride
from app.modules.settings.services.customer_override_service import CustomerDisplayOverrideService
from app.modules.site_dashboard.dto.canonical_dtos import (
    SiteRetentionLossRowDTO,
    SiteRetentionLossResponseDTO,
)


class SiteRetentionLossService:
    """Service to compute per-client excess retention metrics (>10 mins)."""

    RETENTION_THRESHOLD_MINS: float = 10.0

    @classmethod
    async def get_retention_loss_breakdown(
        cls, session: AsyncSession, params_dict: Dict[str, Any]
    ) -> SiteRetentionLossResponseDTO:
        eff_name = CustomerDisplayOverrideService.get_effective_name_expression()

        stmt = (
            select(
                Customer.id.label("customer_id"),
                Customer.code.label("customer_code"),
                eff_name.label("customer_name"),
                func.sum(
                    case((Dispatch.t2c_retention_mins > cls.RETENTION_THRESHOLD_MINS, 1), else_=0)
                ).label("affected_trips"),
                func.sum(
                    case(
                        (
                            Dispatch.t2c_retention_mins > cls.RETENTION_THRESHOLD_MINS,
                            Dispatch.t2c_retention_mins - cls.RETENTION_THRESHOLD_MINS,
                        ),
                        else_=0.0,
                    )
                ).label("total_excess_mins"),
                func.avg(
                    case(
                        (
                            Dispatch.t2c_retention_mins > cls.RETENTION_THRESHOLD_MINS,
                            Dispatch.t2c_retention_mins - cls.RETENTION_THRESHOLD_MINS,
                        ),
                        else_=None,
                    )
                ).label("avg_excess_mins"),
            )
            .join(Customer, Dispatch.customer_id == Customer.id)
            .outerjoin(CustomerDisplayOverride, CustomerDisplayOverride.customer_id == Customer.id)
            .group_by(Customer.id, Customer.code, CustomerDisplayOverride.override_name)
            .having(
                func.sum(
                    case((Dispatch.t2c_retention_mins > cls.RETENTION_THRESHOLD_MINS, 1), else_=0)
                )
                > 0
            )
            .order_by(
                func.sum(
                    case(
                        (
                            Dispatch.t2c_retention_mins > cls.RETENTION_THRESHOLD_MINS,
                            Dispatch.t2c_retention_mins - cls.RETENTION_THRESHOLD_MINS,
                        ),
                        else_=0.0,
                    )
                ).desc()
            )
        )

        # Apply plant, customer, dataset filters if present
        plant_id = params_dict.get("plant_id")
        if plant_id and plant_id != "ALL":
            stmt = stmt.where(Dispatch.plant_id == plant_id)

        cust_filter = params_dict.get("customer_id")
        if cust_filter and cust_filter != "ALL":
            stmt = stmt.where(Customer.code == cust_filter)

        dataset_type = params_dict.get("dataset_type")
        if dataset_type == "REAL_ONLY":
            stmt = stmt.where(Dispatch.source_system != "SYNTHETIC")
        elif dataset_type == "SYNTHETIC_ONLY":
            stmt = stmt.where(Dispatch.source_system == "SYNTHETIC")

        results = (await session.execute(stmt)).all()

        rows: List[SiteRetentionLossRowDTO] = []
        for idx, row in enumerate(results, start=1):
            total_excess_mins = float(row.total_excess_mins or 0.0)
            avg_excess_mins = round(float(row.avg_excess_mins or 0.0), 1)

            # Format total excess as HH:MM
            tot_hrs = int(total_excess_mins // 60)
            tot_rem_mins = int(round(total_excess_mins % 60))
            formatted_time = f"{tot_hrs}:{tot_rem_mins:02d}"

            rows.append(
                SiteRetentionLossRowDTO(
                    rank=idx,
                    customer_id=str(row.customer_id),
                    customer_code=row.customer_code,
                    customer_name=row.customer_name,
                    affected_trips=int(row.affected_trips or 0),
                    avg_excess_retention_mins=avg_excess_mins,
                    total_excess_retention_mins=round(total_excess_mins, 1),
                    total_excess_retention_formatted=formatted_time,
                )
            )

        return SiteRetentionLossResponseDTO(
            total_affected_clients=len(rows),
            data=rows,
        )
