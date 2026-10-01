"""
Legal Reranking Layer for LawLens.

Reranks top retrieved candidate sections by combining:
- Dense semantic vector similarity
- Exact offence match and primary section relevance
- Same offence category match and chapter coherence
- Lexical BM25 keyword relevance
- Legal domain keyword overlap
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from ai.rag.query_understanding import QueryAnalysis

# Foundational BNS sections for canonical offences
PRIMARY_OFFENCE_MAP: Dict[str, str] = {
    "murder": "103",
    "theft": "303",
    "cheating": "318",
    "snatching": "304",
    "extortion": "308",
    "criminal breach of trust": "316",
    "defamation": "356",
    "kidnapping": "137",
    "abduction": "138",
    "negligence": "106",
    "rash driving": "106",
    "rash act": "106",
    "causing death by negligence": "106",
    "organised crime": "111",
    "petty organised crime": "112",
    "private defence": "34",
    "punishments": "4",
    "rape": "63",
    "robbery": "309",
    "dacoity": "310",
    "forgery": "336",
    "criminal intimidation": "351",
}

# Subcategory clusters mapping offence to related sections
OFFENCE_SUBCATEGORY_MAP: Dict[str, List[str]] = {
    "theft": ["303", "305", "306", "307"],
    "murder": ["103", "101", "100", "104", "105"],
    "snatching": ["304"],
    "cheating": ["318", "319"],
    "extortion": ["308"],
    "criminal breach of trust": ["316", "317"],
    "robbery": ["309", "310", "311", "312", "313"],
    "kidnapping": ["137", "138", "139", "140", "141", "142"],
    "defamation": ["356"],
    "negligence": ["106"],
    "organised crime": ["111", "112"],
    "petty organised crime": ["112"],
    "private defence": ["34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44"],
    "punishments": ["4", "5", "6", "7", "8"],
}


class LegalReranker:
    """Reranker prioritizing exact offence matches, category coherence, and keyword overlap."""

    @classmethod
    def compute_rerank_score(
        cls,
        candidate: Dict[str, Any],
        query: str,
        query_analysis: QueryAnalysis,
    ) -> float:
        """
        Compute final hybrid rerank score for a candidate section.

        Args:
            candidate: Section candidate dictionary with 'section', 'title',
                       'dense_score', 'bm25_score', 'offence_category', 'keywords'.
            query: The user query string.
            query_analysis: QueryAnalysis instance.

        Returns:
            Weighted rerank score float.
        """
        sec_num = str(candidate.get("section") or candidate.get("section_number") or "").strip()
        title = str(candidate.get("title") or "").strip().lower()
        cat = str(candidate.get("offence_category") or candidate.get("chapter_title") or "")
        dense_score = float(candidate.get("dense_score", candidate.get("score", 0.0)))
        bm25_score = float(candidate.get("bm25_score", 0.0))

        # Base score from semantic and lexical signals
        score = 0.45 * dense_score + 0.30 * bm25_score

        # 1. Exact section match (highest priority)
        if query_analysis.exact_section and sec_num == str(query_analysis.exact_section):
            score += 10.0

        # 2. Same offence category match
        if query_analysis.offence_category:
            if cat == query_analysis.offence_category:
                score += 0.25
            else:
                # Penalize sections from unrelated chapters when category is clearly identified
                score -= 0.30

        # 3. Exact offence match & Primary section relevance
        q_lower = query.lower()
        for offence, primary_sec in PRIMARY_OFFENCE_MAP.items():
            if re.search(rf"\b{re.escape(offence)}\b", q_lower):
                if sec_num == primary_sec:
                    # Foundational section for this offence (e.g. 103 for murder, 303 for theft, 318 for cheating)
                    score += 0.65
                elif sec_num in OFFENCE_SUBCATEGORY_MAP.get(offence, []):
                    # Direct statutory subcategory variation (e.g. 305 for theft in dwelling house)
                    score += 0.45
                elif re.search(rf"\b{re.escape(offence)}\b", title):
                    score += 0.15

        # 4. Title relevance match
        if title and title in q_lower:
            score += 0.40
        elif title:
            # Check individual significant words in title
            t_words = [w for w in re.findall(r"[a-zA-Z0-9]+", title) if len(w) > 3]
            matched_words = [w for w in t_words if re.search(rf"\b{re.escape(w)}\b", q_lower)]
            if matched_words:
                score += 0.10 * len(matched_words)

        # 5. Legal keyword overlap
        sec_keywords = [k.lower() for k in (candidate.get("keywords") or [])]
        if sec_keywords and query_analysis.legal_keywords:
            overlap = set(query_analysis.legal_keywords).intersection(set(sec_keywords))
            if overlap:
                score += 0.15 * (len(overlap) / len(query_analysis.legal_keywords))

        return score

    @classmethod
    def rerank(
        cls,
        candidates: List[Dict[str, Any]],
        query: str,
        query_analysis: QueryAnalysis,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Rerank top candidates and prune to top_k most relevant sections.

        Args:
            candidates: Initial pool of retrieved candidate section dictionaries (e.g. top 15).
            query: The user search query.
            query_analysis: QueryAnalysis instance.
            top_k: Desired number of final sections (default 3, up to 5).

        Returns:
            Pruned and reordered list of section dictionaries.
        """
        if not candidates:
            return []

        # If exact section query (e.g. "Section 103 BNS"), return ONLY the exact section
        if query_analysis.exact_section:
            exact_match = next(
                (c for c in candidates if str(c.get("section", "")).strip() == str(query_analysis.exact_section)),
                None,
            )
            if exact_match:
                exact_match["score"] = 1.0
                return [exact_match]

        # Score and rerank all candidates
        scored_candidates = []
        for cand in candidates:
            rerank_score = cls.compute_rerank_score(cand, query, query_analysis)
            cand_copy = dict(cand)
            cand_copy["rerank_score"] = rerank_score
            cand_copy["score"] = round(rerank_score, 4)
            scored_candidates.append(cand_copy)

        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored_candidates[:top_k]
