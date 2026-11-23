import app.modules.erp.workers.orchestrator as orchestrator
import inspect

lines = inspect.getsourcelines(orchestrator)[0]
for i, line in enumerate(lines[149:]):
    print(f"{i+150:3d}: {line}", end="")
