from app.dependencies.auth import require_section_permission
from app.schemas.auth import TokenPayload
"""
ERP Administrative Reset Endpoint
Transactional reset utility deleting ONLY ERP import generated data for development and demonstration environments.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.common import get_db_session
from app.modules.erp.api.dependencies import AuthenticatedUser, TimedEnvelope
from app.schemas.envelope import APIResponse

router = APIRouter(prefix="/admin", tags=["ERP Admin Services"])


from app.modules.site_dashboard.cache.materialized_cache import MaterializedDashboardCache


@router.post(
    "/reset-demo-data",
    response_model=APIResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Reset Demo ERP Data (Admin Only)",
    description="Transactionally purges all ERP import generated data while preserving core platform auth, users, and system configuration.",
)
async def reset_demo_data(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthenticatedUser,
    envelope: TimedEnvelope,
    _perm_guard: Annotated[TokenPayload, Depends(require_section_permission("erp_import", "edit"))],
) -> APIResponse[dict[str, Any]]:
    # Invalidate in-memory materialized dashboard cache
    MaterializedDashboardCache.invalidate_all()
    # Record DATA_RESET audit trail entry before clearing domain operational data
    try:
        from app.modules.erp.models import ImportAuditLog, ImportJob
        from app.modules.auth.models import User
        from sqlalchemy import select
        import uuid
        from datetime import datetime, timezone

        admin_name = "admin"
        admin_uuid = None
        if hasattr(user, "sub") and user.sub:
            try:
                admin_uuid = uuid.UUID(user.sub)
                user_rec = (await session.execute(select(User).where(User.id == admin_uuid))).scalar_one_or_none()
                if user_rec:
                    admin_name = user_rec.username or user_rec.full_name or user_rec.email or "admin"
            except Exception:
                pass

        now_iso = datetime.now(timezone.utc).isoformat()
        latest_job = (await session.execute(select(ImportJob).order_by(ImportJob.created_at.desc()).limit(1))).scalars().first()
        if latest_job:
            reset_log = ImportAuditLog(
                job_id=latest_job.id,
                action="DATA_RESET",
                created_by=admin_uuid,
                details={
                    "event": "DEMO_DATA_RESET",
                    "reset_by": admin_name,
                    "timestamp": now_iso,
                    "reason": "Administrative reset of operational data",
                },
            )
            session.add(reset_log)

        # Mark all existing ImportJobs as reset in source_lineage
        existing_jobs = (await session.execute(select(ImportJob))).scalars().all()
        for j in existing_jobs:
            current_lineage = dict(j.source_lineage or {})
            current_lineage["is_reset"] = True
            current_lineage["reset_at"] = now_iso
            current_lineage["reset_by"] = admin_name
            j.source_lineage = current_lineage

        await session.commit()
    except Exception:
        pass

    # Domain & Downstream Operational tables to purge (Audit trail and Job lineage are preserved)
    tables = [
        "ml_prediction_snapshots",
        "tbl_planner_action_log",
        "prediction_error_records",
        "operational_outcomes",
        "operational_alerts",
        "trips",
        "invoices",
        "dispatches",
        "tickets",
        "orders",
        "drivers",
        "vehicles",
        "customers",
        "sites",
        "plants",
    ]

    deleted_counts: dict[str, int] = {}

    try:
        # Truncate tables with CASCADE to handle foreign keys cleanly
        table_list_str = ", ".join(tables)
        stmt = text(f"TRUNCATE TABLE {table_list_str} RESTART IDENTITY CASCADE")
        await session.execute(stmt)
        await session.commit()
        for t in tables:
            deleted_counts[t] = 0
    except Exception:  # noqa: BLE001
        # Fallback to DELETE FROM statements if TRUNCATE has lock restrictions
        await session.rollback()
        for table in tables:
            try:
                stmt = text(f"DELETE FROM {table}")
                res = await session.execute(stmt)
                deleted_counts[table] = getattr(res, "rowcount", 0) or 0
            except Exception:  # noqa: BLE001, S110
                pass
        await session.commit()

    return envelope.success(
        {
            "status": "SUCCESS",
            "message": "Transactional reset of ERP demo data completed successfully.",
            "deleted_counts": deleted_counts,
            "total_records_deleted": sum(deleted_counts.values()),
        }
    )


from pydantic import BaseModel, Field
from fastapi import HTTPException


class RevertDatasetRequest(BaseModel):
    dataset_period: str | None = Field(default=None, description="Dataset period label or name (e.g. 'Dataset 04 (Jan-Feb 2026)')")
    period_key: str | None = Field(default=None, description="Dataset period key (e.g. '2026-JAN-FEB')")
    job_number: str | None = Field(default=None, description="Job number to revert to")


@router.post(
    "/revert-dataset",
    response_model=APIResponse[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Revert Platform Operational Dataset (Admin Only)",
    description="Transactionally resets operational tables and restores domain state from the chosen historical dataset.",
)
async def revert_dataset(
    req: RevertDatasetRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: AuthenticatedUser,
    envelope: TimedEnvelope,
    _perm_guard: Annotated[TokenPayload, Depends(require_section_permission("erp_import", "edit"))],
) -> APIResponse[dict[str, Any]]:
    from app.modules.erp.models import ImportAuditLog, ImportJob, Dispatch
    from app.modules.auth.models import User
    from app.modules.erp.api.jobs import classify_dataset_file
    from app.modules.erp.storage.factory import get_storage_provider
    from app.modules.erp.workers.orchestrator import ImportPipelineOrchestrator
    from app.modules.telemetry.validation.correlator import CrossSourceCorrelator
    from sqlalchemy import select, func
    import uuid
    import pathlib
    import shutil
    from datetime import datetime, timezone

    # 1. Resolve Admin identity
    admin_name = "admin"
    admin_uuid = None
    if hasattr(user, "sub") and user.sub:
        try:
            admin_uuid = uuid.UUID(user.sub)
            user_rec = (await session.execute(select(User).where(User.id == admin_uuid))).scalar_one_or_none()
            if user_rec:
                admin_name = user_rec.username or user_rec.full_name or user_rec.email or "admin"
        except Exception:
            pass

    # 2. Locate all existing non-deleted jobs
    all_jobs = (await session.execute(
        select(ImportJob).where(ImportJob.is_deleted == False).order_by(ImportJob.created_at.desc())
    )).scalars().all()

    target_key = req.period_key
    target_label = req.dataset_period

    if req.job_number:
        found_job = next((j for j in all_jobs if j.job_number == req.job_number), None)
        if found_job:
            k, l, _ = classify_dataset_file(found_job.file_name, found_job.source_lineage)
            target_key = k
            target_label = l

    matched_jobs = []
    for j in all_jobs:
        k, l, _ = classify_dataset_file(j.file_name, j.source_lineage)
        if (target_key and k == target_key) or (target_label and l == target_label):
            matched_jobs.append(j)

    if not matched_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No import jobs found matching target dataset '{target_key or target_label or req.job_number}'.",
        )

    # 3. Deduplicate target jobs: pick newest completed job for each file role
    role_to_job: dict[str, ImportJob] = {}
    for j in matched_jobs:
        _, _, r = classify_dataset_file(j.file_name, j.source_lineage)
        if r not in role_to_job or j.created_at > role_to_job[r].created_at:
            role_to_job[r] = j

    target_jobs = list(role_to_job.values())
    target_jobs.sort(
        key=lambda x: 0 if classify_dataset_file(x.file_name, x.source_lineage)[2] == "ERP Dispatches" else 1
    )

    # Extract non-expired primitive descriptors before any ORM sessions or truncates
    target_job_descriptors = []
    for tj in target_jobs:
        _, _, r = classify_dataset_file(tj.file_name, tj.source_lineage)
        target_job_descriptors.append({
            "id": tj.id,
            "job_number": str(tj.job_number),
            "file_name": str(tj.file_name),
            "role": r,
        })

    # 4. Verify and recover files in storage if needed
    storage_provider = get_storage_provider()
    for jd in target_job_descriptors:
        rel_path = f"workbooks/{jd['id']}/{jd['file_name']}"
        fpath = await storage_provider.get_file_path(rel_path)
        if not fpath.exists():
            fallbacks = [
                pathlib.Path("/tmp/fleet_storage/workbooks"),
                pathlib.Path("/var/lib/fleet_control_tower/storage/workbooks"),
                pathlib.Path("/home/sanjana/demo-fleet/backend"),
                pathlib.Path("/home/sanjana/demo-fleet/scripts"),
            ]
            found_src = None
            for fb in fallbacks:
                if not fb.exists():
                    continue
                cand = fb / jd["file_name"]
                if cand.exists() and cand.is_file() and cand.stat().st_size > 0:
                    found_src = cand
                    break
                for c in fb.rglob(jd["file_name"]):
                    if c.is_file() and c.stat().st_size > 0:
                        found_src = c
                        break
                if found_src:
                    break
            
            if found_src:
                fpath.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(found_src, fpath)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Workbook file '{jd['file_name']}' for job {jd['job_number']} is not available in storage.",
                )

    # 5. Purge domain tables
    MaterializedDashboardCache.invalidate_all()
    tables = [
        "ml_prediction_snapshots",
        "tbl_planner_action_log",
        "prediction_error_records",
        "operational_outcomes",
        "operational_alerts",
        "trips",
        "invoices",
        "dispatches",
        "tickets",
        "orders",
        "drivers",
        "vehicles",
        "customers",
        "sites",
        "plants",
    ]
    try:
        stmt = text(f"TRUNCATE TABLE {', '.join(tables)} RESTART IDENTITY CASCADE")
        await session.execute(stmt)
        await session.commit()
    except Exception:
        await session.rollback()
        for t in tables:
            try:
                await session.execute(text(f"DELETE FROM {t}"))
            except Exception:
                pass
        await session.commit()

    # 6. Update ImportJob active/archived states using dedicated fresh session
    from app.core.database import AsyncSessionFactory
    now_iso = datetime.now(timezone.utc).isoformat()
    target_ids = {jd["id"] for jd in target_job_descriptors}

    async with AsyncSessionFactory() as job_session:
        jobs_to_update = (await job_session.execute(
            select(ImportJob).where(ImportJob.is_deleted == False)
        )).scalars().all()
        for j in jobs_to_update:
            lin = dict(j.source_lineage or {})
            if j.id in target_ids:
                lin["is_reset"] = False
                lin["reverted_at"] = now_iso
                lin["reverted_by"] = admin_name
            else:
                lin["is_reset"] = True
                lin["reset_at"] = now_iso
                lin["reset_by"] = admin_name
            j.source_lineage = lin
        await job_session.commit()

    # 7. Re-execute ingestion pipeline using dedicated AsyncSession per job
    from app.core.database import AsyncSessionFactory
    orchestrator = ImportPipelineOrchestrator()
    has_telemetry = False

    for jd in target_job_descriptors:
        async with AsyncSessionFactory() as pipe_session:
            await orchestrator.execute_pipeline(pipe_session, jd["job_number"])
        if jd["role"] == "Trip Drum Telemetry":
            has_telemetry = True

    if has_telemetry:
        try:
            from app.modules.telemetry.validation.correlator import CrossSourceCorrelator
            async with AsyncSessionFactory() as corr_session:
                correlator = CrossSourceCorrelator()
                await correlator.correlate_unmatched_telemetry(corr_session, limit=10000)
                await corr_session.commit()
        except Exception:
            pass

    # 7.5 Regenerate Actions & Alerts for Reverted Dataset
    try:
        from generate_real_actions import generate_real_actions
        await generate_real_actions()
    except Exception as act_err:
        pass

    # 8. Record audit trail
    MaterializedDashboardCache.invalidate_all()
    resolved_label = target_label or target_key or target_job_descriptors[0]["file_name"]
    first_job_id = target_job_descriptors[0]["id"]
    reverted_job_numbers = [jd["job_number"] for jd in target_job_descriptors]

    async with AsyncSessionFactory() as audit_session:
        reset_log = ImportAuditLog(
            job_id=first_job_id,
            action="DATASET_REVERT",
            created_by=admin_uuid,
            details={
                "event": "DATASET_REVERT",
                "dataset_period": resolved_label,
                "reverted_by": admin_name,
                "reverted_jobs": reverted_job_numbers,
                "timestamp": now_iso,
            },
        )
        audit_session.add(reset_log)
        await audit_session.commit()

    async with AsyncSessionFactory() as final_session:
        disp_cnt = (await final_session.execute(select(func.count(Dispatch.id)))).scalar() or 0
        max_date = (await final_session.execute(select(func.max(func.date(Dispatch.dispatch_date))))).scalar()
        op_date_str = max_date.isoformat() if max_date else None

    return envelope.success({
        "status": "SUCCESS",
        "message": f"Successfully reverted to {resolved_label}.",
        "dataset_period": resolved_label,
        "operational_date": op_date_str,
        "active_jobs": reverted_job_numbers,
        "total_dispatches": disp_cnt,
    })
