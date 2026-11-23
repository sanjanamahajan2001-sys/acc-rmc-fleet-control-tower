"""
WS-10.6 Test Database Isolation & Zero Pollution Regression Test.
Verifies that running WS-10 tests does NOT pollute the production database.
"""

import pytest
from sqlalchemy import select, func, and_

from app.modules.operational_intelligence.tests.conftest import TestAsyncSessionFactory
from app.modules.operational_intelligence.models.ml_registry import MLModelVersion
from app.modules.operational_intelligence.models.prediction_snapshot import MLPredictionSnapshot
from app.modules.operational_intelligence.services.inference_service import WS10InferenceService


@pytest.mark.asyncio
async def test_ws_10_6_zero_test_pollution_regression():
    """
    Verifies production database state invariants after test execution:
    - PROMOTED models count: 0
    - Protected WS-09 REJECTED count: 4
    - Prediction snapshots count: 0
    - Prediction authority status: NOT_CONFIGURED
    """
    async with TestAsyncSessionFactory() as session:
        # 1. Verify PROMOTED = 0
        stmt_p = select(func.count(MLModelVersion.id)).where(MLModelVersion.lifecycle_status == "PROMOTED")
        res_p = await session.execute(stmt_p)
        c_promoted = res_p.scalar()
        assert c_promoted == 0, f"PROMOTED model count is {c_promoted}, expected 0!"

        # 2. Verify WS-09 historical REJECTED = 4
        stmt_r = select(func.count(MLModelVersion.id)).where(
            and_(
                MLModelVersion.lifecycle_status == "REJECTED",
                MLModelVersion.model_version == "v1.0.0-rejected-ws09",
            )
        )
        res_r = await session.execute(stmt_r)
        c_rejected = res_r.scalar()
        assert c_rejected == 4, f"WS-09 historical REJECTED count is {c_rejected}, expected 4!"

        # 3. Verify PREDICTION SNAPSHOTS = 0
        stmt_s = select(func.count(MLPredictionSnapshot.id))
        res_s = await session.execute(stmt_s)
        c_snapshots = res_s.scalar()
        assert c_snapshots == 0, f"Prediction snapshots count is {c_snapshots}, expected 0!"

        # 4. Verify AUTHORITY = NOT_CONFIGURED
        audit = await WS10InferenceService.audit_real_production_inference(session)
        assert audit["overall_prediction_authority_status"] == "NOT_CONFIGURED"
