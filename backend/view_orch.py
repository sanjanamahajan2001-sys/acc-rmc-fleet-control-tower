import app.modules.erp.workers.orchestrator as orchestrator
import inspect

lines = inspect.getsourcelines(orchestrator)[0]
print(f"Total lines in orchestrator.py: {len(lines)}")
for i, line in enumerate(lines[:150]):
    print(f"{i+1:3d}: {line}", end="")
