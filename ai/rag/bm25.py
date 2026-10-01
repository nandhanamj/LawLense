"""
In-memory BM25 (Okapi BM25) implementation for lexical keyword retrieval.

Provides sub-millisecond lexical scoring across all BNS sections without external
dependencies, weighting section titles, legal keywords, numbers, and statutory text.
"""

from __future__ import annotations

from collections import Counter
import math
import re
from typing import Any, Dict, List, Sequence


# Stopwords that dilute legal search relevance
LEGAL_SEARCH_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "is", "are", "was", "were",
    "be", "been", "being", "for", "with", "about", "against", "between", "into",
    "through", "during", "before", "after", "above", "below", "from", "up",
    "down", "on", "off", "over", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "any", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not",
    "only", "own", "same", "so", "than", "too", "very", "can", "will", "just",
    "should", "now", "what", "which", "who", "whom", "this", "that", "these",
    "those", "am", "have", "has", "had", "having", "do", "does", "did", "doing",
    "would", "could", "tell", "me", "provide", "explain", "state", "say", "does",
    "deal", "mean",
}


def tokenize(text: str) -> List[str]:
    """Tokenize legal text into lowercase alphanumeric words, filtering stopwords."""
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    return [w for w in words if len(w) > 1 and w not in LEGAL_SEARCH_STOPWORDS]


class BM25Index:
    """Okapi BM25 index for fast in-memory keyword scoring."""

    def __init__(
        self,
        documents: Sequence[Dict[str, Any]],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        """
        Build BM25 index over BNS section documents.

        Args:
            documents: List of section dicts containing section, title, keywords, content.
            k1: BM25 term frequency saturation parameter.
            b: BM25 document length normalization parameter.
        """
        self.k1 = k1
        self.b = b
        self.corpus_size = len(documents)

        # Build weighted document tokens:
        # Title (weighted 3x), Section number (weighted 3x), Keywords (weighted 2x), Content (1x)
        tokenized_corpus: List[List[str]] = []
        for doc in documents:
            sec_num = str(doc.get("section") or doc.get("section_number") or "")
            title = str(doc.get("title") or "")
            kws = " ".join(doc.get("keywords") or [])
            cat = str(doc.get("offence_category") or doc.get("chapter_title") or "")
            content = str(doc.get("content") or doc.get("text") or "")

            title_tokens = tokenize(title) * 3
            sec_tokens = tokenize(f"section {sec_num}") * 3
            kws_tokens = tokenize(kws) * 2
            cat_tokens = tokenize(cat)
            content_tokens = tokenize(content)

            combined_tokens = title_tokens + sec_tokens + kws_tokens + cat_tokens + content_tokens
            tokenized_corpus.append(combined_tokens)

        self.doc_lens = [len(doc) for doc in tokenized_corpus]
        self.avgdl = (
            sum(self.doc_lens) / self.corpus_size if self.corpus_size > 0 else 1.0
        )

        self.doc_freqs: List[Counter[str]] = []
        self.idf: Dict[str, float] = {}
        df: Counter[str] = Counter()

        for doc_tokens in tokenized_corpus:
            doc_set = set(doc_tokens)
            for word in doc_set:
                df[word] += 1
            self.doc_freqs.append(Counter(doc_tokens))

        for word, freq in df.items():
            # Standard Lucene/BM25 IDF
            self.idf[word] = math.log(
                (self.corpus_size - freq + 0.5) / (freq + 0.5) + 1.0
            )

    def get_scores(self, query: str) -> List[float]:
        """Compute raw Okapi BM25 scores for a query across all indexed documents."""
        q_tokens = tokenize(query)
        scores = [0.0] * self.corpus_size
        if not q_tokens or self.corpus_size == 0:
            return scores

        for word in q_tokens:
            if word not in self.idf:
                continue
            idf_val = self.idf[word]
            for i, doc_freq in enumerate(self.doc_freqs):
                tf = doc_freq.get(word, 0)
                if tf == 0:
                    continue
                denom = tf + self.k1 * (
                    1 - self.b + self.b * (self.doc_lens[i] / self.avgdl)
                )
                score = idf_val * (tf * (self.k1 + 1)) / denom
                scores[i] += score

        return scores

    def get_normalized_scores(self, query: str) -> List[float]:
        """Compute min-max normalized BM25 scores in range [0, 1]."""
        raw_scores = self.get_scores(query)
        max_score = max(raw_scores) if raw_scores else 0.0
        if max_score <= 0.0:
            return [0.0] * self.corpus_size
        return [s / max_score for s in raw_scores]
