import os
import glob
import sys

print("=== BACKEND MODULES SEARCH ===")
import app.modules as modules
print("Modules package dir:", modules.__path__)

# Search for erp import or ingestion
for root, dirs, files in os.walk("/home/sanjana/fleet-operational-intelligence-platform/backend/app"):
    for f in files:
        if "erp" in f or "ingest" in f or "import" in f:
            print("Found file:", os.path.join(root, f))
