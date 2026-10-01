"""
Hybrid RAG retrieval module for the Bharatiya Nyaya Sanhita (BNS) corpus.

Combines:
1. Query Understanding Layer (exact section numbers, statute detection, legal keywords).
2. Metadata Filtering (statute scope boundaries).
3. Hybrid Search (dense multilingual-e5-base embeddings + BM25Okapi lexical matching).
4. Legal Reranking Layer (exact offence matching, category coherence, keyword overlap).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import numpy as np
from sentence_transformers import SentenceTransformer

from ai.rag.bm25 import BM25Index
from ai.rag.query_understanding import QueryAnalysis, QueryUnderstanding
from ai.rag.reranker import LegalReranker

logger = logging.getLogger(__name__)

# Resolve project root (3 levels up: ai/rag/retriever.py -> ai/rag -> ai -> LawLens)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class SemanticRetriever:
    """
    Production-grade Hybrid Retriever for the BNS legal corpus.

    Integrates query understanding, exact section routing, statute metadata filtering,
    dense vector similarity, BM25 lexical keyword matching, and legal domain reranking.
    """

    def __init__(
        self,
        embeddings_path: Optional[Union[Path, str]] = None,
        metadata_path: Optional[Union[Path, str]] = None,
        sections_path: Optional[Union[Path, str]] = None,
        model_name: str = "intfloat/multilingual-e5-base",
    ):
        """
        Initialize the hybrid retriever and load corpus embeddings/metadata.

        Args:
            embeddings_path: Path to the .npz embeddings file.
            metadata_path: Path to the bns_metadata.json file.
            sections_path: Path to the bns_sections.json file.
            model_name: Hugging Face model identifier for query embedding.
        """
        self.embeddings_path = (
            Path(embeddings_path).resolve()
            if embeddings_path
            else PROJECT_ROOT / "data" / "processed" / "bns_embeddings.npz"
        )
        self.metadata_path = (
            Path(metadata_path).resolve()
            if metadata_path
            else PROJECT_ROOT / "data" / "processed" / "bns_metadata.json"
        )
        self.sections_path = (
            Path(sections_path).resolve()
            if sections_path
            else PROJECT_ROOT / "data" / "processed" / "bns_sections.json"
        )
        self.model_name = model_name

        # Validate existence of input files
        if not self.embeddings_path.exists():
            raise FileNotFoundError(
                f"BNS embeddings file not found at: {self.embeddings_path}"
            )
        if not self.metadata_path.exists():
            raise FileNotFoundError(
                f"BNS metadata file not found at: {self.metadata_path}"
            )
        if not self.sections_path.exists():
            raise FileNotFoundError(
                f"BNS sections file not found at: {self.sections_path}"
            )

        # 1. Load dense vector embeddings (.npz)
        embeddings_data = np.load(self.embeddings_path)
        if "embeddings" in embeddings_data:
            self.embeddings = np.array(embeddings_data["embeddings"], dtype=np.float32)
        elif len(embeddings_data.files) > 0:
            self.embeddings = np.array(
                embeddings_data[embeddings_data.files[0]], dtype=np.float32
            )
        else:
            raise ValueError(f"No arrays found in embeddings file: {self.embeddings_path}")

        # 2. Load metadata (.json)
        with open(self.metadata_path, "r", encoding="utf-8") as f:
            self.metadata: List[Dict[str, Any]] = json.load(f)

        # 3. Load sections (.json)
        with open(self.sections_path, "r", encoding="utf-8") as f:
            self.sections: List[Dict[str, Any]] = json.load(f)

        # Build lookup table by section number
        self.sections_by_number: Dict[str, Dict[str, Any]] = {
            str(s.get("section") or s.get("section_number", "")).strip(): s
            for s in self.sections
        }

        # 4. Initialize in-memory BM25 index over rich metadata
        self.bm25_index = BM25Index(self.metadata)

        # 5. Load embedding model once
        self.model = SentenceTransformer(self.model_name)

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        min_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Execute full retrieval pipeline with structured status output.

        Returns:
            Dictionary containing:
            - 'status': 'success' | 'out_of_scope' | 'not_found'
            - 'scope_message': Optional scope refusal explanation
            - 'query_analysis': QueryAnalysis dataclass instance
            - 'sections': List of retrieved section dicts
        """
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query must be a non-empty string.")

        analysis = QueryUnderstanding.analyze(query)

        # 1. Metadata Filtering: Statute boundary check
        if not analysis.is_supported_statute:
            return {
                "status": "out_of_scope",
                "scope_message": analysis.scope_message,
                "query_analysis": analysis,
                "sections": [],
            }

        # 2. Execute hybrid search and reranking
        results = self.search(
            query=query,
            top_k=top_k,
            min_score=min_score,
            query_analysis=analysis,
        )

        return {
            "status": "success" if results else "not_found",
            "scope_message": None,
            "query_analysis": analysis,
            "sections": results,
        }

    def search(
        self,
        query: str,
        top_k: int = 3,
        min_score: Optional[float] = None,
        query_analysis: Optional[QueryAnalysis] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search the BNS corpus using hybrid retrieval and legal reranking.

        Ranking Priority:
        1. Exact section match
        2. Same offence category match
        3. Keyword relevance (BM25)
        4. Semantic similarity (Dense vector cosine)

        Args:
            query: The user search query or legal question.
            top_k: Number of final sections to return (default 3, up to 5).
            min_score: Minimum similarity threshold.
            query_analysis: Optional precomputed QueryAnalysis.

        Returns:
            List of section dictionaries ordered in descending relevance.
        """
        # Input validation
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query must be a non-empty string.")

        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError(f"top_k must be an integer greater than 0, got {top_k}")

        analysis = query_analysis or QueryUnderstanding.analyze(query)

        # 1. Metadata Filtering: If an unsupported statute is queried (e.g. IPC, CrPC),
        # return empty immediately rather than retrieving unrelated BNS sections.
        if not analysis.is_supported_statute:
            return []

        # 2. Exact Section Routing (Priority 1)
        if analysis.exact_section:
            sec_target = str(analysis.exact_section).strip()
            exact_sec = self.sections_by_number.get(sec_target)
            if exact_sec:
                result_item = {
                    "section": str(exact_sec.get("section") or exact_sec.get("section_number", "")),
                    "section_number": str(exact_sec.get("section_number") or exact_sec.get("section", "")),
                    "statute": exact_sec.get("statute", "BNS"),
                    "chapter": exact_sec.get("chapter", ""),
                    "chapter_title": exact_sec.get("chapter_title", ""),
                    "offence_category": exact_sec.get("offence_category", exact_sec.get("chapter_title", "")),
                    "title": exact_sec.get("title", None),
                    "keywords": exact_sec.get("keywords", []),
                    "content": exact_sec.get("content", ""),
                    "score": 1.0,
                    "rerank_score": 10.0,
                }
                # For exact section queries, return ONLY the exact section
                return [result_item]

        # 3. Dense Semantic Similarity Search
        query_text = f"query: {analysis.cleaned_query}"
        query_embedding = self.model.encode(
            [query_text],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        query_vec = np.array(query_embedding[0], dtype=np.float32)
        dense_scores = np.dot(self.embeddings, query_vec)

        # 4. Lexical BM25 Matching
        bm25_scores = self.bm25_index.get_normalized_scores(analysis.cleaned_query)

        # 5. Candidate Generation (Retrieve top 15 initial candidates)
        candidate_pool: List[Dict[str, Any]] = []
        for idx in range(len(self.metadata)):
            d_score = float(dense_scores[idx])
            b_score = float(bm25_scores[idx]) if idx < len(bm25_scores) else 0.0

            # Initial hybrid blend
            initial_score = 0.55 * d_score + 0.45 * b_score

            meta_item = self.metadata[idx]
            sec_num = str(meta_item.get("section") or meta_item.get("section_number", ""))
            sec_data = self.sections_by_number.get(sec_num, meta_item)

            candidate_pool.append({
                "section": sec_num,
                "section_number": sec_num,
                "statute": meta_item.get("statute", "BNS"),
                "chapter": meta_item.get("chapter", ""),
                "chapter_title": meta_item.get("chapter_title", ""),
                "offence_category": meta_item.get("offence_category", meta_item.get("chapter_title", "")),
                "title": meta_item.get("title") or sec_data.get("title"),
                "keywords": meta_item.get("keywords") or sec_data.get("keywords", []),
                "content": sec_data.get("content") or meta_item.get("content", ""),
                "dense_score": d_score,
                "bm25_score": b_score,
                "score": initial_score,
            })

        # Sort candidate pool and select top 15 candidates
        candidate_pool.sort(key=lambda x: x["score"], reverse=True)
        top15_candidates = candidate_pool[:15]

        # 6. Apply Legal Reranker Layer
        reranked = LegalReranker.rerank(
            candidates=top15_candidates,
            query=analysis.cleaned_query,
            query_analysis=analysis,
            top_k=top_k,
        )

        # Apply min_score threshold if specified
        if min_score is not None:
            reranked = [r for r in reranked if r.get("score", 0.0) >= min_score]

        return reranked
