"""
WS-07.4 Alert Rules Evaluation Engine & Import-Triggered Persistence Service.
Connects ERP import completion with post-commit alert evaluation and idempotent persistence into operational_alerts.
"""
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.logging import get_logger
from app.modules.operational_dashboard.widgets.alerts.models import OperationalAlertModel
from app.modules.operational_dashboard.widgets.alerts.evaluator_engine import AlertRulesEvaluatorEngine
from app.modules.operational_dashboard.widgets.dispatch_analysis.repository import DispatchAnalysisRepository
from app.modules.operational_dashboard.widgets.dispatch_optimization.services.readiness_engine import OptimizationReadinessEngine

logger = get_logger(__name__)

class AlertTriggerOrchestrator:
    """
    Post-commit orchestrator that receives successful ERP import metadata,
    evaluates committed dispatches using AlertRulesEvaluatorEngine,
    and persists alert candidates into operational_alerts with idempotency.
    """

    @classmethod
    async def process_post_commit_import_alerts(
        cls,
        session: AsyncSession,
        dataset_id: str,
        import_job_id: Optional[str] = None,
        plant_id: str = "ALL",
        customer_id: str = "ALL",
        batch_size: int = 500,
    ) -> Dict[str, Any]:
        """
        Orchestrates post-commit alert evaluation and idempotent database persistence in chunked batches.
        Must be executed ONLY after the primary ERP import transaction has COMMITTED.
        """
        start_time = datetime.now(timezone.utc)
        logger.info(
            f"[WS-07.4] Alert trigger evaluation started for dataset_id={dataset_id}, import_job_id={import_job_id}"
        )

        result_summary = {
            "dataset_id": dataset_id,
            "import_job_id": import_job_id,
            "evaluation_started": start_time.isoformat(),
            "dispatch_count": 0,
            "candidate_count": 0,
            "inserted_count": 0,
            "duplicate_count": 0,
            "failed_count": 0,
            "readiness_alert_persisted": False,
            "duration_ms": 0.0,
            "status": "SUCCESS",
        }

        try:
            # 1. Bulk Fetch Committed Dispatches (Scoped to imported dataset/filters)
            scope_filter = {
                "plant_id": plant_id,
                "customer_id": customer_id,
                "dataset_type": "REAL_ONLY", # Exclude synthetic/generated dispatches
            }
            dispatches = await DispatchAnalysisRepository.get_scoped_dispatches(session, scope_filter)
            result_summary["dispatch_count"] = len(dispatches)

            # 2. Evaluate Dispatches using WS-07.3 Evaluator Engine
            candidates = AlertRulesEvaluatorEngine.evaluate_dispatches(
                dispatches=dispatches,
                dataset_id=dataset_id,
                import_job_id=import_job_id,
            )

            # 3. Evaluate Platform Data Quality Readiness (Rule 4)
            readiness_dto = await OptimizationReadinessEngine.evaluate_readiness(session, scope_filter)
            readiness_candidate = AlertRulesEvaluatorEngine.evaluate_readiness(
                readiness_status=readiness_dto.status.value,
                quality_summary=readiness_dto.quality_summary.model_dump() if hasattr(readiness_dto.quality_summary, "model_dump") else readiness_dto.quality_summary,
                blocking_conditions=readiness_dto.blocking_conditions,
                plant_id=plant_id,
                customer_id=customer_id,
                dataset_id=dataset_id,
            )

            if readiness_candidate:
                candidates.append(readiness_candidate)
                result_summary["readiness_alert_persisted"] = True

            result_summary["candidate_count"] = len(candidates)

            if not candidates:
                logger.info(f"[WS-07.4] 0 alert candidates generated for dataset_id={dataset_id}")
                end_time = datetime.now(timezone.utc)
                result_summary["duration_ms"] = round((end_time - start_time).total_seconds() * 1000, 2)
                return result_summary

            # 4. Chunked Idempotent Database Persistence via ON CONFLICT DO NOTHING
            now_tz = datetime.now(timezone.utc)
            total_inserted = 0

            # Process candidates in batches of 500 to avoid PostgreSQL parameter limit
            for i in range(0, len(candidates), batch_size):
                chunk = candidates[i : i + batch_size]
                values_to_insert = []

                for c in chunk:
                    evidence_payload = c["evidence_json"]
                    if isinstance(evidence_payload, dict):
                        evidence_payload = json.dumps(evidence_payload)

                    values_to_insert.append({
                        "alert_fingerprint": c["alert_fingerprint"],
                        "alert_type": c["alert_type"],
                        "severity": c["severity"],
                        "status": "OPEN", # Initial lifecycle state
                        "plant_id": c["plant_id"],
                        "customer_id": c["customer_id"],
                        "dispatch_id": c["dispatch_id"],
                        "vehicle_id": c["vehicle_id"],
                        "dataset_id": c["dataset_id"], # Preserve passed dataset_id
                        "import_job_id": import_job_id,
                        "metric_name": c["metric_name"],
                        "actual_value": c["actual_value"],
                        "threshold_value": c["threshold_value"],
                        "unit": c["unit"],
                        "business_impact": c["business_impact"],
                        "evidence_json": evidence_payload,
                        "recommended_action": c["recommended_action"],
                        "rule_version": c["rule_version"],
                        "detected_at": now_tz,
                        "evaluated_at": now_tz,
                        "created_at": now_tz,
                        "updated_at": now_tz,
                        "acknowledged_at": None,
                        "acknowledged_by": None,
                        "acknowledgement_notes": None,
                        "resolved_at": None,
                        "resolved_by": None,
                        "resolution_reason": None,
                    })

                stmt = pg_insert(OperationalAlertModel).values(values_to_insert)
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=["alert_fingerprint", "dataset_id"]
                )

                res = await session.execute(stmt)
                await session.commit()
                if res.rowcount is not None and res.rowcount >= 0:
                    total_inserted += res.rowcount

            result_summary["inserted_count"] = total_inserted
            result_summary["duplicate_count"] = len(candidates) - total_inserted

            logger.info(
                f"[WS-07.4] Alert persistence complete for dataset_id={dataset_id}: "
                f"{total_inserted} inserted, {result_summary['duplicate_count']} duplicates skipped."
            )

        except Exception as exc:
            await session.rollback()
            logger.error(f"[WS-07.4] Alert trigger evaluation failed for dataset_id={dataset_id}: {str(exc)}", exc_info=True)
            result_summary["status"] = "FAILED"
            result_summary["failed_count"] = result_summary["candidate_count"]

        end_time = datetime.now(timezone.utc)
        result_summary["duration_ms"] = round((end_time - start_time).total_seconds() * 1000, 2)
        return result_summary
