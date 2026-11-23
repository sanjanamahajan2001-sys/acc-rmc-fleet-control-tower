"""
WS-07.5 Operational Alerts FastAPI Router.
Provides production REST API endpoints for listing, summarizing, context, details, acknowledging, resolving, and archiving operational alerts.
"""
from uuid import UUID
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RecordNotFoundError, OptimisticLockError
from app.dependencies.common import get_db_session
from app.modules.erp.api.dependencies import AuthenticatedUser
from app.modules.operational_dashboard.widgets.alerts.service import AlertService, RESOLVED_OPERATIONAL_RETENTION_HOURS
from app.modules.operational_dashboard.widgets.alerts.dtos import (
    OperationalAlertItemDTO,
    AlertListResponseDTO,
    AlertSummaryDTO,
    OperationalDatasetContextDTO,
    AlertAcknowledgeRequestDTO,
    AlertResolveRequestDTO,
)

router = APIRouter(prefix="/alerts", tags=["Operational Alerts"])

@router.post(
    "/generate",
    status_code=status.HTTP_200_OK,
    summary="Evaluate & Generate Alerts for Active Dataset",
    description="Evaluates all dispatches for the currently active dataset and creates operational alerts.",
)
async def generate_alerts_for_active_dataset(
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    return await AlertService.evaluate_and_persist_active_alerts(session=session)

@router.get(
    "",
    response_model=AlertListResponseDTO,
    status_code=status.HTTP_200_OK,
    summary="List Operational Alerts",
    description="Returns a paginated list of operational alerts filtered by plant, customer, dataset, status, severity, or alert_type.",
)
async def list_alerts(
    plant_id: str = Query("ALL", description="Plant filter ID or ALL"),
    customer_id: str = Query("ALL", description="Customer filter ID or ALL"),
    dataset_id: Optional[str] = Query(None, description="Dataset ID filter"),
    status_filter: Optional[str] = Query(None, alias="status", description="OPEN | ACKNOWLEDGED | RESOLVED | ARCHIVED"),
    severity: Optional[str] = Query(None, description="CRITICAL | WARNING | INFO"),
    alert_type: Optional[str] = Query(None, description="Alert Rule Type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page (max 100)"),
    session: AsyncSession = Depends(get_db_session),
) -> AlertListResponseDTO:
    return await AlertService.get_alerts_list(
        session=session,
        plant_id=plant_id,
        customer_id=customer_id,
        dataset_id=dataset_id,
        status=status_filter,
        severity=severity,
        alert_type=alert_type,
        page=page,
        page_size=page_size,
    )

@router.get(
    "/summary",
    response_model=AlertSummaryDTO,
    status_code=status.HTTP_200_OK,
    summary="Get Alert Summary Counts",
    description="Returns aggregate counts of open, critical, warning, info, and acknowledged alerts under active scope filters.",
)
async def get_alerts_summary(
    plant_id: str = Query("ALL", description="Plant filter ID or ALL"),
    customer_id: str = Query("ALL", description="Customer filter ID or ALL"),
    dataset_id: Optional[str] = Query(None, description="Dataset ID filter"),
    session: AsyncSession = Depends(get_db_session),
) -> AlertSummaryDTO:
    return await AlertService.get_summary(
        session=session, plant_id=plant_id, customer_id=customer_id, dataset_id=dataset_id
    )

@router.get(
    "/context",
    response_model=OperationalDatasetContextDTO,
    status_code=status.HTTP_200_OK,
    summary="Get Alert Dataset Context",
    description="Returns authoritative dataset metadata, total dispatches, and import timestamp for Alert Center ribbon.",
)
async def get_alerts_context(
    plant_id: str = Query("ALL", description="Plant filter ID or ALL"),
    customer_id: str = Query("ALL", description="Customer filter ID or ALL"),
    dataset_id: Optional[str] = Query(None, description="Dataset ID filter"),
    session: AsyncSession = Depends(get_db_session),
) -> OperationalDatasetContextDTO:
    return await AlertService.get_dataset_context(
        session=session, plant_id=plant_id, customer_id=customer_id, dataset_id=dataset_id
    )

@router.post(
    "/archive",
    status_code=status.HTTP_200_OK,
    summary="Trigger Archival of Resolved Alerts",
    description="Triggers the archival transition (RESOLVED -> ARCHIVED) for alerts older than the specified retention threshold.",
)
async def archive_resolved_alerts(
    retention_hours: float = Query(RESOLVED_OPERATIONAL_RETENTION_HOURS, ge=0.0, description="Retention threshold in hours"),
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    count = await AlertService.archive_resolved_alerts(session=session, retention_hours=retention_hours)
    return {"status": "SUCCESS", "archived_count": count, "retention_hours": retention_hours}

@router.get(
    "/{alert_id}",
    response_model=OperationalAlertItemDTO,
    status_code=status.HTTP_200_OK,
    summary="Get Alert Detail by ID",
    description="Returns full operational alert detail including metric evidence JSON, impact analysis, and recommended action with scope isolation protection.",
)
async def get_alert_detail(
    alert_id: UUID,
    plant_id: str = Query("ALL", description="Plant filter ID or ALL"),
    customer_id: str = Query("ALL", description="Customer filter ID or ALL"),
    session: AsyncSession = Depends(get_db_session),
) -> OperationalAlertItemDTO:
    dto, error = await AlertService.get_alert_detail(session=session, alert_id=alert_id, plant_id=plant_id, customer_id=customer_id)
    if error in ["ALERT_NOT_FOUND", "SCOPE_ACCESS_DENIED"]:
        raise RecordNotFoundError(
            message=f"Operational Alert '{alert_id}' not found under specified plant/customer scope.",
            details={"resource_type": "OperationalAlert", "resource_id": str(alert_id)}
        )
    return dto

@router.post(
    "/{alert_id}/acknowledge",
    response_model=OperationalAlertItemDTO,
    status_code=status.HTTP_200_OK,
    summary="Acknowledge Operational Alert",
    description="Transition alert lifecycle from OPEN to ACKNOWLEDGED with operator identity and notes.",
)
async def acknowledge_alert(
    alert_id: UUID,
    payload: AlertAcknowledgeRequestDTO,
    session: AsyncSession = Depends(get_db_session),
    user: Optional[AuthenticatedUser] = None,
) -> OperationalAlertItemDTO:
    operator_name = payload.acknowledged_by
    if user and hasattr(user, "username") and user.username:
        operator_name = user.username

    dto, error = await AlertService.acknowledge_alert(
        session=session,
        alert_id=alert_id,
        acknowledged_by=operator_name,
        notes=payload.notes,
    )

    if error:
        if error == "ALERT_NOT_FOUND":
            raise RecordNotFoundError(
                message=f"Operational Alert '{alert_id}' not found.",
                details={"resource_type": "OperationalAlert", "resource_id": str(alert_id)}
            )
        else:
            raise OptimisticLockError(
                message=error if "INVALID_LIFECYCLE_TRANSITION" in error else "Alert state modified concurrently.",
                details={"resource_type": "OperationalAlert", "resource_id": str(alert_id)}
            )

    return dto

@router.post(
    "/{alert_id}/resolve",
    response_model=OperationalAlertItemDTO,
    status_code=status.HTTP_200_OK,
    summary="Resolve Operational Alert",
    description="Transition alert lifecycle from OPEN/ACKNOWLEDGED to RESOLVED with resolution reason.",
)
async def resolve_alert(
    alert_id: UUID,
    payload: AlertResolveRequestDTO,
    session: AsyncSession = Depends(get_db_session),
    user: Optional[AuthenticatedUser] = None,
) -> OperationalAlertItemDTO:
    operator_name = payload.resolved_by
    if user and hasattr(user, "username") and user.username:
        operator_name = user.username

    dto, error = await AlertService.resolve_alert(
        session=session,
        alert_id=alert_id,
        resolved_by=operator_name,
        resolution_reason=payload.resolution_reason,
    )

    if error:
        if error == "ALERT_NOT_FOUND":
            raise RecordNotFoundError(
                message=f"Operational Alert '{alert_id}' not found.",
                details={"resource_type": "OperationalAlert", "resource_id": str(alert_id)}
            )
        else:
            raise OptimisticLockError(
                message=error if "INVALID_LIFECYCLE_TRANSITION" in error else "Alert state modified concurrently.",
                details={"resource_type": "OperationalAlert", "resource_id": str(alert_id)}
            )

    return dto
