"""
FastAPI Router for Customer Display Override Settings
Phase 2 REST Endpoints providing authenticated Admin CRUD operations over customer display overrides.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import require_admin, require_section_permission, require_authenticated_user
from app.dependencies.common import get_db_session
from app.modules.erp.api.dependencies import TimedEnvelope
from app.modules.settings.schemas import (
    CustomerSettingsDTO,
    UpdateCustomerOverrideRequest,
    CustomerOverrideMutationResponse,
)

from app.modules.settings.services.customer_override_service import CustomerDisplayOverrideService
from app.schemas.auth import TokenPayload
from app.schemas.envelope import APIResponse

customer_settings_router = APIRouter(
    prefix="/settings/customer-overrides",
    tags=["Customer Settings & Display Overrides"],
)


from app.modules.erp.api.dependencies import get_envelope_helper, EnvelopeHelper


@customer_settings_router.get("", response_model=APIResponse[List[CustomerSettingsDTO]])
async def list_customer_settings(
    customer_id: Optional[uuid.UUID] = Query(default=None, description="Optional customer UUID filter"),
    search: Optional[str] = Query(default=None, description="Optional search query filter for customer name or code"),
    claims: TokenPayload = Depends(require_authenticated_user),
    session: AsyncSession = Depends(get_db_session),
    envelope: EnvelopeHelper = Depends(get_envelope_helper),
) -> APIResponse[List[CustomerSettingsDTO]]:

    """
    Retrieves customer settings list with raw ERP customer names, effective display names,
    override metadata, and associated plant context. Accessible by all authenticated users.
    """
    service = CustomerDisplayOverrideService()
    dtos = await service.get_customer_settings(session, customer_id=customer_id, search_query=search)
    return envelope.success(dtos)


@customer_settings_router.put("/{customer_id}", response_model=APIResponse[CustomerOverrideMutationResponse])
async def update_customer_display_override(
    customer_id: uuid.UUID,
    body: UpdateCustomerOverrideRequest,
    claims: TokenPayload = Depends(require_section_permission("settings", "edit")),
    session: AsyncSession = Depends(get_db_session),
    envelope: EnvelopeHelper = Depends(get_envelope_helper),
) -> APIResponse[CustomerOverrideMutationResponse]:
    """
    Creates or updates a manual display name override for a customer.
    Requires Administrator privileges (require_admin).
    """
    user_uuid = None
    try:
        user_uuid = uuid.UUID(claims.sub)
    except ValueError:
        pass

    service = CustomerDisplayOverrideService()
    res = await service.upsert_customer_override(
        session=session,
        customer_id=customer_id,
        override_name=body.override_name,
        override_reason=body.override_reason,
        updated_by_name=getattr(claims, "email", "ADMIN"),
        user_uuid=user_uuid,
    )
    return envelope.success(res)


@customer_settings_router.delete("/{customer_id}", response_model=APIResponse[CustomerOverrideMutationResponse])
async def reset_customer_display_override(
    customer_id: uuid.UUID,
    claims: TokenPayload = Depends(require_section_permission("settings", "edit")),
    session: AsyncSession = Depends(get_db_session),
    envelope: EnvelopeHelper = Depends(get_envelope_helper),
) -> APIResponse[CustomerOverrideMutationResponse]:

    """
    Resets / removes a customer display override, reverting the effective display name back to the ERP-derived value.
    Requires Administrator privileges (require_admin).
    """
    user_uuid = None
    try:
        user_uuid = uuid.UUID(claims.sub)
    except ValueError:
        pass

    service = CustomerDisplayOverrideService()
    res = await service.reset_customer_override(
        session=session,
        customer_id=customer_id,
        updated_by_name=getattr(claims, "email", "ADMIN"),
        user_uuid=user_uuid,
    )
    return envelope.success(res)
