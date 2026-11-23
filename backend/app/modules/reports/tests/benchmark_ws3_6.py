import time
import asyncio
from unittest.mock import AsyncMock, patch
from app.modules.reports.schemas.predictive_intelligence_canonical import CanonicalPredictiveIntelligenceReport, ReportMetadataDTO, PredictiveKPISummary
from app.modules.reports.handlers.predictive_intelligence_handler import PredictiveIntelligenceReportHandler
from app.modules.reports.renderers.json_renderer import JSONReportRenderer
from app.modules.reports.renderers.xlsx_renderer import XLSXReportRenderer
from app.modules.reports.renderers.pdf_renderer import PDFReportRenderer
from app.modules.operational_intelligence.schemas.predictive_operational_dtos import (
    OperationalPredictiveResponseDTO, OperationalPrioritizationDTO, OperationalPredictionItemDTO
)

mock_dto = OperationalPredictiveResponseDTO(
    overall_authority_status="AUTHORITATIVE",
    promoted_model_count=1,
    total_snapshots_found=25,
    prioritization=OperationalPrioritizationDTO(),
    snapshots=[
        OperationalPredictionItemDTO(
            id=f"id-{i}",
            prediction_snapshot_id=f"SNAP-{i:03d}",
            idempotency_key=f"key-{i}",
            prediction_timestamp="2026-08-05T08:00:00Z",
            prediction_status="SUCCESS",
            model_name="delay_regressor",
            model_version="v1.1.0",
            artifact_sha256="sha-1234",
            feature_set_version="FeatureSetV1",
            dispatch_id=f"DISP-{i:03d}",
            dispatch_code=f"DN-{i:03d}",
            plant_code="VASCO",
            customer_code="CUST-001",
            vehicle_code=f"GA-01-TRUCK-{i:02d}",
            target_name="predicted_delay_mins",
            predicted_value=15.0 + i,
            confidence_score=0.85 + (i * 0.005),
            financial_exposure_inr=10000.0 + (i * 500),
            total_financial_risk_inr=10000.0 + (i * 500)
        )
        for i in range(1, 26)
    ],
    calculation_status="SUCCESS",
    calculation_notes="Benchmark notes"
)

handler = PredictiveIntelligenceReportHandler()
raw_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL"}
eff_scope = {"plant_id": "VASCO", "operation_date": "2026-08-05", "shift": "ALL", "resolved_dataset_id": "DS-20260805-VASCO"}

t0 = time.perf_counter()
with patch("app.modules.operational_intelligence.services.predictive_service.PredictiveIntelligenceService.get_operational_predictive_intelligence", return_value=mock_dto):
    report = asyncio.run(handler.build_canonical_report(AsyncMock(), "bench-pred-25", raw_scope, eff_scope, "fp-bench-pred"))
t1 = time.perf_counter()

json_bytes = JSONReportRenderer.render(report)
t2 = time.perf_counter()

xlsx_bytes = XLSXReportRenderer.render(report)
t3 = time.perf_counter()

pdf_bytes = PDFReportRenderer.render(report)
t4 = time.perf_counter()

print("BENCHMARK_WS3_6_PREDICTIVE_INTELLIGENCE:")
print(f"CANONICAL_ASSEMBLY_MS={((t1-t0)*1000):.2f}")
print(f"JSON_MS={((t2-t1)*1000):.2f}, SIZE={len(json_bytes)} bytes")
print(f"XLSX_MS={((t3-t2)*1000):.2f}, SIZE={len(xlsx_bytes)} bytes")
print(f"PDF_MS={((t4-t3)*1000):.2f}, SIZE={len(pdf_bytes)} bytes")
print(f"TOTAL_MS={((t4-t0)*1000):.2f}")
