"""
Customer Display Override Domain Service
Phase 2 Service Layer for querying customer settings, resolving effective names,
and managing display overrides with RBAC and event auditing.
"""

import re
import uuid
from typing import List, Optional
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import RecordNotFoundError, DomainValidationError
from app.events.bus import EventBus

from app.events.schema import BaseEvent
from app.modules.erp.models import Customer, CustomerDisplayOverride, Plant, Dispatch
from app.modules.settings.schemas import (
    CustomerSettingsDTO,
    PlantContextDTO,
    CustomerOverrideMutationResponse,
)



class CustomerDisplayOverrideService:
    """
    Authoritative domain service for managing customer display overrides and effective name resolution.
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus

    @staticmethod
    def get_effective_name_expression():
        """
        Authoritative SQLAlchemy expression for resolving effective customer display names in SQL queries.
        Calculates:
            COALESCE(
                NULLIF(TRIM(customer_display_overrides.override_name), ''),
                customers.name
            ) AS effective_customer_name
        """
        return func.coalesce(
            func.nullif(func.trim(CustomerDisplayOverride.override_name), ""),
            Customer.name,
        ).label("effective_customer_name")

    @staticmethod
    def resolve_effective_name(raw_name: str, override: Optional[CustomerDisplayOverride]) -> str:
        """
        Authoritative Python name resolver:
        effective_name = override_name if (active override exists and not deleted) else raw_name
        """
        if override and not override.is_deleted and override.override_name and override.override_name.strip():
            return override.override_name.strip()
        return raw_name


    @staticmethod
    def sanitize_override_name(raw_input: str) -> str:
        """Sanitizes user input: collapses whitespace, trims, and validates non-emptiness."""
        if not raw_input:
            raise DomainValidationError("Override name cannot be empty")
        cleaned = re.sub(r"\s+", " ", str(raw_input)).strip()
        if not cleaned:
            raise DomainValidationError("Override name cannot be blank or whitespace-only")
        if len(cleaned) > 255:
            raise DomainValidationError("Override name cannot exceed 255 characters")
        return cleaned

    async def get_customer_settings(
        self,
        session: AsyncSession,
        customer_id: Optional[uuid.UUID] = None,
        search_query: Optional[str] = None,
    ) -> List[CustomerSettingsDTO]:
        """
        Queries B2B customers, eager-loads display overrides and associated plants via dispatches.
        """
        stmt = (
            select(Customer)
            .options(selectinload(Customer.display_override))
            .where(Customer.is_deleted == False)
            .order_by(Customer.name.asc())
        )

        if customer_id:
            stmt = stmt.where(Customer.id == customer_id)
        if search_query:
            q = f"%{search_query.strip()}%"
            stmt = stmt.where((Customer.name.ilike(q)) | (Customer.code.ilike(q)))

        res = await session.execute(stmt)
        customers = res.scalars().all()

        if customer_id and not customers:
            raise RecordNotFoundError(f"Customer with ID '{customer_id}' not found")

        # Gather plant context per customer via dispatches join
        cust_ids = [c.id for c in customers]
        plant_mapping: dict[uuid.UUID, List[PlantContextDTO]] = {cid: [] for cid in cust_ids}

        if cust_ids:
            plant_stmt = (
                select(Dispatch.customer_id, Plant.id, Plant.code, Plant.name)
                .join(Plant, Dispatch.plant_id == Plant.id)
                .where(Dispatch.customer_id.in_(cust_ids))
                .distinct()
            )
            p_res = await session.execute(plant_stmt)
            for cid, p_id, p_code, p_name in p_res.all():
                plant_mapping[cid].append(
                    PlantContextDTO(plant_id=p_id, plant_code=p_code, plant_name=p_name)
                )

        dtos = []
        for c in customers:
            ov = c.display_override
            is_active_ov = ov is not None and not ov.is_deleted
            eff_name = self.resolve_effective_name(c.name, ov if is_active_ov else None)
            
            dtos.append(
                CustomerSettingsDTO(
                    customer_id=c.id,
                    customer_code=c.code,
                    raw_customer_name=c.name,
                    effective_customer_name=eff_name,
                    is_overridden=is_active_ov,
                    override_reason=ov.override_reason if is_active_ov else None,
                    updated_by_name=ov.updated_by_name if is_active_ov else None,
                    plants=plant_mapping.get(c.id, []),
                )
            )

        return dtos

    async def upsert_customer_override(
        self,
        session: AsyncSession,
        customer_id: uuid.UUID,
        override_name: str,
        override_reason: Optional[str] = None,
        updated_by_name: str = "ADMIN",
        user_uuid: Optional[uuid.UUID] = None,
        correlation_id: str = "sys-override",
        request_id: str = "sys-override",
    ) -> CustomerOverrideMutationResponse:
        """
        Creates or updates a manual display override for a customer atomically.
        """
        cleaned_name = self.sanitize_override_name(override_name)

        # Check customer exists
        c_stmt = select(Customer).where(Customer.id == customer_id, Customer.is_deleted == False)
        cust = (await session.execute(c_stmt)).scalars().first()
        if not cust:
            raise RecordNotFoundError(f"Customer with ID '{customer_id}' not found")


        # Query existing override
        ov_stmt = select(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == customer_id)
        ov = (await session.execute(ov_stmt)).scalars().first()

        prev_eff = self.resolve_effective_name(cust.name, ov)

        if ov:
            ov.override_name = cleaned_name
            ov.override_reason = override_reason.strip() if override_reason else None
            ov.updated_by_name = updated_by_name
            ov.updated_by = user_uuid
            ov.is_deleted = False
            ov.deleted_at = None
            ov.version_id += 1
        else:
            ov = CustomerDisplayOverride(
                customer_id=customer_id,
                override_name=cleaned_name,
                override_reason=override_reason.strip() if override_reason else None,
                updated_by_name=updated_by_name,
                updated_by=user_uuid,
            )
            session.add(ov)

        await session.commit()
        await session.refresh(ov)

        # Publish audit event
        if self.event_bus:
            await self.event_bus.publish(
                BaseEvent(
                    event_type="settings.customer_override.updated",
                    correlation_id=correlation_id,
                    request_id=request_id,
                    payload={
                        "customer_id": str(customer_id),
                        "customer_code": cust.code,
                        "raw_customer_name": cust.name,
                        "previous_effective_name": prev_eff,
                        "new_effective_name": cleaned_name,
                        "updated_by_name": updated_by_name,
                        "updated_by": str(user_uuid) if user_uuid else None,
                        "override_reason": override_reason,
                    },
                )
            )

        return CustomerOverrideMutationResponse(
            customer_id=cust.id,
            customer_code=cust.code,
            raw_customer_name=cust.name,
            effective_customer_name=cleaned_name,
            is_overridden=True,
            message="Customer display override successfully updated",
        )

    async def reset_customer_override(
        self,
        session: AsyncSession,
        customer_id: uuid.UUID,
        updated_by_name: str = "ADMIN",
        user_uuid: Optional[uuid.UUID] = None,
        correlation_id: str = "sys-override",
        request_id: str = "sys-override",
    ) -> CustomerOverrideMutationResponse:
        """
        Resets / deletes a customer display override to revert effective_name back to raw ERP customer name.
        Uses SQL DELETE (hard delete) to cleanly purge manual override state.
        """
        c_stmt = select(Customer).where(Customer.id == customer_id, Customer.is_deleted == False)
        cust = (await session.execute(c_stmt)).scalars().first()
        if not cust:
            raise RecordNotFoundError(f"Customer with ID '{customer_id}' not found")


        ov_stmt = select(CustomerDisplayOverride).where(CustomerDisplayOverride.customer_id == customer_id)
        ov = (await session.execute(ov_stmt)).scalars().first()

        if ov:
            prev_eff = ov.override_name
            await session.delete(ov)
            await session.commit()

            if self.event_bus:
                await self.event_bus.publish(
                    BaseEvent(
                        event_type="settings.customer_override.reset",
                        correlation_id=correlation_id,
                        request_id=request_id,
                        payload={
                            "customer_id": str(customer_id),
                            "customer_code": cust.code,
                            "raw_customer_name": cust.name,
                            "previous_effective_name": prev_eff,
                            "new_effective_name": cust.name,
                            "reset_by_name": updated_by_name,
                            "reset_by": str(user_uuid) if user_uuid else None,
                        },
                    )
                )

        return CustomerOverrideMutationResponse(
            customer_id=cust.id,
            customer_code=cust.code,
            raw_customer_name=cust.name,
            effective_customer_name=cust.name,
            is_overridden=False,
            message="Customer display override successfully reset to ERP default",
        )
