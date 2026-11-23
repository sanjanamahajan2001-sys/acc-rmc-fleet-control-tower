"""
ERP API Router Module
Aggregates upload, job management, progress SSE, statistics, audit, and explorer endpoints.
"""

from fastapi import APIRouter

from app.modules.erp.api.admin import router as admin_router
from app.modules.erp.api.audit import router as audit_router
from app.modules.erp.api.explorer import router as explorer_router
from app.modules.erp.api.jobs import router as jobs_router
from app.modules.erp.api.progress import router as progress_router
from app.modules.erp.api.statistics import router as statistics_router
from app.modules.erp.api.upload import router as upload_router

erp_router = APIRouter(prefix="/erp", tags=["ERP Platform Services"])

# Register sub-routers under /api/v1/erp
erp_router.include_router(upload_router)
erp_router.include_router(jobs_router)
erp_router.include_router(progress_router)
erp_router.include_router(statistics_router)
erp_router.include_router(audit_router)
erp_router.include_router(explorer_router)
erp_router.include_router(admin_router)
