"""Deterministic section lookup tool querying legal provisions from MySQL via Django ORM."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any


def _ensure_django_setup() -> None:
    """Ensure Django settings and apps are initialized before ORM operations."""
    backend_dir = Path(__file__).resolve().parent.parent.parent / "backend"
    backend_str = str(backend_dir)
    if backend_str not in sys.path:
        sys.path.insert(0, backend_str)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    import django
    from django.apps import apps

    if not apps.ready:
        django.setup()


_ensure_django_setup()

from django.db import models
from legal.models import Act, Section


class SectionLookup:
    """Deterministic section lookup tool for legal provisions stored in MySQL."""

    def __init__(self) -> None:
        _ensure_django_setup()

    @staticmethod
    def normalize_section(section: str | int) -> str:
        """Normalize section input to a standardized section number string.

        Accepts:
            - int (e.g. 103)
            - str digits (e.g. "103", " 103 ")
            - str with prefixes (e.g. "Section 103", "Sec. 103", "Sec 103", "sec. 103")
            - alphanumeric sections (e.g. "103A", "Section 103A", "Section 103 A")

        Raises:
            ValueError: If input is empty, whitespace, an invalid type, or not a recognizable section number.
        """
        if isinstance(section, bool) or not isinstance(section, (str, int)):
            raise ValueError(
                f"Invalid section type: expected str or int, got {type(section).__name__}."
            )

        if isinstance(section, int):
            if section <= 0:
                raise ValueError(
                    f"Invalid section number: {section}. Section number must be positive."
                )
            return str(section)

        sec_str = section.strip()
        if not sec_str:
            raise ValueError("Section cannot be empty or whitespace only.")

        # Pattern for "Section 103", "Sec. 103", "Sec 103", "Section 103A", "Section 103 A"
        pattern = r"^(?:section|sec\.?)\s*(\d+)\s*([a-zA-Z]?)$"
        match = re.match(pattern, sec_str, re.IGNORECASE)
        if match:
            num = str(int(match.group(1)))
            suffix = match.group(2).upper()
            return f"{num}{suffix}"

        # Direct pattern for "103", "0103", "103A", "103 A"
        direct_pattern = r"^(\d+)\s*([a-zA-Z]?)$"
        direct_match = re.match(direct_pattern, sec_str)
        if direct_match:
            num = str(int(direct_match.group(1)))
            suffix = direct_match.group(2).upper()
            return f"{num}{suffix}"

        raise ValueError(
            f"Invalid section input: {section!r}. Expected a valid section number."
        )

    @staticmethod
    def normalize_act(act: str) -> str:
        """Normalize act name/abbreviation input.

        Raises:
            ValueError: If act is empty, whitespace, or not a string.
        """
        if act is None or not isinstance(act, str):
            raise ValueError(
                f"Invalid act type: expected str, got {type(act).__name__}."
            )

        act_clean = act.strip()
        if not act_clean:
            raise ValueError("Act cannot be empty or whitespace only.")

        return act_clean

    def lookup(
        self,
        section: str | int,
        act: str = "BNS",
    ) -> dict[str, Any] | None:
        """Look up a legal section deterministically from MySQL via Django ORM.

        Args:
            section: Section number as int or str (e.g., 103, "103", " Section 103 ", "Sec. 103").
            act: Act short name or full name (default "BNS").

        Returns:
            Dictionary with section details from the database if found, or None if the Act
            or Section does not exist. Does not fabricate data.
        """
        normalized_section = self.normalize_section(section)
        normalized_act = self.normalize_act(act)

        # Find corresponding Act (case-insensitive by short_name or full name)
        act_obj = Act.objects.filter(
            models.Q(short_name__iexact=normalized_act)
            | models.Q(name__iexact=normalized_act)
        ).first()

        if act_obj is None:
            return None

        # Find Section belonging to the Act using exact section_number matching
        section_obj = Section.objects.filter(
            act=act_obj,
            section_number=normalized_section,
        ).first()

        if section_obj is None:
            return None

        return {
            "act": act_obj.short_name,
            "section": section_obj.section_number,
            "title": section_obj.title,
            "content": section_obj.text,
            "source_url": section_obj.source_url,
        }


def lookup_section(section: str | int, act: str = "BNS") -> dict[str, Any] | None:
    """Convenience function for deterministic legal section lookup."""
    return SectionLookup().lookup(section=section, act=act)
