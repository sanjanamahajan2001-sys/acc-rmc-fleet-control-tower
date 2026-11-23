import inspect
import app.modules.erp.models as erp_models
import app.modules.erp.services.job_service as job_service
import app.modules.erp.workers.orchestrator as orchestrator

print("=== ERP MODELS ===")
for name in dir(erp_models):
    if not name.startswith("_"):
        print("  -", name)

print("\n=== JOB SERVICE FUNCTIONS ===")
for name in dir(job_service):
    if not name.startswith("_"):
        print("  -", name)

print("\n=== ORCHESTRATOR FUNCTIONS ===")
for name in dir(orchestrator):
    if not name.startswith("_"):
        print("  -", name)
