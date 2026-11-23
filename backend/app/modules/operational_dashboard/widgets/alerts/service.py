"""
WS-07.5 Operational Alert Business Service Layer.
Updated in WS-07.9 for configurable archival policy & endpoint logic.
"""
import json
from uuid import UUID
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.operational_dashboard.widgets.alerts.models import OperationalAlertModel
from app.modules.operational_dashboard.widgets.alerts.repository import OperationalAlertRepository
from app.modules.operational_dashboard.widgets.alerts.dtos import (
    AlertSeverityEnum,
    AlertStatusEnum,
    OperationalDatasetContextDTO,
    OperationalAlertItemDTO,
    AlertListResponseDTO,
    AlertSummaryDTO,
)

logger = get_logger(__name__)

# Configurable Operational Retention Policy (Default: 24 Hours)
RESOLVED_OPERATIONAL_RETENTION_HOURS: float = 24.0

class AlertService:
    """
    Business logic layer for WS-07.5 Operational Alert APIs.
    """

    @classmethod
    def _model_to_dto(cls, model: OperationalAlertModel) -> OperationalAlertItemDTO:
        """Convert OperationalAlertModel SQLAlchemy instance into OperationalAlertItemDTO cleanly."""
        evidence = model.evidence_json
        if isinstance(evidence, str):
            try:
                evidence = json.loads(evidence)
            except Exception:
                evidence = {"raw": evidence}
        elif evidence is None:
            evidence = {}

        return OperationalAlertItemDTO(
            id=model.id,
            alert_fingerprint=model.alert_fingerprint,
            alert_type=model.alert_type,
            severity=AlertSeverityEnum(model.severity),
            status=AlertStatusEnum(model.status),
            plant_id=model.plant_id,
            customer_id=model.customer_id,
            dispatch_id=model.dispatch_id,
            vehicle_id=model.vehicle_id,
            dataset_id=model.dataset_id,
            import_job_id=model.import_job_id,
            metric_name=model.metric_name,
            actual_value=float(model.actual_value),
            threshold_value=float(model.threshold_value),
            unit=model.unit,
            business_impact=model.business_impact,
            evidence_json=evidence,
            recommended_action=model.recommended_action,
            detected_at=model.detected_at,
            evaluated_at=model.evaluated_at,
            acknowledged_at=model.acknowledged_at,
            acknowledged_by=model.acknowledged_by,
            acknowledgement_notes=model.acknowledgement_notes,
            resolved_at=model.resolved_at,
            resolved_by=model.resolved_by,
            resolution_reason=model.resolution_reason,
            archived_at=model.archived_at,
            rule_version=model.rule_version,
        )

    @classmethod
    async def get_alerts_list(
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
    ) -> AlertListResponseDTO:
        """Fetch page of operational alerts as strongly typed AlertListResponseDTO."""
        page_size = min(max(1, page_size), 100) # Enforce maximum page size limit of 100
        page = max(1, page)

        effective_dataset_id = dataset_id
        if not effective_dataset_id:
            ctx = await cls.get_dataset_context(
                session=session, plant_id=plant_id, customer_id=customer_id, dataset_id=dataset_id
            )
            effective_dataset_id = ctx.dataset_id

        models, total_count = await OperationalAlertRepository.list_alerts(
            session=session,
            plant_id=plant_id,
            customer_id=customer_id,
            dataset_id=effective_dataset_id,
            status=status,
            severity=severity,
            alert_type=alert_type,
            page=page,
            page_size=page_size,
        )

        items_dtos = [cls._model_to_dto(m) for m in models]
        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

        return AlertListResponseDTO(
            items=items_dtos,
            total_count=total_count,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @classmethod
    async def get_alert_detail(
        cls,
        session: AsyncSession,
        alert_id: UUID,
        plant_id: str = "ALL",
        customer_id: str = "ALL",
    ) -> Tuple[Optional[OperationalAlertItemDTO], Optional[str]]:
        """Fetch alert detail DTO by UUID with scope isolation protection."""
        model = await OperationalAlertRepository.get_alert_by_id(session, alert_id)
        if not model:
            return None, "ALERT_NOT_FOUND"

        # Enforce scope isolation on detail lookup
        if plant_id != "ALL" and model.plant_id != plant_id:
            return None, "SCOPE_ACCESS_DENIED"
        if customer_id != "ALL" and model.customer_id != customer_id:
            return None, "SCOPE_ACCESS_DENIED"

        return cls._model_to_dto(model), None

    @classmethod
    async def get_dataset_context(
        cls,
        session: AsyncSession,
        plant_id: str = "ALL",
        customer_id: str = "ALL",
        dataset_id: Optional[str] = None,
    ) -> OperationalDatasetContextDTO:
        """Fetch dataset context metadata for Alert Center context ribbon dynamically."""
        res_count = await session.execute(text("SELECT COUNT(*) FROM dispatches WHERE is_generated = false;"))
        total_dispatches = res_count.scalar_one_or_none() or 0

        res_date = await session.execute(text("SELECT MAX(dispatch_date) FROM dispatches WHERE is_generated = false;"))
        latest_date = res_date.scalar_one_or_none()
        op_date_str = latest_date.strftime("%Y-%m-%d") if latest_date else "2026-08-05"

        effective_dataset_id = dataset_id
        if not effective_dataset_id:
            # Dynamically derive from active import job or latest dispatch date
            from app.modules.site_dashboard.orchestration.filter_metadata_service import DashboardFilterMetadataService
            meta = await DashboardFilterMetadataService.get_filter_metadata(session)
            if meta and meta.dataset_info:
                effective_dataset_id = meta.dataset_info.dataset_id
                op_date_str = meta.dataset_info.operational_date or op_date_str

        if not effective_dataset_id:
            effective_dataset_id = f"DS-{latest_date.strftime('%Y%m')}-001" if latest_date else "DS-ACTIVE-001"

        res_job = await session.execute(text("SELECT created_at FROM import_jobs ORDER BY created_at DESC LIMIT 1;"))
        last_import = res_job.scalar_one_or_none()
        last_import_str = last_import.isoformat() if last_import else f"{op_date_str}T00:00:00Z"

        return OperationalDatasetContextDTO(
            operational_date=op_date_str,
            total_dispatches=total_dispatches,
            last_imported_at=last_import_str,
            dataset_id=effective_dataset_id,
            status="ACTIVE_PRODUCTION",
        )

    @classmethod
    async def get_summary(
        cls,
        session: AsyncSession,
        plant_id: str = "ALL",
        customer_id: str = "ALL",
        dataset_id: Optional[str] = None,
    ) -> AlertSummaryDTO:
        """Fetch summary alert metric counts DTO under active filters."""
        ctx = await cls.get_dataset_context(
            session=session, plant_id=plant_id, customer_id=customer_id, dataset_id=dataset_id
        )
        effective_dataset_id = dataset_id or ctx.dataset_id

        counts = await OperationalAlertRepository.get_summary_counts(
            session=session, plant_id=plant_id, customer_id=customer_id, dataset_id=effective_dataset_id
        )

        return AlertSummaryDTO(
            total_active_alerts=counts["open_count"],
            critical_count=counts["critical_count"],
            warning_count=counts["warning_count"],
            info_count=counts["info_count"],
            acknowledged_count=counts["acknowledged_count"],
            dataset_context=ctx,
        )

    @classmethod
    async def acknowledge_alert(
        cls,
        session: AsyncSession,
        alert_id: UUID,
        acknowledged_by: str,
        notes: Optional[str] = None,
    ) -> Tuple[Optional[OperationalAlertItemDTO], Optional[str]]:
        """
        Acknowledge an alert (OPEN -> ACKNOWLEDGED).
        Returns (dto, error_code).
        """
        existing = await OperationalAlertRepository.get_alert_by_id(session, alert_id)
        if not existing:
            return None, "ALERT_NOT_FOUND"

        if existing.status != "OPEN":
            return None, f"INVALID_LIFECYCLE_TRANSITION: Cannot acknowledge alert in state {existing.status}"

        updated = await OperationalAlertRepository.acknowledge_alert(
            session=session, alert_id=alert_id, acknowledged_by=acknowledged_by, notes=notes
        )
        if not updated:
            return None, "CONCURRENT_LIFECYCLE_CONFLICT"

        logger.info(f"[WS-07.5] Alert {alert_id} acknowledged by {acknowledged_by}")
        return cls._model_to_dto(updated), None

    @classmethod
    async def resolve_alert(
        cls,
        session: AsyncSession,
        alert_id: UUID,
        resolved_by: str,
        resolution_reason: str,
    ) -> Tuple[Optional[OperationalAlertItemDTO], Optional[str]]:
        """
        Resolve an alert (OPEN/ACKNOWLEDGED -> RESOLVED).
        Returns (dto, error_code).
        """
        existing = await OperationalAlertRepository.get_alert_by_id(session, alert_id)
        if not existing:
            return None, "ALERT_NOT_FOUND"

        if existing.status not in ["OPEN", "ACKNOWLEDGED"]:
            return None, f"INVALID_LIFECYCLE_TRANSITION: Cannot resolve alert in state {existing.status}"

        updated = await OperationalAlertRepository.resolve_alert(
            session=session, alert_id=alert_id, resolved_by=resolved_by, resolution_reason=resolution_reason
        )
        if not updated:
            return None, "CONCURRENT_LIFECYCLE_CONFLICT"

        logger.info(f"[WS-07.5] Alert {alert_id} resolved by {resolved_by}")
        return cls._model_to_dto(updated), None

    @classmethod
    async def archive_resolved_alerts(
        cls,
        session: AsyncSession,
        retention_hours: float = RESOLVED_OPERATIONAL_RETENTION_HOURS,
    ) -> int:
        """
        Executes archival transition RESOLVED -> ARCHIVED for alerts exceeding retention_hours.
        """
        return await OperationalAlertRepository.archive_resolved_alerts(session, retention_hours=retention_hours)

    @classmethod
    async def evaluate_and_persist_active_alerts(
        cls,
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """
        Evaluates real-time business rule alerts for the currently active operational dataset
        and persists them into operational_alerts.
        """
        from datetime import datetime, timezone
        from sqlalchemy import select, text
        from sqlalchemy.dialects.postgresql import insert
        from app.modules.erp.models import Dispatch, Plant, Customer, Ticket, Order
        from app.modules.operational_dashboard.widgets.alerts.evaluator_engine import AlertRulesEvaluatorEngine
        from app.modules.operational_dashboard.widgets.alerts.models import OperationalAlertModel
        from app.modules.site_dashboard.orchestration.filter_metadata_service import DashboardFilterMetadataService

        meta = await DashboardFilterMetadataService.get_filter_metadata(session)
        active_ds_id = meta.dataset_info.dataset_id if (meta and meta.dataset_info) else "DS-ACTIVE-001"
        op_date_str = meta.dataset_info.operational_date if (meta and meta.dataset_info) else "2026-03-01"

        stmt = (
            select(Dispatch, Plant, Customer)
            .outerjoin(Plant, Dispatch.plant_id == Plant.id)
            .outerjoin(Ticket, Dispatch.ticket_id == Ticket.id)
            .outerjoin(Order, Ticket.order_id == Order.id)
            .outerjoin(Customer, Order.customer_id == Customer.id)
            .where(Dispatch.is_deleted == False)
        )
        rows = (await session.execute(stmt)).all()

        dispatch_dicts = []
        for disp, plant, cust in rows:
            dispatch_dicts.append({
                'dispatch_id': str(disp.id),
                'plant_id': plant.code if plant else 'ACC_KUNDAIM',
                'customer_id': cust.code if cust else 'CUST_DEFAULT',
                't1_transit_mins': float(disp.t1_transit_mins or 0.0),
                't2a_holding_mins': float(disp.t2a_holding_mins or 0.0),
                't2b_unloading_mins': float(disp.t2b_unloading_mins or 0.0),
                't2c_retention_mins': float(disp.t2c_retention_mins or 0.0),
                'date': op_date_str
            })

        alert_dicts = AlertRulesEvaluatorEngine.evaluate_dispatches(dispatch_dicts, dataset_id=active_ds_id)

        existing_fps = set((await session.execute(
            select(OperationalAlertModel.alert_fingerprint).where(OperationalAlertModel.dataset_id == active_ds_id)
        )).scalars().all())

        now_dt = datetime.now(timezone.utc)
        new_models = []
        for ad_dict in alert_dicts:
            if isinstance(ad_dict, dict) and ad_dict.get('alert_fingerprint') not in existing_fps:
                existing_fps.add(ad_dict['alert_fingerprint'])
                ad_copy = dict(ad_dict)
                ad_copy.setdefault('created_at', now_dt)
                ad_copy.setdefault('updated_at', now_dt)
                new_models.append(ad_copy)

        CHUNK_SIZE = 1000
        if new_models:
            for i in range(0, len(new_models), CHUNK_SIZE):
                chunk = new_models[i:i + CHUNK_SIZE]
                await session.execute(insert(OperationalAlertModel).values(chunk))
            await session.commit()
            logger.info(f"[WS-07] Successfully generated & persisted {len(new_models)} operational alerts for {active_ds_id}")

        return {
            "status": "SUCCESS",
            "dataset_id": active_ds_id,
            "total_dispatches": len(rows),
            "total_alerts": len(alert_dicts),
            "new_alerts_inserted": len(new_models),
        }
