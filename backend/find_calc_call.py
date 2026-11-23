import os

def search():
    for root, dirs, files in os.walk("/home/sanjana/fleet-operational-intelligence-platform/backend/app/modules/operational_intelligence"):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8") as file:
                        text = file.read()
                        if "FinancialCalculationEngine" in text or "resolve_authoritative_rate" in text:
                            print("FOUND CALC ENGINE IN:", path)
                except Exception:
                    pass

if __name__ == "__main__":
    search()
