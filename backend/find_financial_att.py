import os

def search():
    for root, dirs, files in os.walk("/home/sanjana/fleet-operational-intelligence-platform/backend"):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8") as file:
                        text = file.read()
                        if "NOT_CONFIGURED" in text or "financial_exposure" in text:
                            print("FOUND IN:", path)
                except Exception:
                    pass

if __name__ == "__main__":
    search()
