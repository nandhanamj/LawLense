"""
Django management command to seed Bharatiya Nyaya Sanhita (BNS) sections into MySQL.

Loads preprocessed section data from data/processed/bns_sections.json into
the legal Act and Section database models.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from legal.models import Act, Section


def resolve_project_root() -> Path:
    """Robustly resolve the project root directory."""
    if hasattr(settings, "BASE_DIR"):
        base_dir = Path(settings.BASE_DIR).resolve()
        # If BASE_DIR points to backend/, parent is the project root
        if base_dir.name == "backend":
            return base_dir.parent
        return base_dir
    # Fallback relative to this file: backend/legal/management/commands/seed_bns.py -> 5 levels up
    return Path(__file__).resolve().parents[4]


class Command(BaseCommand):
    help = "Seed preprocessed BNS sections from JSON into the MySQL database."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--file",
            type=str,
            default=None,
            help="Optional custom path to bns_sections.json",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        project_root = resolve_project_root()

        # Determine path to bns_sections.json
        custom_file = options.get("file")
        if custom_file:
            data_file = Path(custom_file).resolve()
        else:
            data_file = project_root / "data" / "processed" / "bns_sections.json"

        self.stdout.write(f"Loading BNS corpus from: {data_file}")

        if not data_file.exists():
            raise CommandError(
                f"Source data file does not exist: {data_file}. "
                "Ensure data/processed/bns_sections.json has been generated."
            )

        # 1. Load JSON file using UTF-8
        try:
            with open(data_file, "r", encoding="utf-8") as f:
                sections_data = json.load(f)
        except Exception as err:
            raise CommandError(f"Failed to read JSON from {data_file}: {err}")

        # 2. Validate loaded data
        if not isinstance(sections_data, list) or len(sections_data) == 0:
            raise CommandError(
                f"Invalid data in {data_file}: expected non-empty list of section objects."
            )

        for idx, item in enumerate(sections_data):
            if not isinstance(item, dict):
                raise CommandError(f"Invalid section record at index {idx}: expected dictionary.")
            if "section" not in item or not str(item["section"]).strip():
                raise CommandError(f"Missing or empty 'section' field at index {idx}.")
            if "content" not in item or not str(item["content"]).strip():
                raise CommandError(
                    f"Missing or empty 'content' field at index {idx} (Section {item.get('section')})."
                )

        total_input_sections = len(sections_data)
        self.stdout.write(f"Validated {total_input_sections} section records from JSON.")

        # 3. Database operations inside atomic transaction
        with transaction.atomic():
            # Get or create BNS Act record
            act, act_created = Act.objects.get_or_create(
                short_name="BNS",
                defaults={
                    "name": "Bharatiya Nyaya Sanhita, 2023",
                    "description": (
                        "The Bharatiya Nyaya Sanhita, 2023 (BNS) is the official criminal code "
                        "of the Republic of India, replacing the Indian Penal Code, 1860."
                    ),
                    "source_url": "https://www.mha.gov.in",
                },
            )

            if act_created:
                self.stdout.write(self.style.SUCCESS(f"Created Act record: {act.short_name}"))
            else:
                self.stdout.write(f"Using existing Act record: {act.short_name}")

            created_count = 0
            updated_count = 0

            # Insert or update each section idempotently
            for item in sections_data:
                sec_num = str(item["section"]).strip()
                content = item["content"].strip()

                # Preserve title / chapter information according to model fields
                title = (item.get("title") or item.get("chapter_title") or "").strip()
                if len(title) > 500:
                    title = title[:500]

                source_url = (item.get("source_url") or act.source_url or "").strip()
                if len(source_url) > 200:
                    source_url = source_url[:200]

                section_obj, sec_created = Section.objects.update_or_create(
                    act=act,
                    section_number=sec_num,
                    defaults={
                        "title": title,
                        "text": content,
                        "source_url": source_url,
                    },
                )

                if sec_created:
                    created_count += 1
                else:
                    updated_count += 1

            total_act_sections = Section.objects.filter(act=act).count()

        # 4. Print structured completion summary
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("BNS Corpus Seeding Completed Successfully"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"Source JSON file   : {data_file}")
        self.stdout.write(f"Act                : {act.short_name} ({act.name})")
        self.stdout.write(f"Act record status  : {'Created' if act_created else 'Existing'}")
        self.stdout.write(f"Sections processed : {total_input_sections}")
        self.stdout.write(f"Sections created   : {created_count}")
        self.stdout.write(f"Sections updated   : {updated_count}")
        self.stdout.write(f"Total BNS Sections : {total_act_sections}")
        self.stdout.write(self.style.SUCCESS("=" * 60))
