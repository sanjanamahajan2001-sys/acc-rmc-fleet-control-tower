import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.modules.reports.workers.report_worker import ReportBackgroundWorker
from app.modules.reports.services.security_limiter import SecurityRateLimiter, DownloadTokenManager
from app.modules.reports.services.telemetry import ReportingMetricsCollector



from app.modules.reports.schemas.report_schemas import (
    ReportRequestDTO,
    ReportExecutionResponse,
    ReportStatus,
    ScopeValidationStatus,
    ReportFormat
)
from app.modules.reports.models.report_execution import ReportExecutionAudit
from app.modules.reports.services.report_registry import ReportRegistry, ReportDefinitionDTO
from app.modules.reports.services.scope_resolver import ScopeResolverService
from app.modules.reports.services.report_service import ReportService
from app.modules.reports.handlers.dispatch_analysis_handler import DispatchAnalysisReportHandler
from app.modules.reports.handlers.site_operations_handler import SiteOperationsReportHandler
from app.modules.reports.handlers.fleet_operations_handler import FleetOperationsReportHandler
from app.modules.reports.handlers.site_comparison_handler import SiteComparisonReportHandler
from app.modules.reports.handlers.dispatch_optimization_handler import DispatchOptimizationReportHandler
from app.modules.reports.handlers.operational_intelligence_handler import OperationalIntelligenceReportHandler
from app.modules.reports.handlers.predictive_intelligence_handler import PredictiveIntelligenceReportHandler
from app.modules.reports.handlers.action_execution_handler import ActionExecutionReportHandler
from app.modules.reports.handlers.alerts_incidents_handler import AlertsIncidentsReportHandler
from app.modules.reports.handlers.timeline_operations_handler import TimelineOperationsReportHandler
from app.modules.reports.handlers.erp_import_audit_handler import ERPImportAuditReportHandler
from app.modules.reports.handlers.erp_data_explorer_handler import ERPDataExplorerReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.reports.storage.artifact_storage import ReportArtifactStorage

reports_router = APIRouter(prefix="/reports", tags=["Reports & Exports"])
report_service = ReportService()
scope_resolver = ScopeResolverService()
dispatch_handler = DispatchAnalysisReportHandler()
site_operations_handler = SiteOperationsReportHandler()
fleet_operations_handler = FleetOperationsReportHandler()
site_comparison_handler = SiteComparisonReportHandler()
dispatch_optimization_handler = DispatchOptimizationReportHandler()
operational_intelligence_handler = OperationalIntelligenceReportHandler()
predictive_intelligence_handler = PredictiveIntelligenceReportHandler()
action_execution_handler = ActionExecutionReportHandler()
alerts_incidents_handler = AlertsIncidentsReportHandler()
timeline_operations_handler = TimelineOperationsReportHandler()
erp_import_audit_handler = ERPImportAuditReportHandler()
erp_data_explorer_handler = ERPDataExplorerReportHandler()













@reports_router.get("", response_model=List[ReportDefinitionDTO])
async def list_reports():
    return ReportRegistry.list_all()


@reports_router.get("/metrics")
async def get_reporting_metrics():
    payload, content_type = ReportingMetricsCollector.get_metrics_payload()
    return Response(content=payload, media_type=content_type)



@reports_router.get("/{report_id}", response_model=ReportDefinitionDTO)
async def get_report_definition(report_id: str):
    definition = ReportRegistry.get(report_id)
    if not definition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "REPORT_NOT_FOUND",
                "message": f"Report '{report_id}' is not registered in the report catalog."
            }
        )
    return definition


@reports_router.post("/generate", response_model=ReportExecutionResponse)
async def generate_report(
    req: ReportRequestDTO,
    request: Request = None,
    db: AsyncSession = Depends(get_db_session)
):
    client_ip = request.client.host if request and request.client else "127.0.0.1"
    key = f"rate_limit:gen:{req.requested_by}:{client_ip}"
    allowed, retry_after = SecurityRateLimiter.check_rate_limit(
        key=key,
        max_requests=settings.REPORT_GENERATE_RATE_LIMIT_PER_MINUTE,
        window_seconds=60
    )
    if not allowed:
        ReportingMetricsCollector.record_rate_limit(endpoint="/generate")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMIT_EXCEEDED", "message": "Report generation rate limit exceeded. Please try again later."},
            headers={"Retry-After": str(retry_after)}
        )


    definition = ReportRegistry.get(req.report_id)

    if not definition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "REPORT_NOT_FOUND", "message": f"Report '{req.report_id}' not found."}
        )

    is_valid, effective_scope, error_code = await scope_resolver.resolve_and_validate_scope(
        session=db,
        raw_scope=req.scope.model_dump()
    )

    if not is_valid:
        await report_service.create_execution_record(
            session=db,
            report_id=req.report_id,
            report_type=definition.source_service,
            format=req.format.value,
            requested_by=req.requested_by,
            requested_scope=req.scope.model_dump(),
            effective_scope={},
            scope_fingerprint="",
            validation_status=ScopeValidationStatus.INVALID_SCOPE.value,
            record_count=0,
            status=ReportStatus.SCOPE_VALIDATION_FAILED.value,
            error_code=error_code or "REPORT_SCOPE_VALIDATION_FAILED",
            error_message="The requested report scope is invalid or unauthorized."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "REPORT_SCOPE_VALIDATION_FAILED",
                "message": "The requested report scope is invalid or unauthorized.",
                "reason": error_code
            }
        )

    record_count = effective_scope.get("record_count", 0)
    execution_status = ReportStatus.NO_DATA if record_count == 0 else ReportStatus.COMPLETED

    execution = await report_service.create_execution_record(
        session=db,
        report_id=req.report_id,
        report_type=definition.source_service,
        format=req.format.value,
        requested_by=req.requested_by,
        requested_scope=req.scope.model_dump(),
        effective_scope=effective_scope,
        scope_fingerprint=effective_scope.get("scope_fingerprint", ""),
        validation_status=ScopeValidationStatus.VALIDATED.value,
        record_count=record_count,
        dataset_id=effective_scope.get("resolved_dataset_id"),
        status=execution_status.value
    )

    if req.report_id == "site_operations":

        canonical_report = await site_operations_handler.build_canonical_report(
            session=db,
            execution_id=execution.execution_id,
            requested_scope=req.scope.model_dump(),
            effective_scope=effective_scope,
            scope_fingerprint=effective_scope.get("scope_fingerprint", ""),
            requested_by=req.requested_by
        )
    elif req.report_id == "fleet_operations":
        canonical_report = await fleet_operations_handler.build_canonical_report(
            session=db,
            execution_id=execution.execution_id,
            requested_scope=req.scope.model_dump(),
            effective_scope=effective_scope,
            scope_fingerprint=effective_scope.get("scope_fingerprint", ""),
            requested_by=req.requested_by
        )
    elif req.report_id == "site_comparison":
        canonical_report = await site_comparison_handler.build_canonical_report(
            session=db,
            execution_id=execution.execution_id,
            requested_scope=req.scope.model_dump(),
            effective_scope=effective_scope,
            scope_fingerprint=effective_scope.get("scope_fingerprint", ""),
            requested_by=req.requested_by
        )
    elif req.report_id == "dispatch_optimization":
        canonical_report = await dispatch_optimization_handler.build_canonical_report(
            session=db,
            execution_id=execution.execution_id,
            requested_scope=req.scope.model_dump(),
            effective_scope=effective_scope,
            scope_fingerprint=effective_scope.get("scope_fingerprint", ""),
            requested_by=req.requested_by
        )
    elif req.report_id == "operational_intelligence":
        canonical_report = await operational_intelligence_handler.build_canonical_report(
            session=db,
            execution_id=execution.execution_id,
            requested_scope=req.scope.model_dump(),
            effective_scope=effective_scope,
            scope_fingerprint=effective_scope.get("scope_fingerprint", ""),
            requested_by=req.requested_by
        )
    elif req.report_id == "predictive_intelligence":
        canonical_report = await predictive_intelligence_handler.build_canonical_report(
            session=db,
            execution_id=execution.execution_id,
            requested_scope=req.scope.model_dump(),
            effective_scope=effective_scope,
            scope_fingerprint=effective_scope.get("scope_fingerprint", ""),
            requested_by=req.requested_by
        )
    elif req.report_id == "action_execution":
        canonical_report = await action_execution_handler.build_canonical_report(
            session=db,
            execution_id=execution.execution_id,
            requested_scope=req.scope.model_dump(),
            effective_scope=effective_scope,
            scope_fingerprint=effective_scope.get("scope_fingerprint", ""),
            requested_by=req.requested_by
        )
    elif req.report_id == "alerts_incidents":
        canonical_report = await alerts_incidents_handler.build_canonical_report(
            session=db,
            execution_id=execution.execution_id,
            requested_scope=req.scope.model_dump(),
            effective_scope=effective_scope,
            scope_fingerprint=effective_scope.get("scope_fingerprint", ""),
            requested_by=req.requested_by
        )
    elif req.report_id == "timeline_operations":
        canonical_report = await timeline_operations_handler.build_canonical_report(
            session=db,
            execution_id=execution.execution_id,
            requested_scope=req.scope.model_dump(),
            effective_scope=effective_scope,
            scope_fingerprint=effective_scope.get("scope_fingerprint", ""),
            requested_by=req.requested_by
        )
    elif req.report_id == "erp_import_audit":
        canonical_report = await erp_import_audit_handler.build_canonical_report(
            session=db,
            execution_id=execution.execution_id,
            requested_scope=req.scope.model_dump(),
            effective_scope=effective_scope,
            scope_fingerprint=effective_scope.get("scope_fingerprint", ""),
            requested_by=req.requested_by
        )
    elif req.report_id == "erp_data_explorer":
        canonical_report = await erp_data_explorer_handler.build_canonical_report(
            session=db,
            execution_id=execution.execution_id,
            requested_scope=req.scope.model_dump(),
            effective_scope=effective_scope,
            scope_fingerprint=effective_scope.get("scope_fingerprint", ""),
            requested_by=req.requested_by
        )






    elif req.report_id == "dispatch_analysis":
        canonical_report = await dispatch_handler.build_canonical_report(
            session=db,
            execution_id=execution.execution_id,
            requested_scope=req.scope.model_dump(),
            effective_scope=effective_scope,
            requested_by=req.requested_by
        )
    else:
        canonical_report = await dispatch_handler.build_canonical_report(
            session=db,
            execution_id=execution.execution_id,
            requested_scope=req.scope.model_dump(),
            effective_scope=effective_scope,
            requested_by=req.requested_by
        )








    if hasattr(canonical_report, "status") and canonical_report.status:
        execution.status = canonical_report.status.value if hasattr(canonical_report.status, "value") else str(canonical_report.status)
        execution.record_count = getattr(canonical_report, "record_count", execution.record_count)
        await db.commit()

    # Render into JSON, XLSX, and PDF formats

    json_bytes = JSONReportRenderer.render(canonical_report)
    xlsx_bytes = XLSXReportRenderer.render(canonical_report)
    pdf_bytes = PDFReportRenderer.render(canonical_report)

    # Save artifacts into storage/reports/{execution_id}/
    ReportArtifactStorage.save_artifacts(
        execution_id=execution.execution_id,
        artifacts={
            "json": json_bytes,
            "xlsx": xlsx_bytes,
            "pdf": pdf_bytes
        }
    )

    return ReportExecutionResponse(
        execution_id=execution.execution_id,
        report_id=execution.report_id,
        report_type=execution.report_type,
        format=ReportFormat(execution.format),
        requested_by=execution.requested_by,
        requested_at=execution.requested_at,
        requested_scope=execution.requested_scope,
        effective_scope=effective_scope,
        scope_fingerprint=execution.scope_fingerprint,
        scope_validation_status=ScopeValidationStatus(execution.scope_validation_status),
        record_count=execution.record_count,
        dataset_id=execution.dataset_id,
        status=ReportStatus(execution.status)
    )


@reports_router.post("/generate-async", response_model=ReportExecutionResponse, status_code=status.HTTP_202_ACCEPTED)
async def generate_report_async(
    req: ReportRequestDTO,
    background_tasks: BackgroundTasks,
    request: Request = None,
    db: AsyncSession = Depends(get_db_session)
):
    client_ip = request.client.host if request and request.client else "127.0.0.1"
    key = f"rate_limit:gen_async:{req.requested_by}:{client_ip}"
    allowed, retry_after = SecurityRateLimiter.check_rate_limit(
        key=key,
        max_requests=settings.REPORT_GENERATE_RATE_LIMIT_PER_MINUTE,
        window_seconds=60
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMIT_EXCEEDED", "message": "Async report generation rate limit exceeded. Please try again later."},
            headers={"Retry-After": str(retry_after)}
        )

    definition = ReportRegistry.get(req.report_id)

    if not definition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "REPORT_NOT_FOUND", "message": f"Report ID '{req.report_id}' is not registered."}
        )

    is_valid, effective_scope, error_code = await scope_resolver.resolve_and_validate_scope(
        session=db,
        raw_scope=req.scope.model_dump()
    )


    if not is_valid:
        await report_service.create_execution_record(
            session=db,
            report_id=req.report_id,
            report_type=definition.source_service,
            format=req.format.value,
            requested_by=req.requested_by,
            requested_scope=req.scope.model_dump(),
            effective_scope={},
            scope_fingerprint="",
            validation_status=ScopeValidationStatus.INVALID_SCOPE.value,
            record_count=0,
            status=ReportStatus.SCOPE_VALIDATION_FAILED.value,
            error_code=error_code or "REPORT_SCOPE_VALIDATION_FAILED",
            error_message="The requested report scope is invalid or unauthorized."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "REPORT_SCOPE_VALIDATION_FAILED",
                "message": "The requested report scope is invalid or unauthorized.",
                "reason": error_code
            }
        )

    record_count = effective_scope.get("record_count", 0)

    # Initial state QUEUED
    execution = await report_service.create_execution_record(
        session=db,
        report_id=req.report_id,
        report_type=definition.source_service,
        format=req.format.value,
        requested_by=req.requested_by,
        requested_scope=req.scope.model_dump(),
        effective_scope=effective_scope,
        scope_fingerprint=effective_scope.get("scope_fingerprint", ""),
        validation_status=ScopeValidationStatus.VALIDATED.value,
        record_count=record_count,
        dataset_id=effective_scope.get("resolved_dataset_id"),
        status=ReportStatus.QUEUED.value
    )

    # Offload execution to BackgroundTasks
    background_tasks.add_task(
        ReportBackgroundWorker.process_report_task,
        execution_id=execution.execution_id,
        report_id=req.report_id,
        requested_scope=req.scope.model_dump(),
        effective_scope=effective_scope,
        requested_by=req.requested_by
    )

    return ReportExecutionResponse(
        execution_id=execution.execution_id,
        report_id=execution.report_id,
        report_type=execution.report_type,
        format=ReportFormat(execution.format),
        requested_by=execution.requested_by,
        requested_at=execution.requested_at,
        requested_scope=execution.requested_scope,
        effective_scope=effective_scope,
        scope_fingerprint=execution.scope_fingerprint,
        scope_validation_status=ScopeValidationStatus(execution.scope_validation_status),
        record_count=execution.record_count,
        dataset_id=execution.dataset_id,
        status=ReportStatus.QUEUED
    )


@reports_router.get("/metrics")
async def get_reporting_metrics():
    payload, content_type = ReportingMetricsCollector.get_metrics_payload()
    return Response(content=payload, media_type=content_type)


@reports_router.get("/executions/{execution_id}/status", response_model=ReportExecutionResponse)
async def get_execution_status(
    execution_id: str,
    db: AsyncSession = Depends(get_db_session)
):
    query = select(ReportExecutionAudit).where(ReportExecutionAudit.execution_id == execution_id)
    result = await db.execute(query)
    execution = result.scalars().first()
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "REPORT_EXECUTION_NOT_FOUND", "message": f"Execution ID '{execution_id}' not found."}
        )

    return ReportExecutionResponse(
        execution_id=execution.execution_id,
        report_id=execution.report_id,
        report_type=execution.report_type,
        format=ReportFormat(execution.format),
        requested_by=execution.requested_by,
        requested_at=execution.requested_at,
        requested_scope=execution.requested_scope,
        effective_scope=execution.effective_scope,
        scope_fingerprint=execution.scope_fingerprint,
        scope_validation_status=ScopeValidationStatus(execution.scope_validation_status),
        record_count=execution.record_count,
        dataset_id=execution.dataset_id,
        status=ReportStatus(execution.status),
        error_code=execution.error_code,
        error_message=execution.error_message
    )



@reports_router.get("/executions", response_model=List[ReportExecutionResponse])

async def list_executions(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db_session)
):
    executions = await report_service.list_executions(db, limit=limit, offset=offset)
    return [
        ReportExecutionResponse(
            execution_id=e.execution_id,
            report_id=e.report_id,
            report_type=e.report_type,
            format=ReportFormat(e.format),
            requested_by=e.requested_by,
            requested_at=e.requested_at,
            requested_scope=e.requested_scope,
            effective_scope=e.effective_scope,
            scope_fingerprint=e.scope_fingerprint,
            scope_validation_status=ScopeValidationStatus(e.scope_validation_status),
            record_count=e.record_count,
            dataset_id=e.dataset_id,
            status=ReportStatus(e.status)
        )
        for e in executions
    ]


@reports_router.get("/executions/{execution_id}/download")
async def download_report_artifact(
    execution_id: str,
    format: str = "pdf",
    token: Optional[str] = None,
    user_id: Optional[str] = None,
    request: Request = None,
    db: AsyncSession = Depends(get_db_session)
):
    client_ip = request.client.host if request and request.client else "127.0.0.1"
    rate_key = f"rate_limit:download:{user_id or 'anon'}:{client_ip}"
    allowed, retry_after = SecurityRateLimiter.check_rate_limit(
        key=rate_key,
        max_requests=settings.REPORT_DOWNLOAD_RATE_LIMIT_PER_MINUTE,
        window_seconds=60
    )
    if not allowed:
        ReportingMetricsCollector.record_rate_limit(endpoint="/download")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMIT_EXCEEDED", "message": "Report download rate limit exceeded. Please try again later."},
            headers={"Retry-After": str(retry_after)}
        )

    valid_formats = {"pdf": "application/pdf", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "json": "application/json"}
    fmt = format.lower()
    if fmt not in valid_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_REPORT_FORMAT", "message": f"Format '{format}' is invalid. Supported: pdf, xlsx, json"}
        )

    # Cryptographic Download Token Validation (if token parameter provided)
    if token is not None:
        is_valid_token = DownloadTokenManager.verify_download_token(
            token=token,
            expected_execution_id=execution_id,
            expected_format=fmt,
            expected_user_id=user_id
        )
        if not is_valid_token:
            ReportingMetricsCollector.record_security_denial(reason="INVALID_DOWNLOAD_TOKEN")
            ReportingMetricsCollector.record_download(format_str=fmt, status_str="DENIED")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": "INVALID_DOWNLOAD_TOKEN", "message": "Download token is invalid, expired, or scoped to a different execution/user."}
            )

    try:
        filepath = ReportArtifactStorage.get_artifact_path(execution_id, fmt)
        filename = f"dispatch_analysis_{execution_id}.{fmt}"
        ReportingMetricsCollector.record_download(format_str=fmt, status_str="SUCCESS")
        return FileResponse(
            path=filepath,
            media_type=valid_formats[fmt],
            filename=filename,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, private",
                "X-Content-Type-Options": "nosniff"
            }
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "REPORT_ARTIFACT_NOT_FOUND", "message": f"Artifact for execution '{execution_id}' in format '{fmt}' not found."}
        )


@reports_router.post("/executions/{execution_id}/download-token")
async def create_download_token(
    execution_id: str,
    format: str = "pdf",
    user_id: str = "SYSTEM",
    db: AsyncSession = Depends(get_db_session)
):
    query = select(ReportExecutionAudit).where(ReportExecutionAudit.execution_id == execution_id)
    result = await db.execute(query)
    execution = result.scalars().first()
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "REPORT_EXECUTION_NOT_FOUND", "message": f"Execution ID '{execution_id}' not found."}
        )

    # Ownership isolation check
    if execution.requested_by != user_id and user_id != "SYSTEM" and user_id != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "ACCESS_DENIED", "message": f"User '{user_id}' is not authorized to access execution '{execution_id}'."}
        )

    download_token = DownloadTokenManager.create_download_token(
        execution_id=execution_id,
        user_id=user_id,
        format_ext=format
    )

    return {
        "execution_id": execution_id,
        "format": format.lower(),
        "download_token": download_token,
        "expires_in_minutes": settings.DOWNLOAD_TOKEN_EXPIRE_MINUTES
    }




@reports_router.post("/purge-expired", status_code=status.HTTP_200_OK)
async def purge_expired_report_artifacts(
    db: AsyncSession = Depends(get_db_session)
):
    result = await report_service.purge_expired_artifacts(db)
    return result


@reports_router.get("/metrics")
async def get_reporting_metrics():
    payload, content_type = ReportingMetricsCollector.get_metrics_payload()
    return Response(content=payload, media_type=content_type)



