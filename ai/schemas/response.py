"""
Response and citation schemas for the LawLense AI layer.

Defines structured Pydantic models for legal assistant responses,
ensuring grounding, citation consistency, and safe refusal states.
"""

import re
from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class Citation(BaseModel):
    """
    Structured citation model representing a referenced legal provision.
    """

    act: str = Field(
        ...,
        description="Name or standard abbreviation of the legal act (e.g., 'BNS', 'BNSS', 'BSA').",
    )
    section: str = Field(
        ...,
        description="Consistent section number or identifier within the act (e.g., '103', '104(1)').",
    )
    title: Optional[str] = Field(
        default=None,
        description="Title or heading of the section if available.",
    )
    supporting_text: Optional[str] = Field(
        default=None,
        description="Direct legal excerpt or evidence from the section supporting the answer.",
    )
    evidence: Optional[str] = Field(
        default=None,
        description="Corpus evidence or excerpt supporting the statement.",
    )
    source: Optional[str] = Field(
        default=None,
        description="Source reference, chapter title, or document URL if available.",
    )
    source_info: Optional[str] = Field(
        default=None,
        description="Additional source metadata or information if available.",
    )

    @field_validator("act")
    @classmethod
    def validate_act(cls, v: Any) -> str:
        """Validate and clean act name."""
        if v is None:
            raise ValueError("Act cannot be None")
        act_str = str(v).strip()
        if not act_str:
            raise ValueError("Act cannot be empty")
        return act_str

    @field_validator("section", mode="before")
    @classmethod
    def normalize_section(cls, v: Any) -> str:
        """
        Normalize section representations consistently.
        Strips whitespace and standardizes prefixes like 'Section 103' -> '103'.
        """
        if v is None:
            raise ValueError("Section cannot be None")
        sec_str = str(v).strip()
        if not sec_str:
            raise ValueError("Section cannot be empty")

        # Strip redundant prefixes like 'Section ' or 'Sec. ' to represent consistently
        cleaned = re.sub(r"^(?:section|sec\.?)\s*", "", sec_str, flags=re.IGNORECASE).strip()
        return cleaned if cleaned else sec_str

    @model_validator(mode="before")
    @classmethod
    def pre_validate_citation(cls, data: Any) -> Any:
        """Support alias field names for source and evidence."""
        if isinstance(data, dict):
            # Map source / source_info / source_url
            src = data.get("source") or data.get("source_info") or data.get("source_url")
            if src:
                data.setdefault("source", src)
                data.setdefault("source_info", src)

            # Map supporting_text / evidence / source_text
            text = (
                data.get("supporting_text")
                or data.get("evidence")
                or data.get("source_text")
            )
            if text:
                data.setdefault("supporting_text", text)
                data.setdefault("evidence", text)
        return data

    @model_validator(mode="after")
    def sync_citation_fields(self) -> "Citation":
        """Ensure bidirectional consistency between supporting_text/evidence and source/source_info."""
        if self.supporting_text and not self.evidence:
            object.__setattr__(self, "evidence", self.supporting_text)
        elif self.evidence and not self.supporting_text:
            object.__setattr__(self, "supporting_text", self.evidence)

        if self.source and not self.source_info:
            object.__setattr__(self, "source_info", self.source)
        elif self.source_info and not self.source:
            object.__setattr__(self, "source", self.source_info)

        return self


class LegalResponse(BaseModel):
    """
    Structured response contract for the LawLense legal assistant.

    Enforces that:
    1. An answer cannot claim to be supported without citations.
    2. Unsupported or refusal responses can contain zero citations.
    3. Section numbers are represented consistently.
    4. Refusal reason and refusal state are accurately tracked.
    """

    query: Optional[str] = Field(
        default=None,
        description="The original user query or prompt.",
    )
    answer: str = Field(
        ...,
        description="The generated legal answer text or explanation.",
    )
    supported: bool = Field(
        ...,
        description="Whether the answer is grounded in and supported by the verified legal corpus.",
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="List of verified legal citations supporting the answer.",
    )
    refusal_reason: Optional[str] = Field(
        default=None,
        description="Reason for refusal when no supporting legal section exists or query is unsupported.",
    )
    is_refusal: bool = Field(
        default=False,
        description="Flag indicating whether the response represents a refusal state.",
    )
    language: Optional[str] = Field(
        default="en",
        description="Language of the response (e.g., 'en' for English, 'ml' for Malayalam).",
    )

    @model_validator(mode="before")
    @classmethod
    def pre_validate_response(cls, data: Any) -> Any:
        """Handle aliases and infer refusal state when applicable."""
        if isinstance(data, dict):
            if "user_query" in data and "query" not in data:
                data["query"] = data["user_query"]
            if "is_refusal" not in data:
                if data.get("refusal_reason") or (data.get("supported") is False):
                    data["is_refusal"] = True
        return data

    @model_validator(mode="after")
    def validate_response_consistency(self) -> "LegalResponse":
        """
        Enforce business constraints on the legal response:
        - An answer cannot claim to be supported without citations.
        - Supported answers cannot have refusal reasons or refusal flags.
        - Unsupported/refusal responses can contain zero citations.
        """
        # An answer cannot claim to be supported without citations
        if self.supported and len(self.citations) == 0:
            raise ValueError("An answer cannot claim to be supported without citations.")

        # A supported answer cannot specify a refusal_reason
        if self.supported and self.refusal_reason:
            raise ValueError("A supported answer cannot specify a refusal_reason.")

        # A supported answer cannot be marked as a refusal
        if self.supported and self.is_refusal:
            raise ValueError("A response cannot be both supported and marked as a refusal.")

        # If unsupported or refusal_reason is set, ensure is_refusal is True
        if (not self.supported or self.refusal_reason) and not self.is_refusal:
            object.__setattr__(self, "is_refusal", True)

        return self

    @property
    def user_query(self) -> Optional[str]:
        """Convenience property for user query."""
        return self.query


# Aliases for project compatibility
LegalAnswer = LegalResponse
Response = LegalResponse
