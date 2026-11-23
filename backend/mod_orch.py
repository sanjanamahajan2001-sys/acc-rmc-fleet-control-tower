import re

path = "/home/sanjana/fleet-operational-intelligence-platform/backend/app/modules/erp/workers/orchestrator.py"
with open(path, "r") as f:
    content = f.read()

target = '        await self._publish(\n            "erp.import.completed",\n            {"job_number": job_number, "processed_rows": val_stats.rows_accepted},\n        )'

replacement = """        await self._publish(
            "erp.import.completed",
            {"job_number": job_number, "processed_rows": val_stats.rows_accepted},
        )

        # 8. WS-10.1 Trigger Boundary: Evaluate ERP completion for ML Lifecycle Trigger
        try:
            from app.modules.operational_intelligence.events.erp_trigger_listener import ERPTriggerListener
            await ERPTriggerListener.on_erp_import_completed(
                session=session,
                event_payload={
                    "job_number": job_number,
                    "dataset_id": job_number,
                    "processed_rows": val_stats.rows_accepted,
                    "counts": counts,
                },
                correlation_id=self.correlation_id,
                request_id=self.request_id,
            )
        except Exception as trigger_err:
            # Transaction safety: trigger evaluation failure MUST NOT fail ERP import persistence
            pass"""

if target in content:
    new_content = content.replace(target, replacement, 1)
    with open(path, "w") as f:
        f.write(new_content)
    print("SUCCESSFULLY MODIFIED ORCHESTRATOR")
else:
    print("TARGET NOT FOUND IN ORCHESTRATOR")
