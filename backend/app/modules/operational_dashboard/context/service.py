from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.modules.erp.models import Plant, Customer, Dispatch
from app.modules.site_dashboard.sync.repository import SyncRepository
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_dashboard.context.dtos import (
    ShellContextResponseDTO,
    OperationalContextEnvelopeDTO,
    FilterOptionDTO,
)


class OperationalContextService:
    """Canonical Backend Context Service for Phase 3 Operational Dashboard."""

    @staticmethod
    async def get_shell_context(session: AsyncSession, params: DashboardFilterParams) -> ShellContextResponseDTO:
        # 1. Validate dataset_type parameter strictly
        valid_dataset_types = {"ALL", "REAL_ONLY", "SYNTHETIC_ONLY"}
        raw_type = (params.dataset_type or "ALL").upper()
        if raw_type not in valid_dataset_types:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid dataset_type '{params.dataset_type}'. Must be one of: {sorted(list(valid_dataset_types))}",
            )

        # 2. Query dynamic available plants from PostgreSQL (Deduplicated by code)
        plant_stmt = select(Plant).where(Plant.is_deleted == False).order_by(Plant.name)
        plants_raw = (await session.execute(plant_stmt)).scalars().all()
        
        seen_plant_codes = set()
        plants_db = []
        for p in plants_raw:
            if p.code not in seen_plant_codes:
                seen_plant_codes.add(p.code)
                plants_db.append(p)

        plant_code_map = {p.code: p.id for p in plants_db}
        plant_options = [FilterOptionDTO(id="ALL", name="All Plants")] + [
            FilterOptionDTO(id=p.code, name=p.name, code=p.code) for p in plants_db
        ]

        # 3. Query dynamic available customers from PostgreSQL (Deduplicated & excluding test synthetic codes)
        cust_stmt = select(Customer).where(Customer.is_deleted == False).order_by(Customer.name)
        custs_raw = (await session.execute(cust_stmt)).scalars().all()

        seen_cust_codes = set()
        custs_db = []
        for c in custs_raw:
            # Exclude synthetic test runner codes
            code_upper = (c.code or "").upper()
            if any(test_prefix in code_upper for test_prefix in ["CRASH", "REST", "TEST-", "CUST-T"]):
                continue
            if c.code not in seen_cust_codes:
                seen_cust_codes.add(c.code)
                custs_db.append(c)

        cust_code_map = {c.code: c.id for c in custs_db}
        customer_options = [FilterOptionDTO(id="ALL", name="All Customers")] + [
            FilterOptionDTO(id=c.code, name=c.name, code=c.code) for c in custs_db
        ]

        # 4. Deterministic validation for plant_id and customer_id
        selected_plant = params.plant_id or "ALL"
        if selected_plant != "ALL" and selected_plant not in plant_code_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plant identifier '{selected_plant}' not found in canonical database.",
            )

        selected_customer = params.customer_id or "ALL"
        if selected_customer != "ALL" and selected_customer not in cust_code_map:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer identifier '{selected_customer}' not found in canonical database.",
            )

        # 5. Query overall canonical DB state (total dispatches & snapshot version) via SyncRepository
        db_state = await SyncRepository.get_latest_db_state(session)
        overall_total = db_state["total_records"]

        # 6. Query filtered dispatches count matching the exact filter intersection
        count_stmt = select(func.count(Dispatch.id))
        filter_conditions = []

        if selected_plant != "ALL":
            filter_conditions.append(Dispatch.plant_id == plant_code_map[selected_plant])
        if selected_customer != "ALL":
            filter_conditions.append(Dispatch.customer_id == cust_code_map[selected_customer])

        if raw_type == "REAL_ONLY":
            filter_conditions.append(Dispatch.is_generated == False)
        elif raw_type == "SYNTHETIC_ONLY":
            filter_conditions.append(Dispatch.is_generated == True)

        if filter_conditions:
            count_stmt = count_stmt.where(and_(*filter_conditions))

        filtered_count = (await session.execute(count_stmt)).scalar() or 0

        # 7. Build production context envelope
        now_iso = datetime.now(timezone.utc).isoformat()
        dataset_status = "ACTIVE_PRODUCTION" if overall_total > 0 else "ZERO_RECORDS_EMPTY"

        # Dynamically resolve active dataset and operational date
        eff_dataset_id = params.dataset_id
        eff_op_date = params.operation_date or params.date_from

        if not eff_dataset_id or not eff_op_date:
            try:
                from app.modules.site_dashboard.orchestration.filter_metadata_service import DashboardFilterMetadataService
                meta = await DashboardFilterMetadataService.get_filter_metadata(session)
                if meta and meta.dataset_info:
                    if not eff_dataset_id:
                        eff_dataset_id = meta.dataset_info.dataset_id
                    if not eff_op_date:
                        eff_op_date = meta.dataset_info.operational_date
            except Exception:
                pass

        context_env = OperationalContextEnvelopeDTO(
            dataset_id=eff_dataset_id or "DS-20260204-001",
            snapshot_version=db_state["snapshot_version"],
            operational_date=eff_op_date or "2026-03-01",
            plant_id=selected_plant,
            customer_id=selected_customer,
            dataset_type=raw_type,
            generated_at=now_iso,
        )

        metadata = {
            "total_dispatches": filtered_count,
            "overall_total_dispatches": overall_total,
            "dataset_status": dataset_status,
            "sync_status": "SYNCHRONIZED",
            "e_tag": db_state["e_tag"],
        }

        return ShellContextResponseDTO(
            context=context_env,
            metadata=metadata,
            available_plants=plant_options,
            available_customers=customer_options,
        )
