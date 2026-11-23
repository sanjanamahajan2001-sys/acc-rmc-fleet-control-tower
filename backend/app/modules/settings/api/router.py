"""
FastAPI Platform Configuration Registry REST Endpoints
Workstream X.3 Production Endpoints
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.common import get_db_session
from app.dependencies.auth import require_admin
from app.schemas.auth import TokenPayload
from app.modules.erp.api.dependencies import TimedEnvelope
from app.modules.settings.models import PlatformConfiguration, PlatformConfigurationHistory, ConfigurationCategory
from app.modules.settings.schemas import (
    PlatformConfigurationDTO,
    ConfigurationCategoryDTO,
    UpdateConfigurationRequest,
    ConfigurationHistoryDTO,
)
from app.modules.settings.schemas_db_preview import (
    DatabaseSchemaResponseDTO,
    DatabaseSqlExportResponseDTO,
)
from app.modules.settings.services.schema_introspection_service import DatabaseSchemaIntrospectionService
from app.core.config import settings as app_settings
from app.schemas.envelope import APIResponse

router = APIRouter(prefix="/settings", tags=["Platform Configuration Registry"])

# Global Configuration Cache Dictionary
_CONFIG_CACHE: dict[str, dict[str, Any]] = {}


@router.get("/database-schema", response_model=APIResponse[DatabaseSchemaResponseDTO], summary="Inspect Live PostgreSQL Database Schema")
async def get_database_schema(
    session: AsyncSession = Depends(get_db_session),
    admin_claims: TokenPayload = Depends(require_admin),
    envelope: TimedEnvelope = None,
) -> APIResponse[DatabaseSchemaResponseDTO]:
    """
    Returns dynamically introspected PostgreSQL database schema.
    Requires Administrator privileges.
    """
    db_name = getattr(app_settings, "POSTGRES_DB", "fleet_control_tower_db")
    schema_dto = await DatabaseSchemaIntrospectionService.get_database_schema(
        session=session,
        database_name=db_name,
    )
    return envelope.success(schema_dto)


@router.get(
    "/database-schema/sql-export",
    response_model=APIResponse[DatabaseSqlExportResponseDTO],
    summary="Export Read-Only PostgreSQL Schema SQL",
)
async def get_database_sql_export(
    session: AsyncSession = Depends(get_db_session),
    admin_claims: TokenPayload = Depends(require_admin),
    envelope: TimedEnvelope = None,
) -> APIResponse[DatabaseSqlExportResponseDTO]:
    """
    Generates clean read-only DDL SQL export of the live PostgreSQL schema.
    Requires Administrator privileges.
    """
    db_name = getattr(app_settings, "POSTGRES_DB", "fleet_control_tower_db")
    export_dto = await DatabaseSchemaIntrospectionService.generate_sql_export(
        session=session,
        database_name=db_name,
    )
    return envelope.success(export_dto)


@router.get("", response_model=APIResponse[dict[str, list[PlatformConfigurationDTO]]])
async def get_all_configurations(
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[dict[str, list[PlatformConfigurationDTO]]]:
    stmt = select(PlatformConfiguration).order_by(PlatformConfiguration.domain, PlatformConfiguration.display_order)
    configs = (await session.execute(stmt)).scalars().all()

    grouped: dict[str, list[PlatformConfigurationDTO]] = {}
    for c in configs:
        dto = PlatformConfigurationDTO.model_validate(c)
        if c.is_secret:
            dto.value = "********"
        if c.domain not in grouped:
            grouped[c.domain] = []
        grouped[c.domain].append(dto)

    return envelope.success(grouped)


@router.get("/categories", response_model=APIResponse[list[ConfigurationCategoryDTO]])
async def get_configuration_categories(
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[list[ConfigurationCategoryDTO]]:
    stmt = select(ConfigurationCategory).order_by(ConfigurationCategory.display_order)
    cats = (await session.execute(stmt)).scalars().all()
    return envelope.success([ConfigurationCategoryDTO.model_validate(c) for c in cats])


@router.get("/{domain}", response_model=APIResponse[list[PlatformConfigurationDTO]])
async def get_domain_configurations(
    domain: str,
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[list[PlatformConfigurationDTO]]:
    stmt = select(PlatformConfiguration).where(PlatformConfiguration.domain == domain).order_by(PlatformConfiguration.display_order)
    configs = (await session.execute(stmt)).scalars().all()

    res = []
    for c in configs:
        dto = PlatformConfigurationDTO.model_validate(c)
        if c.is_secret:
            dto.value = "********"
        res.append(dto)

    return envelope.success(res)


@router.put("/{domain}/{key}", response_model=APIResponse[PlatformConfigurationDTO])
async def update_configuration_item(
    domain: str,
    key: str,
    body: UpdateConfigurationRequest,
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[PlatformConfigurationDTO]:
    stmt = select(PlatformConfiguration).where(
        PlatformConfiguration.domain == domain,
        PlatformConfiguration.key == key,
    )
    config = (await session.execute(stmt)).scalars().first()

    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Configuration item not found")

    if not config.editable:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Configuration item is read-only")

    # Record change in Configuration History
    history = PlatformConfigurationHistory(
        configuration_id=config.id,
        previous_value=config.value,
        new_value=body.value,
        changed_by="admin",
        change_reason=body.change_reason,
    )
    session.add(history)

    # Update config value
    config.value = body.value
    await session.commit()
    await session.refresh(config)

    # Invalidate Cache
    if domain in _CONFIG_CACHE:
        _CONFIG_CACHE[domain][key] = body.value

    dto = PlatformConfigurationDTO.model_validate(config)
    if config.is_secret:
        dto.value = "********"

    return envelope.success(dto)


@router.post("/cache/reload", response_model=APIResponse[dict[str, str]])
async def reload_configuration_cache(
    session: AsyncSession = Depends(get_db_session),
    envelope: TimedEnvelope = None,
) -> APIResponse[dict[str, str]]:
    stmt = select(PlatformConfiguration)
    configs = (await session.execute(stmt)).scalars().all()

    _CONFIG_CACHE.clear()
    for c in configs:
        if c.domain not in _CONFIG_CACHE:
            _CONFIG_CACHE[c.domain] = {}
        _CONFIG_CACHE[c.domain][c.key] = c.value

    return envelope.success({"message": f"Successfully reloaded {len(_CONFIG_CACHE)} configuration domains into memory cache."})
