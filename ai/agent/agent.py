"""
Legal chatbot agent for LawLense.

Connects SemanticRetriever, deterministic section lookup, and CitationValidator
to produce validated, grounded LegalResponse outputs conforming to Pydantic schemas.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional, Union

from ai.rag.retriever import SemanticRetriever
from ai.schemas.response import Citation, LegalResponse
from ai.tools.citation_validator import CitationValidator
from ai.tools.section_lookup import lookup_section
from ai.llm.groq_client import GroqLegalClient

logger = logging.getLogger(__name__)

# Known external statutes outside the BNS corpus
UNSUPPORTED_ACT_PATTERNS = [
    (r"\b(?:IPC|Indian\s+Penal\s+Code)\b", "Indian Penal Code (IPC)"),
    (r"\b(?:CrPC|Code\s+of\s+Criminal\s+Procedure)\b", "Code of Criminal Procedure (CrPC)"),
    (r"\b(?:CPC|Code\s+of\s+Civil\s+Procedure)\b", "Code of Civil Procedure (CPC)"),
    (r"\b(?:IEA|Indian\s+Evidence\s+Act)\b", "Indian Evidence Act (IEA)"),
    (r"\b(?:Companies\s+Act)\b", "Companies Act"),
    (r"\b(?:Motor\s+Vehicles?\s+Act)\b", "Motor Vehicles Act"),
    (r"\b(?:Income\s+Tax\s+Act)\b", "Income Tax Act"),
    (r"\b(?:Negotiable\s+Instruments?\s+Act)\b", "Negotiable Instruments Act"),
    (r"\b(?:Contract\s+Act)\b", "Indian Contract Act"),
    (r"\b(?:IT\s+Act|Information\s+Technology\s+Act)\b", "Information Technology Act"),
    (r"\b(?:Constitution(?:\s+of\s+India)?)\b", "Constitution of India"),
    (r"\b(?:Hindu\s+Marriage\s+Act)\b", "Hindu Marriage Act"),
    (r"\b(?:POCSO(?:\s+Act)?)\b", "POCSO Act"),
    (r"\b(?:NDPS(?:\s+Act)?)\b", "NDPS Act"),
    (r"\b(?:Consumer\s+Protection\s+Act)\b", "Consumer Protection Act"),
    (r"\b(?:Arbitration(?:\s+and\s+Conciliation)?\s+Act)\b", "Arbitration Act"),
]


class LegalAgent:
    """
    Legal assistant agent connecting retrieval, section lookup, and citation validation.

    Guarantees:
    - Grounding in the BNS corpus without hallucination.
    - Deterministic section lookup when specific sections are queried.
    - Semantic vector retrieval for natural-language questions.
    - Rigorous citation validation before any supported response is returned.
    - Graceful refusal responses conforming to Pydantic schemas when provisions cannot be verified.
    """

    def __init__(
        self,
        retriever: Optional[SemanticRetriever] = None,
        lookup_fn: Optional[
            Callable[[Union[str, int], str], Optional[Dict[str, Any]]]
        ] = None,
        validator: Optional[CitationValidator] = None,
        llm_client: Optional[GroqLegalClient] = None,
    ) -> None:
        """
        Initialize the legal agent.

        Args:
            retriever: Optional SemanticRetriever instance (lazy loaded if None).
            lookup_fn: Optional section lookup callable (defaults to lookup_section).
            validator: Optional CitationValidator instance (defaults to CitationValidator with lookup_fn).
            llm_client: Optional GroqLegalClient instance (lazy loaded if None).
        """
        self._retriever = retriever
        self.lookup_fn = lookup_fn or lookup_section
        self.validator = validator or CitationValidator(lookup_fn=self.lookup_fn)
        self._llm_client = llm_client
        self.last_llm_metadata: Optional[Dict[str, Any]] = None

    @property
    def llm_client(self) -> GroqLegalClient:
        """Lazy load Groq LLM client."""
        if self._llm_client is None:
            self._llm_client = GroqLegalClient()
        return self._llm_client

    @property
    def retriever(self) -> SemanticRetriever:
        """Lazy load retriever to avoid unnecessary overhead if not needed immediately."""
        if self._retriever is None:
            self._retriever = SemanticRetriever()
        return self._retriever

    def _detect_unsupported_act(self, query: str) -> Optional[str]:
        """Detect if the query explicitly asks about an unsupported legal act outside BNS."""
        # If user explicitly asks about BNS, do not treat as unsupported
        if re.search(r"\b(?:BNS|Bharatiya\s+Nyaya\s+Sanhita)\b", query, re.IGNORECASE):
            return None

        for pattern, act_name in UNSUPPORTED_ACT_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                return act_name

        return None

    def _extract_exact_section(self, query: str) -> Optional[str]:
        """Extract an exact section reference from the user query if present."""
        # Match expressions like "Section 103", "Sec. 103", "Sec 103", "s. 103"
        match = re.search(
            r"\b(?:section|sec\.?|s\.)\s*(\d+[a-zA-Z]?)\b",
            query,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).upper()

        # Match direct numeric query like "103" or "103A"
        direct_match = re.match(r"^\s*(\d+[a-zA-Z]?)\s*$", query)
        if direct_match:
            return direct_match.group(1).upper()

        return None

    def _format_grounded_answer(
        self,
        sections: List[Dict[str, Any]],
    ) -> str:
        """Format an objective statutory explanation without legal advice."""
        lines = ["Based on the provisions of the Bharatiya Nyaya Sanhita, 2023 (BNS):\n"]
        for sec in sections:
            sec_num = sec.get("section")
            title = sec.get("title")
            content = (sec.get("content") or sec.get("text") or "").strip()

            header = f"• Section {sec_num}"
            if title:
                header += f" ({title})"
            lines.append(f"{header}:")
            lines.append(f"  {content}\n")

        lines.append(
            "Disclaimer: This response provides objective legal information from the statutory "
            "text of the BNS and does not constitute formal legal advice."
        )
        return "\n".join(lines)
    def _generate_llm_answer(
        self,
        query: str,
        sections: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generate a natural-language answer from verified legal evidence via Groq LLM.
        Captures token counts, latency, and cost info in self.last_llm_metadata.
        """
        try:
            result = self.llm_client.generate(query=query, evidence=sections)
            self.last_llm_metadata = result
            return result
        except Exception as err:
            logger.error("Failed to invoke Groq LLM: %s", err)
            fallback_res = {
                "answer": "",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                "cost": {"total_cost_usd": None, "pricing_configured": False},
                "model": getattr(self.llm_client, "model", "openai/gpt-oss-20b"),
                "latency_seconds": 0.0,
                "success": False,
                "error": str(err),
            }
            self.last_llm_metadata = fallback_res
            return fallback_res

    def _generate_grounded_response_text(
        self,
        query: str,
        verified_sections: List[Dict[str, Any]],
    ) -> str:
        """
        Generate natural-language explanation using Groq LLM backed by verified BNS evidence.
        Falls back safely to structured statutory text if Groq fails or returns empty.
        """
        llm_res = self._generate_llm_answer(query=query, sections=verified_sections)
        llm_answer = (llm_res.get("answer") or "").strip()

        if llm_res.get("success") and llm_answer:
            # Ensure statutory disclaimer is present in the response
            if "does not constitute formal legal advice" not in llm_answer.lower():
                llm_answer = (
                    f"{llm_answer}\n\nDisclaimer: This response provides objective legal "
                    f"information from the statutory text of the BNS and does not constitute formal legal advice."
                )
            return llm_answer

        # Fallback if Groq call failed or returned empty
        err_msg = llm_res.get("error") or "Language generation returned an empty response."
        logger.warning(
            "Groq language generation failed (%s). Falling back to verified statutory text.",
            err_msg,
        )
        grounded_fallback = self._format_grounded_answer(verified_sections)
        return (
            "Note: Language generation service was unavailable. "
            f"Displaying verified statutory text fallback.\n\n{grounded_fallback}"
        )

    def ask(self, query: str) -> LegalResponse:
        """
        Process a user's legal question and return a validated LegalResponse.

        Args:
            query: The user's input legal question or section reference.

        Returns:
            Validated Pydantic LegalResponse instance.
        """
        # 1. Handle empty / whitespace query safely
        if not query or not isinstance(query, str) or not query.strip():
            return LegalResponse(
                query=query if isinstance(query, str) else "",
                answer="Please provide a valid, non-empty legal question or section query.",
                supported=False,
                citations=[],
                refusal_reason="Empty or whitespace query provided.",
                is_refusal=True,
            )

        clean_query = query.strip()

        # 2. Check for unsupported legal acts outside BNS
        unsupported_act = self._detect_unsupported_act(clean_query)
        if unsupported_act:
            return LegalResponse(
                query=clean_query,
                answer=(
                    f"The LawLense assistant currently only supports provisions from the "
                    f"Bharatiya Nyaya Sanhita, 2023 (BNS). The requested statute ({unsupported_act}) "
                    f"is not present in our legal corpus."
                ),
                supported=False,
                citations=[],
                refusal_reason=f"Statute '{unsupported_act}' is not present in the BNS legal corpus.",
                is_refusal=True,
            )

        # 3. Check for exact section lookup route
        exact_section = self._extract_exact_section(clean_query)
        if exact_section:
            # Check known bounds: BNS only contains sections 1 to 358
            try:
                sec_int = int(re.sub(r"[a-zA-Z]", "", exact_section))
                if sec_int < 1 or sec_int > 358:
                    return LegalResponse(
                        query=clean_query,
                        answer=(
                            f"Section {exact_section} does not exist in the Bharatiya Nyaya Sanhita, 2023 (BNS). "
                            f"The BNS corpus contains Sections 1 through 358."
                        ),
                        supported=False,
                        citations=[],
                        refusal_reason=f"Section {exact_section} does not exist in the BNS legal corpus.",
                        is_refusal=True,
                    )
            except ValueError:
                pass

            # Query database via lookup_fn
            db_record = self.lookup_fn(section=exact_section, act="BNS")

            if db_record is None:
                # Differentiate unseeded database from nonexistent section
                return LegalResponse(
                    query=clean_query,
                    answer=(
                        f"Unable to retrieve Section {exact_section} from the database. "
                        f"The BNS section records have not yet been seeded into MySQL."
                    ),
                    supported=False,
                    citations=[],
                    refusal_reason="BNS section data has not yet been seeded into MySQL.",
                    is_refusal=True,
                )

            # Build candidate citation
            content_text = db_record.get("content") or db_record.get("text") or ""
            citation = Citation(
                act=db_record.get("act", "BNS"),
                section=str(db_record["section"]),
                title=db_record.get("title"),
                supporting_text=content_text,
                source=db_record.get("source_url") or "BNS Official Gazette",
            )

            # Validate citation
            validation = self.validator.validate([citation])
            if not validation.get("valid", False):
                return LegalResponse(
                    query=clean_query,
                    answer=f"Citation validation failed for Section {exact_section}.",
                    supported=False,
                    citations=[],
                    refusal_reason="Citation validation failed.",
                    is_refusal=True,
                )

            # Validated exact section answer via Groq LLM (with fallback to statutory text)
            grounded_answer = self._generate_grounded_response_text(clean_query, [db_record])
            return LegalResponse(
                query=clean_query,
                answer=grounded_answer,
                supported=True,
                citations=[citation],
                is_refusal=False,
            )

        # 4. Semantic retrieval route for natural-language questions
        try:
            results = self.retriever.search(clean_query, top_k=3, min_score=0.4)
        except Exception as err:
            return LegalResponse(
                query=clean_query,
                answer="An error occurred while retrieving relevant legal sections.",
                supported=False,
                citations=[],
                refusal_reason=f"Retrieval error: {err}",
                is_refusal=True,
            )

        if not results:
            return LegalResponse(
                query=clean_query,
                answer="No relevant legal provisions could be found in the Bharatiya Nyaya Sanhita (BNS) corpus for your query.",
                supported=False,
                citations=[],
                refusal_reason="No supporting legal sections found in retrieval.",
                is_refusal=True,
            )

        # Attempt to verify candidate sections against MySQL lookup
        verified_sections: List[Dict[str, Any]] = []
        candidate_citations: List[Citation] = []

        for item in results:
            sec_num = str(item.get("section", "")).strip()
            if not sec_num:
                continue

            db_record = self.lookup_fn(section=sec_num, act="BNS")
            if db_record is not None:
                verified_sections.append(db_record)
                candidate_citations.append(
                    Citation(
                        act=db_record.get("act", "BNS"),
                        section=str(db_record["section"]),
                        title=db_record.get("title") or item.get("title"),
                        supporting_text=db_record.get("content") or db_record.get("text"),
                        source=db_record.get("source_url") or "BNS Official Gazette",
                    )
                )

        # If database records are missing (e.g., MySQL not yet seeded)
        if not verified_sections:
            return LegalResponse(
                query=clean_query,
                answer=(
                    "Relevant provisions were identified via semantic retrieval, but database verification "
                    "failed because BNS section records have not yet been seeded into MySQL."
                ),
                supported=False,
                citations=[],
                refusal_reason="BNS section data has not yet been seeded into MySQL.",
                is_refusal=True,
            )

        # Run candidate citations through CitationValidator
        validation = self.validator.validate(candidate_citations)
        valid_items = validation.get("valid_citations", [])

        if not valid_items:
            return LegalResponse(
                query=clean_query,
                answer="No supporting legal citations could be verified for this question.",
                supported=False,
                citations=[],
                refusal_reason="Citation validation failed for all candidate sections.",
                is_refusal=True,
            )

        # Build final validated citations (ensuring no unsupported citations reach client)
        final_citations: List[Citation] = [
            Citation(
                act=item["act"],
                section=item["section"],
                title=item.get("title"),
                supporting_text=item.get("supporting_text") or item.get("content"),
                source=item.get("source_url") or item.get("source"),
            )
            for item in valid_items
        ]

        # Filter verified sections to match valid citations
        valid_sec_numbers = {str(c.section).strip() for c in final_citations}
        final_sections = [
            s for s in verified_sections if str(s.get("section", "")).strip() in valid_sec_numbers
        ]

        # Validated semantic retrieval answer via Groq LLM (with fallback to statutory text)
        grounded_answer = self._generate_grounded_response_text(clean_query, final_sections)

        return LegalResponse(
            query=clean_query,
            answer=grounded_answer,
            supported=True,
            citations=final_citations,
            is_refusal=False,
        )

    def __call__(self, query: str) -> LegalResponse:
        """Make the agent instance directly callable."""
        return self.ask(query)
