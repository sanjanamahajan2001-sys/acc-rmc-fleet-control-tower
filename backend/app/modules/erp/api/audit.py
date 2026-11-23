"""
Audit Logs REST API Endpoint
Exposes operational and security audit logs for import activity with filtering and pagination.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.common import get_db_session
from app.modules.erp.api.dependencies import AuthenticatedUser, TimedEnvelope
from app.modules.erp.api.schemas import AuditLogResponse, PaginatedResponse
from app.modules.erp.models import ImportAuditLog
from app.schemas.envelope import APIResponse

router = APIRouter(prefix="/audit-logs", tags=["ERP Audit Logs"])


@router.get(
    "",
    response_model=APIResponse[PaginatedResponse[AuditLogResponse]],
    status_code=status.HTTP_200_OK,
    summary="Get ERP Import Audit Logs",
    description="Returns paginated security and operational audit logs for import pipeline activity.",
)
async def list_audit_logs(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthenticatedUser,
    envelope: TimedEnvelope,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=200)] = 50,
) -> APIResponse[PaginatedResponse[AuditLogResponse]]:
    count_stmt = select(func.count()).select_from(ImportAuditLog)
    total = (await session.execute(count_stmt)).scalar_one() or 0

    stmt = (
        select(ImportAuditLog)
        .order_by(ImportAuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await session.execute(stmt)
    logs = list(result.scalars().all())

    items = [
        AuditLogResponse(
            id=log.id,
            job_id=log.job_id,
            action=log.action,
            details=log.details,
            created_at=log.created_at,
        )
        for log in logs
    ]

    total_pages = max(1, (total + page_size - 1) // page_size)
    paginated_data = PaginatedResponse[AuditLogResponse](
        items=items,
        total_records=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )

    return envelope.success(paginated_data)
