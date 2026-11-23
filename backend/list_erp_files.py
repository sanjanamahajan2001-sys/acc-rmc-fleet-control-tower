import os

erp_dir = "/home/sanjana/fleet-operational-intelligence-platform/backend/app/modules/erp"
for root, dirs, files in os.walk(erp_dir):
    for f in files:
        if f.endswith(".py"):
            rel = os.path.relpath(os.path.join(root, f), erp_dir)
            print("ERP file:", rel)
