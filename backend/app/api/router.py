"""
FastAPI Main Router Configuration.
Delegates router aggregation to app.api.v1.registry.v1_router.
"""
from fastapi import APIRouter
from app.api.v1.registry import v1_router

main_router = APIRouter(prefix="/demo-api")
main_router.include_router(v1_router)

fleet_router = APIRouter(prefix="/fleet-api")
fleet_router.include_router(v1_router)
