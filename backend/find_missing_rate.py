import os

def search():
    for root, dirs, files in os.walk("/home/sanjana/fleet-operational-intelligence-platform/backend"):
        for f in files:
            if f.endswith(".py"):
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8") as file:
                        text = file.read()
                        if "MISSING_RATE_CONFIGURATION" in text:
                            print("FOUND MISSING_RATE_CONFIGURATION IN:", path)
                except Exception:
                    pass

if __name__ == "__main__":
    search()
