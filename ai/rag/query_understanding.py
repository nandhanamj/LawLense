"""
Query Understanding and Preprocessing Layer for LawLens.

Performs robust query analysis before retrieval:
- Detects exact section numbers (e.g. "Section 103", "BNS Section 318", "under section 106").
- Detects statute names (BNS, IPC, CrPC, etc.) and enforces metadata scope boundaries.
- Extracts legal offence concepts and domain keywords for hybrid reranking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from typing import List, Optional, Tuple

# Supported statute in the LawLens corpus
SUPPORTED_STATUTE = "BNS"

# Known external / unsupported statutes
UNSUPPORTED_ACT_PATTERNS: List[Tuple[str, str]] = [
    (r"\b(?:IPC|Indian\s+Penal\s+Code)\b", "IPC"),
    (r"\b(?:CrPC|Code\s+of\s+Criminal\s+Procedure)\b", "CrPC"),
    (r"\b(?:CPC|Code\s+of\s+Civil\s+Procedure)\b", "CPC"),
    (r"\b(?:IEA|Indian\s+Evidence\s+Act)\b", "Indian Evidence Act (IEA)"),
    (r"\b(?:Companies\s+Act)\b", "Companies Act"),
    (r"\b(?:Motor\s+Vehicles?\s+Act)\b", "Motor Vehicles Act"),
    (r"\b(?:Income\s+Tax\s+Act)\b", "Income Tax Act"),
    (r"\b(?:Negotiable\s+Instruments?\s+Act)\b", "Negotiable Instruments Act"),
    (r"\b(?:Contract\s+Act|Indian\s+Contract\s+Act)\b", "Indian Contract Act"),
    (r"\b(?:IT\s+Act|Information\s+Technology\s+Act)\b", "Information Technology Act"),
    (r"\b(?:Constitution(?:\s+of\s+India)?)\b", "Constitution of India"),
    (r"\b(?:Hindu\s+Marriage\s+Act)\b", "Hindu Marriage Act"),
    (r"\b(?:POCSO(?:\s+Act)?)\b", "POCSO Act"),
    (r"\b(?:NDPS(?:\s+Act)?)\b", "NDPS Act"),
    (r"\b(?:Consumer\s+Protection\s+Act)\b", "Consumer Protection Act"),
    (r"\b(?:Arbitration(?:\s+and\s+Conciliation)?\s+Act)\b", "Arbitration Act"),
]

# Primary legal offence concept map for category detection
OFFENCE_CATEGORY_TRIGGERS = {
    "theft": "OF OFFENCES AGAINST PROPERTY",
    "stealing": "OF OFFENCES AGAINST PROPERTY",
    "stolen property": "OF OFFENCES AGAINST PROPERTY",
    "snatching": "OF OFFENCES AGAINST PROPERTY",
    "extortion": "OF OFFENCES AGAINST PROPERTY",
    "robbery": "OF OFFENCES AGAINST PROPERTY",
    "dacoity": "OF OFFENCES AGAINST PROPERTY",
    "cheating": "OF OFFENCES AGAINST PROPERTY",
    "fraud": "OF OFFENCES AGAINST PROPERTY",
    "criminal breach of trust": "OF OFFENCES AGAINST PROPERTY",
    "mischief": "OF OFFENCES AGAINST PROPERTY",
    "criminal trespass": "OF OFFENCES AGAINST PROPERTY",
    "murder": "OF OFFENCES AFFECTING THE HUMAN BODY",
    "culpable homicide": "OF OFFENCES AFFECTING THE HUMAN BODY",
    "causing death by negligence": "OF OFFENCES AFFECTING THE HUMAN BODY",
    "negligence": "OF OFFENCES AFFECTING THE HUMAN BODY",
    "rash driving": "OF OFFENCES AFFECTING THE HUMAN BODY",
    "rash act": "OF OFFENCES AFFECTING THE HUMAN BODY",
    "hurt": "OF OFFENCES AFFECTING THE HUMAN BODY",
    "grievous hurt": "OF OFFENCES AFFECTING THE HUMAN BODY",
    "kidnapping": "OF OFFENCES AFFECTING THE HUMAN BODY",
    "abduction": "OF OFFENCES AFFECTING THE HUMAN BODY",
    "assault": "OF OFFENCES AFFECTING THE HUMAN BODY",
    "wrongful restraint": "OF OFFENCES AFFECTING THE HUMAN BODY",
    "wrongful confinement": "OF OFFENCES AFFECTING THE HUMAN BODY",
    "rape": "OF OFFENCES AGAINST WOMEN AND CHILDREN",
    "sexual offences": "OF OFFENCES AGAINST WOMEN AND CHILDREN",
    "dowry death": "OF OFFENCES AGAINST WOMEN AND CHILDREN",
    "private defence": "GENERAL EXCEPTIONS",
    "punishments": "OF PUNISHMENTS",
    "punishment": "OF PUNISHMENTS",
    "defamation": "OF CRIMINAL INTIMIDATION, INSULT, ANNOYANCE, DEFAMATION, ETC.",
    "organised crime": "OF OFFENCES AFFECTING THE HUMAN BODY",
    "petty organised crime": "OF OFFENCES AFFECTING THE HUMAN BODY",
}


@dataclass
class QueryAnalysis:
    """Structured representation of preprocessed query intent and metadata."""

    raw_query: str
    cleaned_query: str
    statute: Optional[str] = None
    is_supported_statute: bool = True
    scope_message: Optional[str] = None
    exact_section: Optional[str] = None
    is_exact_section_query: bool = False
    offence_category: Optional[str] = None
    legal_keywords: List[str] = field(default_factory=list)


class QueryUnderstanding:
    """Preprocessor analyzing query intent, exact section patterns, and statute boundaries."""

    @classmethod
    def detect_statute(cls, query: str) -> Tuple[Optional[str], bool, Optional[str]]:
        """
        Detect whether an unsupported statute is queried.

        Returns:
            Tuple of (statute_name, is_supported, scope_refusal_message).
        """
        # If user explicitly specifies BNS or Bharatiya Nyaya Sanhita, supported
        has_bns = bool(
            re.search(r"\b(?:BNS|Bharatiya\s+Nyaya\s+Sanhita)\b", query, re.IGNORECASE)
        )

        # Check for unsupported acts
        for pattern, act_name in UNSUPPORTED_ACT_PATTERNS:
            if re.search(pattern, query, re.IGNORECASE):
                # If IPC or CrPC mentioned without BNS context
                scope_msg = f"{act_name} is not available. LawLens currently supports BNS only."
                return act_name, False, scope_msg

        if has_bns:
            return "BNS", True, None

        return None, True, None

    @classmethod
    def detect_exact_section(cls, query: str) -> Tuple[Optional[str], bool]:
        """
        Detect if the user query specifies an exact section reference.

        Returns:
            Tuple of (section_number_str, is_primarily_exact_query).
        """
        clean_q = query.strip()

        # Strict exact section patterns
        # 1. "Section 103", "Sec 103", "Sec. 103", "s. 103"
        m = re.search(r"\b(?:section|sec\.?|s\.)\s*(\d+[a-zA-Z]?)\b", clean_q, re.IGNORECASE)
        if m:
            sec_num = m.group(1).upper()
            is_strict = bool(
                re.match(
                    r"^\s*(?:what\s+does\s+)?(?:the\s+)?(?:bns\s+)?(?:section|sec\.?|s\.)\s*\d+[a-zA-Z]?(?:\s+of\s+(?:the\s+)?(?:bns|bharatiya\s+nyaya\s+sanhita))?(?:\s+(?:deal\s+with|provide|state|say|mean))?\??\s*$",
                    clean_q,
                    re.IGNORECASE,
                )
            )
            return sec_num, is_strict

        # 2. "under section 106", "in section 106"
        m = re.search(r"\b(?:under|in)\s+(?:section|sec\.?|s\.)\s*(\d+[a-zA-Z]?)\b", clean_q, re.IGNORECASE)
        if m:
            return m.group(1).upper(), False

        # 3. "BNS Section 318", "BNS 318"
        m = re.search(
            r"\b(?:bns|bharatiya\s+nyaya\s+sanhita)\s+(?:section|sec\.?|s\.)?\s*(\d+[a-zA-Z]?)\b",
            clean_q,
            re.IGNORECASE,
        )
        if m:
            sec_num = m.group(1).upper()
            return sec_num, True

        # 4. "103 of BNS", "304 BNS", "Section 103 BNS"
        m = re.search(
            r"\b(\d+[a-zA-Z]?)\s*(?:of\s+(?:the\s+)?(?:bns|bharatiya\s+nyaya\s+sanhita)|\s+bns)\b",
            clean_q,
            re.IGNORECASE,
        )
        if m:
            return m.group(1).upper(), True

        # 5. Direct standalone number query e.g. "103"
        m = re.match(r"^\s*(\d+[a-zA-Z]?)\s*$", clean_q)
        if m:
            return m.group(1).upper(), True

        return None, False

    @classmethod
    def extract_legal_keywords(cls, query: str) -> List[str]:
        """Extract legal offence terms from query for category matching and lexical filtering."""
        q_lower = query.lower()
        found: List[str] = []
        for trigger in OFFENCE_CATEGORY_TRIGGERS:
            if re.search(rf"\b{re.escape(trigger)}\b", q_lower):
                found.append(trigger)
        return found

    @classmethod
    def detect_offence_category(cls, legal_keywords: List[str]) -> Optional[str]:
        """Map detected keywords to the primary BNS offence category."""
        for kw in legal_keywords:
            cat = OFFENCE_CATEGORY_TRIGGERS.get(kw)
            if cat:
                return cat
        return None

    @classmethod
    def analyze(cls, query: str) -> QueryAnalysis:
        """
        Execute full query understanding pipeline.

        Args:
            query: Raw user query string.

        Returns:
            QueryAnalysis dataclass instance.
        """
        clean_q = query.strip()
        statute, is_supported, scope_msg = cls.detect_statute(clean_q)
        exact_sec, is_exact_q = cls.detect_exact_section(clean_q)
        keywords = cls.extract_legal_keywords(clean_q)
        category = cls.detect_offence_category(keywords)

        return QueryAnalysis(
            raw_query=query,
            cleaned_query=clean_q,
            statute=statute,
            is_supported_statute=is_supported,
            scope_message=scope_msg,
            exact_section=exact_sec,
            is_exact_section_query=is_exact_q,
            offence_category=category,
            legal_keywords=keywords,
        )
