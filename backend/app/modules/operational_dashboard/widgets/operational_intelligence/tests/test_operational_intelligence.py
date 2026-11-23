import pytest
from app.modules.operational_dashboard.widgets.operational_intelligence.dtos import (
    ProblemCustomerDTO,
    ProblemCustomerListResponseDTO,
    OverlapSiteDTO,
    OverlapHeatmapResponseDTO,
    SiteReadinessDTO,
    SiteReadinessResponseDTO,
    OperationalIntelligenceStatusEnum,
    OperationalGradeEnum,
)

def test_problem_customer_dto_contracts():
    pc = ProblemCustomerDTO(
        customer_id="CUST_001",
        customer_name="Test Customer",
        rank=1,
        total_trips=50,
        holding_hours=10.5,
        retention_hours=2.5,
        total_lost_hours=13.0,
        cei=74.0,
    )
    assert pc.customer_id == "CUST_001"
    assert pc.rank == 1
    assert pc.total_lost_hours == 13.0

    res = ProblemCustomerListResponseDTO(
        success=True,
        status=OperationalIntelligenceStatusEnum.AVAILABLE,
        total_count=1,
        data=[pc],
        filters={"plant_id": "ACC_DHARGA"},
    )
    assert res.success is True
    assert res.status == OperationalIntelligenceStatusEnum.AVAILABLE
    assert len(res.data) == 1
    assert res.filters["plant_id"] == "ACC_DHARGA"


def test_overlap_heatmap_dto_contracts():
    site = OverlapSiteDTO(
        site_id="CUST_002",
        site_name="Overlap Site",
        rank=1,
        total_trips=25,
        peak_tms_together=5,
        avg_tms_standing_together=4.2,
        overlap_hours=15.0,
        weighted_tm_minutes=2880.0,
    )
    assert site.site_id == "CUST_002"
    assert site.peak_tms_together == 5
    assert site.avg_tms_standing_together == 4.2

    res = OverlapHeatmapResponseDTO(
        success=True,
        status=OperationalIntelligenceStatusEnum.AVAILABLE,
        total_sites=1,
        data=[site],
        filters={"customer_id": "CUST_002"},
    )
    assert res.total_sites == 1
    assert res.data[0].weighted_tm_minutes == 2880.0


def test_site_readiness_dto_contracts():
    sri = SiteReadinessDTO(
        site_id="CUST_03",
        site_name="Readiness Site",
        rank=1,
        total_trips=30,
        swi_site=85.0,
        dpi_site=75.0,
        fui_site=100.0,
        sri_score=85.25,
        grade=OperationalGradeEnum.GRADE_A,
    )
    assert sri.grade == OperationalGradeEnum.GRADE_A
    assert sri.sri_score == 85.25

    res = SiteReadinessResponseDTO(
        success=True,
        status=OperationalIntelligenceStatusEnum.AVAILABLE,
        total_sites=1,
        data=[sri],
        filters={"dataset_type": "REAL_ONLY"},
    )
    assert res.total_sites == 1
    assert res.data[0].grade == OperationalGradeEnum.GRADE_A


def test_deterministic_zero_null_semantics():
    res_empty = ProblemCustomerListResponseDTO(
        success=True,
        status=OperationalIntelligenceStatusEnum.NO_OBSERVATIONS,
        total_count=0,
        data=[],
        filters={},
    )
    assert res_empty.total_count == 0
    assert res_empty.data == []
    assert res_empty.status == OperationalIntelligenceStatusEnum.NO_OBSERVATIONS
