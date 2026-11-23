import os
import glob

def search_files():
    for root, dirs, files in os.walk("/home/sanjana/fleet-operational-intelligence-platform/backend"):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8") as file:
                        content = file.read()
                        if "RATE-GLOBAL-HOLDING-V1" in content or "seed_rate" in f or "seed_calculation" in f:
                            print("FOUND IN:", path)
                except Exception:
                    pass

if __name__ == "__main__":
    search_files()
