"""
WS-07.5 Operational Alert Repository Layer.
Provides database access abstraction for listing, summarizing, retrieving, acknowledging, resolving, and archiving operational alerts.
Updated in WS-07.9 for RESOLVED -> ARCHIVED lifecycle transition.
"""
from uuid import UUID
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import text, select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.operational_dashboard.widgets.alerts.models import OperationalAlertModel

logger = get_logger(__name__)

class OperationalAlertRepository:
    """
    PostgreSQL SQLAlchemy Async Repository for `operational_alerts` table.
    Enforces scope isolation, server-side pagination, and deterministic sorting.
    """

    @classmethod
    async def list_alerts(
        cls,
        session: AsyncSession,
        plant_id: str = "ALL",
        customer_id: str = "ALL",
        dataset_id: Optional[str] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        alert_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[OperationalAlertModel], int]:
        """
        List operational alerts matching filter criteria with server-side pagination and deterministic sorting.
        Ordering: detected_at DESC, id ASC
        """
        query = select(OperationalAlertModel)

        # Scope Filtering
        if plant_id != "ALL":
            query = query.where(OperationalAlertModel.plant_id == plant_id)
        if customer_id != "ALL":
            query = query.where(OperationalAlertModel.customer_id == customer_id)
        if dataset_id:
            query = query.where(OperationalAlertModel.dataset_id == dataset_id)
        if status:
            query = query.where(OperationalAlertModel.status == status)
        if severity:
            query = query.where(OperationalAlertModel.severity == severity)
        if alert_type:
            query = query.where(OperationalAlertModel.alert_type == alert_type)

        # Count total matching rows before pagination
        count_query = select(func.count()).select_from(query.subquery())
        total_res = await session.execute(count_query)
        total_count = total_res.scalar_one()

        # Deterministic sorting & pagination
        offset = (page - 1) * page_size
        query = query.order_by(
            OperationalAlertModel.detected_at.desc(),
            OperationalAlertModel.id.asc()
        ).limit(page_size).offset(offset)

        res = await session.execute(query)
        alerts = res.scalars().all()

        return list(alerts), total_count

    @classmethod
    async def get_alert_by_id(
        cls,
        session: AsyncSession,
        alert_id: UUID,
    ) -> Optional[OperationalAlertModel]:
        """Fetch a single alert by UUID."""
        res = await session.execute(
            select(OperationalAlertModel).where(OperationalAlertModel.id == alert_id)
        )
        return res.scalar_one_or_none()

    @classmethod
    async def get_summary_counts(
        cls,
        session: AsyncSession,
        plant_id: str = "ALL",
        customer_id: str = "ALL",
        dataset_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Calculate summary metric counts under active filters using a single aggregation query.
        """
        query = select(
            func.count().label("total"),
            func.count().filter(OperationalAlertModel.status == "OPEN").label("open_count"),
            func.count().filter(OperationalAlertModel.status == "ACKNOWLEDGED").label("acknowledged_count"),
            func.count().filter(OperationalAlertModel.status == "RESOLVED").label("resolved_count"),
            func.count().filter(OperationalAlertModel.status == "ARCHIVED").label("archived_count"),
            func.count().filter((OperationalAlertModel.severity == "CRITICAL") & (OperationalAlertModel.status == "OPEN")).label("critical_count"),
            func.count().filter((OperationalAlertModel.severity == "WARNING") & (OperationalAlertModel.status == "OPEN")).label("warning_count"),
            func.count().filter((OperationalAlertModel.severity == "INFO") & (OperationalAlertModel.status == "OPEN")).label("info_count"),
            func.count().filter((OperationalAlertModel.severity == "CRITICAL") & (OperationalAlertModel.status.in_(["OPEN", "ACKNOWLEDGED"]))).label("active_critical_count"),
            func.count().filter((OperationalAlertModel.severity == "WARNING") & (OperationalAlertModel.status.in_(["OPEN", "ACKNOWLEDGED"]))).label("active_warning_count"),
            func.count().filter((OperationalAlertModel.severity == "INFO") & (OperationalAlertModel.status.in_(["OPEN", "ACKNOWLEDGED"]))).label("active_info_count"),
        ).select_from(OperationalAlertModel)

        if plant_id != "ALL":
            query = query.where(OperationalAlertModel.plant_id == plant_id)
        if customer_id != "ALL":
            query = query.where(OperationalAlertModel.customer_id == customer_id)
        if dataset_id:
            query = query.where(OperationalAlertModel.dataset_id == dataset_id)

        res = await session.execute(query)
        row = res.fetchone()

        if not row:
            return {
                "total": 0, "open_count": 0, "acknowledged_count": 0,
                "resolved_count": 0, "archived_count": 0, "critical_count": 0, "warning_count": 0, "info_count": 0,
                "active_critical_count": 0, "active_warning_count": 0, "active_info_count": 0
            }

        return {
            "total": row.total or 0,
            "open_count": row.open_count or 0,
            "acknowledged_count": row.acknowledged_count or 0,
            "resolved_count": row.resolved_count or 0,
            "archived_count": row.archived_count or 0,
            "critical_count": row.critical_count or 0,
            "warning_count": row.warning_count or 0,
            "info_count": row.info_count or 0,
            "active_critical_count": row.active_critical_count or 0,
            "active_warning_count": row.active_warning_count or 0,
            "active_info_count": row.active_info_count or 0,
        }

    @classmethod
    async def get_top_categories(
        cls,
        session: AsyncSession,
        plant_id: str = "ALL",
        customer_id: str = "ALL",
        dataset_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Query top active alert categories grouped by alert_type."""
        query = select(
            OperationalAlertModel.alert_type,
            OperationalAlertModel.severity,
            func.count(OperationalAlertModel.id).label("count")
        ).where(OperationalAlertModel.status.in_(["OPEN", "ACKNOWLEDGED"]))

        if plant_id != "ALL":
            query = query.where(OperationalAlertModel.plant_id == plant_id)
        if customer_id != "ALL":
            query = query.where(OperationalAlertModel.customer_id == customer_id)
        if dataset_id:
            query = query.where(OperationalAlertModel.dataset_id == dataset_id)

        query = query.group_by(OperationalAlertModel.alert_type, OperationalAlertModel.severity).order_by(text("count DESC")).limit(limit)

        res = await session.execute(query)
        rows = res.fetchall()
        return [{"alert_type": r.alert_type, "severity": r.severity, "count": r.count} for r in rows]

    @classmethod
    async def get_plant_concentration(
        cls,
        session: AsyncSession,
        plant_id: str = "ALL",
        customer_id: str = "ALL",
        dataset_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Query active alert concentration grouped by plant_id."""
        query = select(
            OperationalAlertModel.plant_id,
            func.count().filter(OperationalAlertModel.severity == "CRITICAL").label("critical_count"),
            func.count().filter(OperationalAlertModel.severity == "WARNING").label("warning_count"),
            func.count().label("total_count")
        ).where(OperationalAlertModel.status.in_(["OPEN", "ACKNOWLEDGED"]))

        if plant_id != "ALL":
            query = query.where(OperationalAlertModel.plant_id == plant_id)
        if customer_id != "ALL":
            query = query.where(OperationalAlertModel.customer_id == customer_id)
        if dataset_id:
            query = query.where(OperationalAlertModel.dataset_id == dataset_id)

        query = query.group_by(OperationalAlertModel.plant_id).order_by(text("total_count DESC")).limit(limit)

        res = await session.execute(query)
        rows = res.fetchall()
        return [{
            "group_type": "PLANT",
            "group_code": r.plant_id,
            "group_name": r.plant_id,
            "critical_count": r.critical_count or 0,
            "warning_count": r.warning_count or 0,
            "total_count": r.total_count or 0
        } for r in rows]

    @classmethod
    async def get_customer_concentration(
        cls,
        session: AsyncSession,
        plant_id: str = "ALL",
        customer_id: str = "ALL",
        dataset_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Query active alert concentration grouped by customer_id with effective customer display name."""
        from app.modules.erp.models import Customer, CustomerDisplayOverride
        from app.modules.settings.services.customer_override_service import CustomerDisplayOverrideService

        eff_name = CustomerDisplayOverrideService.get_effective_name_expression()

        query = select(
            OperationalAlertModel.customer_id,
            Customer.code.label("customer_code"),
            eff_name.label("effective_customer_name"),
            func.count().filter(OperationalAlertModel.severity == "CRITICAL").label("critical_count"),
            func.count().filter(OperationalAlertModel.severity == "WARNING").label("warning_count"),
            func.count().label("total_count")
        ).outerjoin(
            Customer, OperationalAlertModel.customer_id == Customer.code
        ).outerjoin(
            CustomerDisplayOverride, CustomerDisplayOverride.customer_id == Customer.id
        ).where(OperationalAlertModel.status.in_(["OPEN", "ACKNOWLEDGED"]))

        if plant_id != "ALL":
            query = query.where(OperationalAlertModel.plant_id == plant_id)
        if customer_id != "ALL":
            query = query.where(OperationalAlertModel.customer_id == customer_id)
        if dataset_id:
            query = query.where(OperationalAlertModel.dataset_id == dataset_id)

        query = query.group_by(
            OperationalAlertModel.customer_id,
            Customer.code,
            Customer.name,
            CustomerDisplayOverride.override_name
        ).order_by(text("total_count DESC")).limit(limit)

        res = await session.execute(query)
        rows = res.fetchall()
        return [{
            "group_type": "CUSTOMER",
            "group_code": r.customer_id,
            "group_name": r.effective_customer_name or r.customer_id or "UNSPECIFIED CUSTOMER",
            "critical_count": r.critical_count or 0,
            "warning_count": r.warning_count or 0,
            "total_count": r.total_count or 0
        } for r in rows]

    @classmethod
    async def get_priority_unresolved_alerts(
        cls,
        session: AsyncSession,
        plant_id: str = "ALL",
        customer_id: str = "ALL",
        dataset_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[OperationalAlertModel]:
        """
        Query top priority unresolved alerts (status IN ('OPEN', 'ACKNOWLEDGED')).
        Deterministic Ordering: CRITICAL > WARNING > INFO, then detected_at ASC, then id ASC.
        """
        severity_order = text(
            "CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'WARNING' THEN 2 WHEN 'INFO' THEN 3 ELSE 4 END ASC"
        )
        query = select(OperationalAlertModel).where(
            OperationalAlertModel.status.in_(["OPEN", "ACKNOWLEDGED"])
        )

        if plant_id != "ALL":
            query = query.where(OperationalAlertModel.plant_id == plant_id)
        if customer_id != "ALL":
            query = query.where(OperationalAlertModel.customer_id == customer_id)
        if dataset_id:
            query = query.where(OperationalAlertModel.dataset_id == dataset_id)

        query = query.order_by(
            severity_order,
            OperationalAlertModel.detected_at.asc(),
            OperationalAlertModel.id.asc()
        ).limit(limit)

        res = await session.execute(query)
        return list(res.scalars().all())

    @classmethod
    async def acknowledge_alert(
        cls,
        session: AsyncSession,
        alert_id: UUID,
        acknowledged_by: str,
        notes: Optional[str] = None,
    ) -> Optional[OperationalAlertModel]:
        """
        Atomic lifecycle transition OPEN -> ACKNOWLEDGED.
        Returns None if alert not found or state transition is invalid.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            update(OperationalAlertModel)
            .where(
                (OperationalAlertModel.id == alert_id) &
                (OperationalAlertModel.status == "OPEN")
            )
            .values(
                status="ACKNOWLEDGED",
                acknowledged_at=now,
                acknowledged_by=acknowledged_by,
                acknowledgement_notes=notes,
                updated_at=now,
            )
            .execution_options(synchronize_session="fetch")
        )
        res = await session.execute(stmt)
        if res.rowcount == 0:
            return None

        await session.commit()
        return await cls.get_alert_by_id(session, alert_id)

    @classmethod
    async def resolve_alert(
        cls,
        session: AsyncSession,
        alert_id: UUID,
        resolved_by: str,
        resolution_reason: str,
    ) -> Optional[OperationalAlertModel]:
        """
        Atomic lifecycle transition OPEN/ACKNOWLEDGED -> RESOLVED.
        Returns None if alert not found or state transition is invalid.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            update(OperationalAlertModel)
            .where(
                (OperationalAlertModel.id == alert_id) &
                (OperationalAlertModel.status.in_(["OPEN", "ACKNOWLEDGED"]))
            )
            .values(
                status="RESOLVED",
                resolved_at=now,
                resolved_by=resolved_by,
                resolution_reason=resolution_reason,
                updated_at=now,
            )
            .execution_options(synchronize_session="fetch")
        )
        res = await session.execute(stmt)
        if res.rowcount == 0:
            return None

        await session.commit()
        return await cls.get_alert_by_id(session, alert_id)

    @classmethod
    async def archive_resolved_alerts(
        cls,
        session: AsyncSession,
        retention_hours: float = 24.0,
    ) -> int:
        """
        Transition RESOLVED alerts older than retention_hours to ARCHIVED state.
        Sets archived_at timestamp. NO physical DELETE occurs.
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=retention_hours)
        stmt = (
            update(OperationalAlertModel)
            .where(
                (OperationalAlertModel.status == "RESOLVED") &
                (OperationalAlertModel.resolved_at <= cutoff)
            )
            .values(
                status="ARCHIVED",
                archived_at=now,
                updated_at=now,
            )
            .execution_options(synchronize_session="fetch")
        )
        res = await session.execute(stmt)
        archived_count = res.rowcount
        if archived_count > 0:
            await session.commit()
            logger.info(f"[WS-07.9] Archived {archived_count} RESOLVED alerts older than {retention_hours} hours")
        return archived_count
