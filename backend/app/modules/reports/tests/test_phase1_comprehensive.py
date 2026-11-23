import pytest
import asyncio
from app.modules.reports.schemas.report_schemas import (
    ReportScopeDTO,
    ReportRequestDTO,
    ReportFormat,
    ReportStatus,
    ScopeValidationStatus
)
from app.modules.reports.services.scope_resolver import ScopeResolverService
from app.modules.reports.services.report_registry import ReportRegistry, ReportDefinitionDTO


def test_fingerprint_differentiation_and_normalization():
    s1 = {"plant_id": "VASCO", "customer_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL", "dataset_type": "ALL"}
    s2 = {"plant_id": "vasco", "customer_id": "all", "operation_date": "2026-08-05", "shift": "all", "dataset_type": "all"}
    s3_diff_plant = {"plant_id": "MAGARPAETTA", "customer_id": "ALL", "operation_date": "2026-08-05", "shift": "ALL", "dataset_type": "ALL"}
    s2_diff_date = {"plant_id": "VASCO", "customer_id": "ALL", "operation_date": "2026-08-06", "shift": "ALL", "dataset_type": "ALL"}

    fp1a = ScopeResolverService.compute_scope_fingerprint(s1)
    fp1b = ScopeResolverService.compute_scope_fingerprint(s2)
    fp3 = ScopeResolverService.compute_scope_fingerprint(s3_diff_plant)
    fp4 = ScopeResolverService.compute_scope_fingerprint(s2_diff_date)

    assert fp1a == fp1b
    assert fp1a != fp3
    assert fp1a != fp4



def test_report_registry_all_12_and_duplicate_rejection():
    catalog = ReportRegistry.list_all()
    assert len(catalog) == 12
    report_ids = [p.report_id for p in catalog]
    assert "dispatch_analysis" in report_ids
    assert "site_operations" in report_ids

    with pytest.raises(ValueError):
        ReportRegistry.register(ReportDefinitionDTO(
            report_id="dispatch_analysis",
            name="Duplicate",
            description="Duplicate",
            source_service="duplicate",
            supported_formats=[ReportFormat.PDF],
            supported_filters=[]
        ))


@pytest.mark.asyncio
async def test_authorization_and_scope_validation_logic():
    resolver = ScopeResolverService()
    
    class MockSession:
        async def execute(self, query):
            class MockResult:
                def scalar(self):
                    return 100
            return MockResult()
    mock_session = MockSession()

    ok, scope, err = await resolver.resolve_and_validate_scope(
        session=mock_session,
        raw_scope={"plant_id": "INVALID", "customer_id": "ALL"},
        authorized_plants=["VASCO", "MAGARPAETTA"]
    )
    assert ok is False
    assert err in ("UNAUTHORIZED_PLANT_SCOPE", "INVALID_PLANT_SCOPE")


    ok2, scope2, err2 = await resolver.resolve_and_validate_scope(
        session=mock_session,
        raw_scope={"plant_id": "VASCO", "customer_id": "ALL"},
        authorized_plants=["VASCO", "MAGARPAETTA"]
    )
    assert ok2 is True
    assert scope2["plant_id"] == "VASCO"
    assert scope2["record_count"] == 100

