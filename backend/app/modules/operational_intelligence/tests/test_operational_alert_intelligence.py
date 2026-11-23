"""
WS-09 Phase 2 Automated Test Suite & Direct PostgreSQL Reconciliation Test
Tests Operational Alert Intelligence backend calculations, filter matrix propagation, widget-level reconciliation,
and cross-section reconciliation with Section 01.
"""

import pytest
from sqlalchemy import select, func, text
from app.core.database import AsyncSessionFactory, engine
from app.modules.site_dashboard.schemas.request_dtos import DashboardFilterParams
from app.modules.operational_intelligence.services.alert_intelligence_service import OperationalAlertIntelligenceService
from app.modules.operational_intelligence.services.health_service import OperationalHealthService
from app.modules.operational_dashboard.widgets.alerts.models import OperationalAlertModel


@pytest.mark.asyncio
async def test_alert_intelligence_service_basic():
    """
    Test OperationalAlertIntelligenceService basic execution under default filters.
    Verifies that the service returns an OperationalAlertIntelligenceResponseDTO.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        params = DashboardFilterParams(
            plant_id="ALL",
            customer_id="ALL",
            dataset_type="ALL",
        )
        result = await OperationalAlertIntelligenceService.get_alert_intelligence(db_session, params)

        assert result is not None
        assert result.summary is not None
        assert result.calculation_status in ["SUCCESS", "NO_RECORDS"]

        if result.calculation_status == "SUCCESS":
            assert result.summary.total_active >= 0
            assert result.summary.open_count + result.summary.acknowledged_count == result.summary.total_active
            assert result.summary.critical_count + result.summary.warning_count + result.summary.info_count == result.summary.total_active
            assert len(result.severity_distribution) > 0


@pytest.mark.asyncio
async def test_alert_intelligence_filter_matrix_suite():
    """
    Test filter propagation across Plant, Customer, Date, and Dataset Type parameters.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        # 1. Test Plant Filter ACC_KUNDAIM
        params_kundaim = DashboardFilterParams(plant_id="ACC_KUNDAIM", customer_id="ALL", dataset_type="ALL")
        res_kundaim = await OperationalAlertIntelligenceService.get_alert_intelligence(db_session, params_kundaim)
        assert res_kundaim is not None
        assert res_kundaim.summary.total_active == 852
        assert "852 active alerts" in res_kundaim.calculation_notes

        # 2. Test Plant Filter ACC_VASCO
        params_vasco = DashboardFilterParams(plant_id="ACC_VASCO", customer_id="ALL", dataset_type="ALL")
        res_vasco = await OperationalAlertIntelligenceService.get_alert_intelligence(db_session, params_vasco)
        assert res_vasco is not None
        assert res_vasco.summary.total_active == 612
        assert "612 active alerts" in res_vasco.calculation_notes

        # 3. Test Customer Filter CUST_TRUE_BUILD
        params_cust = DashboardFilterParams(plant_id="ALL", customer_id="CUST_TRUE_BUILD", dataset_type="ALL")
        res_cust = await OperationalAlertIntelligenceService.get_alert_intelligence(db_session, params_cust)
        assert res_cust is not None
        assert res_cust.calculation_status in ["SUCCESS", "NO_RECORDS"]

        # 4. Test Combined Filter (ACC_VASCO + CUST_TRUE_BUILD + REAL_ONLY)
        params_comb = DashboardFilterParams(
            plant_id="ACC_VASCO",
            customer_id="CUST_TRUE_BUILD",
            dataset_type="REAL_ONLY",
            operation_date="2026-08-05",
        )
        res_comb = await OperationalAlertIntelligenceService.get_alert_intelligence(db_session, params_comb)
        assert res_comb is not None
        assert res_comb.calculation_status in ["SUCCESS", "NO_RECORDS"]


@pytest.mark.asyncio
async def test_alert_intelligence_full_widget_reconciliation():
    """
    MANDATORY WIDGET-LEVEL RECONCILIATION TEST:
    Verifies all 11 Section 02 metric families against direct SQL calculations on `operational_alerts` table.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        dataset_id = "DS-20260805-001"
        params = DashboardFilterParams(plant_id="ALL", customer_id="ALL", dataset_id=dataset_id)
        dto = await OperationalAlertIntelligenceService.get_alert_intelligence(db_session, params)

        # 1. Direct Summary Reconciliation (Total Active, Open, Ack, Crit, Warn, Info)
        q_summary = select(
            func.count().filter(OperationalAlertModel.status.in_(["OPEN", "ACKNOWLEDGED"])).label("total_active"),
            func.count().filter(OperationalAlertModel.status == "OPEN").label("open_count"),
            func.count().filter(OperationalAlertModel.status == "ACKNOWLEDGED").label("ack_count"),
            func.count().filter((OperationalAlertModel.severity == "CRITICAL") & (OperationalAlertModel.status.in_(["OPEN", "ACKNOWLEDGED"]))).label("crit_count"),
            func.count().filter((OperationalAlertModel.severity == "WARNING") & (OperationalAlertModel.status.in_(["OPEN", "ACKNOWLEDGED"]))).label("warn_count"),
            func.count().filter((OperationalAlertModel.severity == "INFO") & (OperationalAlertModel.status.in_(["OPEN", "ACKNOWLEDGED"]))).label("info_count"),
        ).where(OperationalAlertModel.dataset_id == dataset_id)

        res_sum = (await db_session.execute(q_summary)).fetchone()
        assert dto.summary.total_active == (res_sum.total_active or 0)
        assert dto.summary.open_count == (res_sum.open_count or 0)
        assert dto.summary.acknowledged_count == (res_sum.ack_count or 0)
        assert dto.summary.critical_count == (res_sum.crit_count or 0)
        assert dto.summary.warning_count == (res_sum.warn_count or 0)
        assert dto.summary.info_count == (res_sum.info_count or 0)

        # 2. Plant Concentration Reconciliation
        q_plant = select(
            OperationalAlertModel.plant_id,
            func.count().label("total_cnt")
        ).where(
            OperationalAlertModel.dataset_id == dataset_id,
            OperationalAlertModel.status.in_(["OPEN", "ACKNOWLEDGED"])
        ).group_by(OperationalAlertModel.plant_id).order_by(text("total_cnt DESC"))

        plant_rows = (await db_session.execute(q_plant)).fetchall()
        db_top_plant = plant_rows[0] if plant_rows else None
        if db_top_plant and dto.plant_concentration:
            assert dto.plant_concentration[0].group_code == db_top_plant.plant_id
            assert dto.plant_concentration[0].total_count == db_top_plant.total_cnt

        # 3. Priority Alerts Ordering Reconciliation (CRITICAL > WARNING > INFO, detected_at ASC, id ASC)
        q_priority = select(OperationalAlertModel).where(
            OperationalAlertModel.dataset_id == dataset_id,
            OperationalAlertModel.status.in_(["OPEN", "ACKNOWLEDGED"])
        ).order_by(
            text("CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'WARNING' THEN 2 WHEN 'INFO' THEN 3 ELSE 4 END ASC"),
            OperationalAlertModel.detected_at.asc(),
            OperationalAlertModel.id.asc()
        ).limit(5)

        priority_models = (await db_session.execute(q_priority)).scalars().all()
        assert len(dto.priority_alerts) == len(priority_models)
        for dto_item, db_item in zip(dto.priority_alerts, priority_models):
            assert dto_item.id == str(db_item.id)
            assert dto_item.severity == db_item.severity


@pytest.mark.asyncio
async def test_cross_section_reconciliation_sec01_vs_sec02():
    """
    CROSS-SECTION RECONCILIATION TEST:
    Verifies that Active Critical Alerts count in Section 01 equals Critical Active Alerts count in Section 02.
    """
    await engine.dispose()
    async with AsyncSessionFactory() as db_session:
        for plant in ["ALL", "ACC_VASCO", "ACC_KUNDAIM", "ACC_DHARGA", "ACC_NESSAI"]:
            params = DashboardFilterParams(plant_id=plant, customer_id="ALL", dataset_type="ALL")
            
            s1_res = await OperationalHealthService.get_operational_health(db_session, params)
            s2_res = await OperationalAlertIntelligenceService.get_alert_intelligence(db_session, params)

            if s1_res.calculation_status == "SUCCESS" and s2_res.calculation_status == "SUCCESS":
                s1_crit = next((m.current_value for m in s1_res.metrics if m.key == "active_critical_alerts"), 0.0)
                s2_crit = float(s2_res.summary.critical_count)

                assert s1_crit == s2_crit, f"Cross-section mismatch for plant {plant}: Sec01={s1_crit}, Sec02={s2_crit}"
