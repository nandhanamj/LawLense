import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
JSON_FILE = BASE_DIR / "data" / "processed" / "bns_sections.json"

with open(JSON_FILE, "r", encoding="utf-8") as f:
    sections = json.load(f)

numbers = sorted(int(s["section"]) for s in sections)

print("Total:", len(numbers))
print()

print("Missing Sections:")

for i in range(1, 359):
    if i not in numbers:
        print(i)