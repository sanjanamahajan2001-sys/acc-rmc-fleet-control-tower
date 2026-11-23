"""
KPI Subsystem SQL Repository
Workstream 2.2 Backend Repository
"""

from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.erp.models import Trip, Dispatch


class KPIRepository:
    """PostgreSQL Canonical SQL Queries for KPI Metrics."""

    @staticmethod
    async def get_total_dispatches(session: AsyncSession, filters: dict[str, Any]) -> int:
        stmt = select(func.count(Trip.id))
        result = await session.execute(stmt)
        return result.scalar() or 0
