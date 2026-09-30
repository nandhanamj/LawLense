import re
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "processed" / "bns_raw.txt"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "bns_sections.json"


# -----------------------------
# Read raw extracted text
# -----------------------------
with open(INPUT_FILE, "r", encoding="utf-8") as f:
    lines = f.readlines()


# -----------------------------
# Remove PDF publication/signature metadata
# -----------------------------
clean_lines = []

for line in lines:
    if "UPLOADED BY THE MANAGER" in line:
        break

    clean_lines.append(line)

lines = clean_lines


# -----------------------------
# Parse chapters and sections
# -----------------------------
sections = []

current_chapter = ""
current_chapter_title = ""

current_section = None
current_content = []

i = 0

while i < len(lines):

    line = lines[i].strip()

    # Skip empty lines
    if not line:
        i += 1
        continue

    # -----------------------------------
    # Detect CHAPTER
    # -----------------------------------
    chapter_match = re.match(
        r"CHAPTER\s*([IVXLCDM]+)",
        line,
        re.IGNORECASE
    )

    if chapter_match:

        current_chapter = chapter_match.group(1)

        # Read next non-empty line as chapter title
        j = i + 1

        while j < len(lines):

            title = lines[j].strip()

            if title:
                current_chapter_title = title
                break

            j += 1

        i += 1
        continue

    # -----------------------------------
    # Detect SECTION
    # Examples:
    # 104. Whoever...
    # 104.Whoever...
    # -----------------------------------
    section_match = re.match(
        r"^(\d{1,3})\.\s*(.+)",
        line
    )

    if section_match:

        # Save previous section
        if current_section is not None:

            sections.append({
                "act": "BNS",
                "chapter": current_chapter,
                "chapter_title": current_chapter_title,
                "section": current_section,
                "content": "\n".join(current_content).strip()
            })

        current_section = section_match.group(1)
        current_content = [section_match.group(2)]

        i += 1
        continue

    # -----------------------------------
    # Continue current section
    # -----------------------------------
    if current_section is not None:
        current_content.append(line)

    i += 1


# -----------------------------------
# Save last section
# -----------------------------------
if current_section is not None:

    sections.append({
        "act": "BNS",
        "chapter": current_chapter,
        "chapter_title": current_chapter_title,
        "section": current_section,
        "content": "\n".join(current_content).strip()
    })


# -----------------------------------
# Remove duplicate (chapter, section)
# -----------------------------------
unique_sections = []
seen = set()

for section in sections:

    key = (section["chapter"], section["section"])

    if key not in seen:
        seen.add(key)
        unique_sections.append(section)

sections = unique_sections


# -----------------------------------
# Keep only valid BNS sections
# -----------------------------------
sections = [
    s for s in sections
    if 1 <= int(s["section"]) <= 358
]


# -----------------------------------
# Sort by section number
# -----------------------------------
sections.sort(key=lambda x: int(x["section"]))


# -----------------------------------
# Save JSON
# -----------------------------------
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

    json.dump(
        sections,
        f,
        indent=4,
        ensure_ascii=False
    )


print("=" * 60)
print(f"Sections Extracted : {len(sections)}")
print(f"Saved To : {OUTPUT_FILE}")
print("=" * 60)