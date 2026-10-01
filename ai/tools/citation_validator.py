"""
Citation validation tool for the LawLens legal chatbot guardrail.

Verifies that citations generated in legal responses deterministically exist
in the legal corpus via SectionLookup and that supporting evidence matches.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Union

from ai.schemas.response import Citation
from ai.tools.section_lookup import lookup_section


class CitationResult(dict):
    """Dictionary representing a successfully validated citation with attribute access."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'CitationResult' object has no attribute '{name}'")


class InvalidCitationResult(dict):
    """Dictionary representing an invalid citation with reason and attribute access."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(
                f"'InvalidCitationResult' object has no attribute '{name}'"
            )


def _normalize_whitespace(text: str) -> str:
    """Normalize text whitespace and characters for content containment verification."""
    if not text:
        return ""
    # Normalize newlines, tabs, and common typography variations
    cleaned = (
        text.replace("\r\n", " ")
        .replace("\r", " ")
        .replace("\n", " ")
        .replace("\t", " ")
        .replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("—", "-")
        .replace("––", "-")
    )
    return " ".join(cleaned.split())


class CitationValidator:
    """
    Guardrail tool that verifies citations against the legal corpus.

    Ensures that:
    1. The referenced Act exists.
    2. The referenced Section exists in the Act.
    3. The returned database section corresponds to the requested act and section.
    4. Any provided supporting text or evidence is present in the statutory text.
    5. Nonexistent sections (e.g. Section 999) or acts are rejected.
    6. Duplicate citations are detected and reported deterministically.
    """

    def __init__(
        self,
        lookup_fn: Optional[
            Callable[[Union[str, int], str], Optional[Dict[str, Any]]]
        ] = None,
    ) -> None:
        """
        Initialize CitationValidator.

        Args:
            lookup_fn: Optional custom section lookup function. Defaults to lookup_section.
        """
        self.lookup_fn = lookup_fn or lookup_section

    def validate_single(
        self,
        citation: Any,
    ) -> tuple[bool, Optional[CitationResult], Optional[InvalidCitationResult]]:
        """
        Validate a single citation independently.

        Returns:
            Tuple of (is_valid, valid_result, invalid_result).
        """
        act: Optional[str] = None
        section: Optional[Any] = None
        supporting_text: Optional[str] = None

        if isinstance(citation, Citation):
            act = citation.act
            section = citation.section
            supporting_text = citation.supporting_text or citation.evidence
        elif isinstance(citation, dict):
            act = citation.get("act")
            section = citation.get("section")
            supporting_text = (
                citation.get("supporting_text")
                or citation.get("evidence")
                or citation.get("source_text")
            )
        else:
            reason = (
                f"Invalid citation data: expected Citation instance or dict, got "
                f"{type(citation).__name__}."
            )
            return (
                False,
                None,
                InvalidCitationResult(act=None, section=None, reason=reason),
            )

        # Validate presence of act
        if act is None or not isinstance(act, str) or not act.strip():
            reason = "Invalid citation: Act is missing, empty, or not a string."
            return (
                False,
                None,
                InvalidCitationResult(
                    act=act if isinstance(act, str) else None,
                    section=str(section) if section is not None else None,
                    reason=reason,
                ),
            )

        # Validate presence of section
        if section is None or (isinstance(section, str) and not section.strip()):
            reason = "Invalid citation: Section number is missing or empty."
            return (
                False,
                None,
                InvalidCitationResult(
                    act=act.strip(),
                    section=None,
                    reason=reason,
                ),
            )

        act_clean = act.strip()
        sec_input = section.strip() if isinstance(section, str) else section

        # Deterministic section lookup via lookup_fn
        try:
            db_record = self.lookup_fn(section=sec_input, act=act_clean)
        except ValueError as err:
            reason = f"Invalid section or act format: {err}"
            return (
                False,
                None,
                InvalidCitationResult(
                    act=act_clean,
                    section=str(sec_input),
                    reason=reason,
                ),
            )
        except Exception as err:
            reason = f"Section lookup failed: {err}"
            return (
                False,
                None,
                InvalidCitationResult(
                    act=act_clean,
                    section=str(sec_input),
                    reason=reason,
                ),
            )

        # A citation is valid only when the referenced section exists in the corpus
        if db_record is None:
            reason = (
                f"Section '{sec_input}' of Act '{act_clean}' does not exist in the legal corpus."
            )
            return (
                False,
                None,
                InvalidCitationResult(
                    act=act_clean,
                    section=str(sec_input),
                    reason=reason,
                ),
            )

        # Verify returned Act corresponds to the requested act
        db_act = str(db_record.get("act", "")).strip().upper()
        if db_act and db_act != act_clean.upper():
            reason = (
                f"Act mismatch: requested '{act_clean}', but retrieved record belongs to '{db_act}'."
            )
            return (
                False,
                None,
                InvalidCitationResult(
                    act=act_clean,
                    section=str(sec_input),
                    reason=reason,
                ),
            )

        # Verify supporting_text / evidence if provided
        if supporting_text and str(supporting_text).strip():
            supp_norm = _normalize_whitespace(str(supporting_text))
            content_val = db_record.get("content") or db_record.get("text") or ""
            content_norm = _normalize_whitespace(str(content_val))

            if supp_norm.lower() not in content_norm.lower():
                sec_display = str(db_record.get("section", sec_input))
                reason = (
                    f"Supporting text is not present in the verified legal text of "
                    f"{act_clean} Section {sec_display}."
                )
                return (
                    False,
                    None,
                    InvalidCitationResult(
                        act=act_clean,
                        section=sec_display,
                        reason=reason,
                    ),
                )

        valid_res = CitationResult(
            act=db_record.get("act", act_clean),
            section=str(db_record.get("section", sec_input)),
            title=db_record.get("title"),
            content=db_record.get("content") or db_record.get("text"),
            source_url=db_record.get("source_url"),
            supporting_text=str(supporting_text).strip() if supporting_text else None,
        )
        return True, valid_res, None

    def validate(
        self,
        citations: Any,
        allow_duplicates: bool = False,
    ) -> Dict[str, Any]:
        """
        Validate a list of citations or a single citation.

        Args:
            citations: A Citation instance, a dict, a LegalResponse, or a list of citations.
            allow_duplicates: If False, duplicate citations are reported as invalid.

        Returns:
            Dictionary with structure:
            {
                "valid": bool,
                "citations_checked": int,
                "valid_citations": [...],
                "invalid_citations": [...],
                "duplicates": [...],
                "errors": [...]
            }
        """
        if citations is None:
            citation_list = []
        elif hasattr(citations, "citations") and isinstance(citations.citations, list):
            citation_list = list(citations.citations)
        elif isinstance(citations, (list, tuple)):
            citation_list = list(citations)
        else:
            citation_list = [citations]

        valid_citations: List[CitationResult] = []
        invalid_citations: List[InvalidCitationResult] = []
        duplicates: List[Dict[str, Any]] = []
        errors: List[str] = []

        seen_keys: set[tuple[str, str]] = set()

        for item in citation_list:
            is_valid, valid_item, invalid_item = self.validate_single(item)

            if is_valid and valid_item is not None:
                key = (
                    valid_item["act"].upper(),
                    str(valid_item["section"]).strip().upper(),
                )
                if key in seen_keys:
                    dup_info = {
                        "act": valid_item["act"],
                        "section": valid_item["section"],
                        "reason": (
                            f"Duplicate citation for Act '{valid_item['act']}' "
                            f"Section '{valid_item['section']}'."
                        ),
                    }
                    duplicates.append(dup_info)
                    if not allow_duplicates:
                        invalid_citations.append(InvalidCitationResult(**dup_info))
                        errors.append(dup_info["reason"])
                else:
                    seen_keys.add(key)
                    valid_citations.append(valid_item)
            else:
                if invalid_item is not None:
                    invalid_citations.append(invalid_item)
                    errors.append(invalid_item["reason"])

        overall_valid = len(invalid_citations) == 0

        return {
            "valid": overall_valid,
            "citations_checked": len(citation_list),
            "valid_citations": valid_citations,
            "invalid_citations": invalid_citations,
            "duplicates": duplicates,
            "errors": errors,
        }


def validate_citations(
    citations: Any,
    lookup_fn: Optional[
        Callable[[Union[str, int], str], Optional[Dict[str, Any]]]
    ] = None,
    allow_duplicates: bool = False,
) -> Dict[str, Any]:
    """
    Convenience function to validate citations against the legal corpus.

    Args:
        citations: List of citations, single citation, or LegalResponse to validate.
        lookup_fn: Optional lookup function overriding SectionLookup.
        allow_duplicates: Whether to permit duplicate citations without marking them invalid.

    Returns:
        Structured validation dictionary.
    """
    validator = CitationValidator(lookup_fn=lookup_fn)
    return validator.validate(citations=citations, allow_duplicates=allow_duplicates)
