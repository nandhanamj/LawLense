"""
BNS Corpus Preprocessing and Chunk Generation Pipeline.

Parses extracted statutory text from data/processed/bns_raw.txt, strips Gazette
headers and artifacts, associates official section titles and offence categories,
and emits production-ready structured chunks into data/processed/bns_sections.json.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "processed" / "bns_raw.txt"
TITLES_FILE = BASE_DIR / "data" / "mappings" / "section_titles.json"
OUTPUT_FILE = BASE_DIR / "data" / "processed" / "bns_sections.json"

# Curated legal keywords for key offence sections
OFFENCE_KEYWORD_MAP: Dict[str, List[str]] = {
    "103": ["murder", "punishment for murder", "death penalty", "capital punishment", "imprisonment for life", "mob lynching", "culpable homicide amounting to murder", "killing"],
    "101": ["murder definition", "culpable homicide", "intention to cause death", "bodily injury likely to cause death"],
    "100": ["culpable homicide", "causing death", "homicide not amounting to murder"],
    "106": ["causing death by negligence", "rash or negligent act", "medical negligence", "rash driving", "vehicular accident death", "negligent act", "death by negligence"],
    "111": ["organised crime", "organized crime syndicate", "gangster", "continuing unlawful activity", "extortion syndicate", "contract killing", "ransom", "economic offences"],
    "112": ["petty organised crime", "theft gang", "snatching gang", "pickpocketing", "card skimming", "ticket touting", "unauthorized betting", "public nuisance gang"],
    "137": ["kidnapping", "kidnapping from India", "kidnapping from lawful guardianship", "minor kidnapping", "enticing child", "abduction punishment"],
    "138": ["abduction", "compelling by force", "inducing by deceitful means", "abducting person"],
    "303": ["theft", "punishment for theft", "definition of theft", "dishonest moving", "stealing", "movable property theft", "first time offender theft", "community service for theft", "imprisonment for theft"],
    "304": ["snatching", "punishment for snatching", "theft is snatching", "forcible seizure", "sudden grabbing", "quick snatching", "running away with stolen property", "grab movable property"],
    "305": ["theft in dwelling house", "theft in building", "theft in tent", "theft in vessel", "theft in transport", "theft in place of worship", "theft in human dwelling"],
    "306": ["theft by clerk", "theft by servant", "clerk or servant theft of master property"],
    "307": ["theft after preparation for death", "theft with hurt preparation"],
    "308": ["extortion", "punishment for extortion", "putting person in fear of injury", "dishonestly inducing property delivery"],
    "309": ["robbery", "punishment for robbery", "theft when robbery", "extortion when robbery"],
    "310": ["dacoity", "punishment for dacoity", "conjoint robbery five or more persons"],
    "316": ["criminal breach of trust", "misappropriation of entrusted property", "dishonest conversion", "breach of trust punishment"],
    "318": ["cheating", "punishment for cheating", "cheating definition", "deceit", "fraudulently inducing delivery", "dishonest inducement", "cheating and dishonestly inducing delivery of property"],
    "319": ["cheating by personation", "pretending to be someone else cheating"],
    "356": ["defamation", "punishment for defamation", "harming reputation", "defamatory statement", "libel", "slander", "community service for defamation"],
    "4": ["punishments", "types of punishments", "death sentence", "imprisonment for life", "rigorous imprisonment", "simple imprisonment", "forfeiture of property", "fine", "community service"],
    "34": ["private defence", "right of private defence", "defence of body", "defence of property", "justified act"],
}


def clean_content(text: str) -> str:
    """Strip Gazette headers, footers, underlines, and misplaced marginal dumps."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        l = line.strip()
        if not l:
            cleaned.append("")
            continue
        # Gazette header/footer/OCR triggers
        if any(h in l for h in ["EXTRAORDINARY", "PART II", "REGISTERED NO", "xxxGID", "सी.जी.-डी.एल.", "PUBLISHED BY AUTHORITY", "MINISTRY OF LAW", "UPLOADED BY THE MANAGER", "bl Hkkx", "izkf/kdkj"]):
            continue
        if re.match(r"^(?:Sec\.\s*\d+\]|\[Part\s+II|No\.\s*\d+\])", l, re.IGNORECASE):
            continue
        if re.match(r"^(?:NEW\s+DELHI|THE\s+GAZETTE\s+OF\s+INDIA)", l, re.IGNORECASE):
            continue
        if re.match(r"^_{5,}$", l):
            continue
        if re.match(r"^\d{1,3}$", l) and len(l) <= 3:
            continue
        # Marginal text blocks that sometimes leak into raw text
        if l in ["Short title,", "commencement", "and", "application.", "Definitions.", "General", "explanations.", "Punishments.", "Commutation of", "sentence."]:
            continue
        cleaned.append(line)
    res = "\n".join(cleaned).strip()
    return re.sub(r"\n{3,}", "\n\n", res)


def generate_keywords(sec_num: str, title: str, category: str, content: str) -> List[str]:
    """Generate curated search keywords combining domain mappings and title terms."""
    kws = list(OFFENCE_KEYWORD_MAP.get(sec_num, []))
    title_clean = re.sub(r"[^a-zA-Z0-9\s]", " ", title.lower())
    for word in title_clean.split():
        if len(word) > 3 and word not in ["with", "from", "into", "under", "upon", "that", "this", "other", "certain"]:
            if word not in kws:
                kws.append(word)
    return kws[:10]


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Input file not found at: {INPUT_FILE}")

    # Load titles if present
    titles: Dict[str, str] = {}
    if TITLES_FILE.exists():
        with open(TITLES_FILE, "r", encoding="utf-8") as f:
            titles = json.load(f)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    clean_lines = []
    for line in lines:
        if "UPLOADED BY THE MANAGER" in line:
            break
        clean_lines.append(line)
    lines = clean_lines

    sections: List[Dict[str, Any]] = []
    current_chapter = ""
    current_chapter_title = ""
    current_section = None
    current_content = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        chapter_match = re.match(r"CHAPTER\s*([IVXLCDM]+)", line, re.IGNORECASE)
        if chapter_match:
            current_chapter = chapter_match.group(1)
            j = i + 1
            while j < len(lines):
                t = lines[j].strip()
                if t:
                    current_chapter_title = t
                    break
                j += 1
            i += 1
            continue

        section_match = re.match(r"^(\d{1,3})\.\s*(.+)", line)
        if section_match:
            if current_section is not None:
                sections.append({
                    "act": "BNS",
                    "statute": "BNS",
                    "chapter": current_chapter,
                    "chapter_title": current_chapter_title,
                    "offence_category": current_chapter_title,
                    "section": current_section,
                    "section_number": current_section,
                    "title": titles.get(current_section, current_chapter_title),
                    "content": "\n".join(current_content).strip(),
                })
            current_section = section_match.group(1)
            current_content = [section_match.group(2)]
            i += 1
            continue

        if current_section is not None:
            current_content.append(line)
        i += 1

    if current_section is not None:
        sections.append({
            "act": "BNS",
            "statute": "BNS",
            "chapter": current_chapter,
            "chapter_title": current_chapter_title,
            "offence_category": current_chapter_title,
            "section": current_section,
            "section_number": current_section,
            "title": titles.get(current_section, current_chapter_title),
            "content": "\n".join(current_content).strip(),
        })

    # Deduplicate and keep only valid 1..358
    unique_sections = []
    seen = set()
    for s in sections:
        key = (s["chapter"], s["section"])
        if key not in seen and 1 <= int(s["section"]) <= 358:
            seen.add(key)
            cleaned_text = clean_content(s["content"])
            sec_num = str(s["section"])
            title = titles.get(sec_num, s.get("title", s.get("chapter_title", "")))
            category = s.get("chapter_title", "")
            s["content"] = cleaned_text
            s["title"] = title
            s["keywords"] = generate_keywords(sec_num, title, category, cleaned_text)
            unique_sections.append(s)

    unique_sections.sort(key=lambda x: int(x["section"]))

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(unique_sections, f, indent=4, ensure_ascii=False)

    print("=" * 60)
    print(f"Sections Extracted & Cleaned : {len(unique_sections)}")
    print(f"Saved To                    : {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()