"""
Semantic retrieval module for the BNS legal corpus.

Provides vector similarity search using multilingual-e5-base embeddings.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import json
import numpy as np
from sentence_transformers import SentenceTransformer

# Resolve project root (3 levels up: ai/rag/retriever.py -> ai/rag -> ai -> LawLense)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class SemanticRetriever:
    """
    Semantic search retriever for the Bharatiya Nyaya Sanhita (BNS) corpus.

    Embeds queries using the multilingual-e5-base model and performs cosine
    similarity matching against precomputed normalized section embeddings.
    """

    def __init__(
        self,
        embeddings_path: Optional[Union[Path, str]] = None,
        metadata_path: Optional[Union[Path, str]] = None,
        sections_path: Optional[Union[Path, str]] = None,
        model_name: str = "intfloat/multilingual-e5-base",
    ):
        """
        Initialize the semantic retriever and load corpus embeddings/metadata.

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

        # 1. Load embeddings (.npz)
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
            self.metadata = json.load(f)

        # 3. Load sections (.json)
        with open(self.sections_path, "r", encoding="utf-8") as f:
            self.sections = json.load(f)

        # Build lookup table by section number for consistent content retrieval
        self.sections_by_number: Dict[str, Dict[str, Any]] = {
            str(s.get("section", "")).strip(): s for s in self.sections
        }

        # 4. Load embedding model once
        self.model = SentenceTransformer(self.model_name)

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search the BNS corpus for sections semantically relevant to the query.

        Args:
            query: The user search query or question.
            top_k: Maximum number of top-scoring sections to return.
            min_score: Minimum cosine similarity threshold (range [-1, 1]).

        Returns:
            List of dictionaries containing section metadata, content, and scores,
            ordered in descending similarity score.
        """
        # Input validation
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query must be a non-empty string.")

        if not isinstance(top_k, int) or top_k <= 0:
            raise ValueError(f"top_k must be an integer greater than 0, got {top_k}")

        if min_score is not None:
            if not isinstance(min_score, (int, float)) or isinstance(min_score, bool):
                raise ValueError(
                    f"min_score must be a numeric value, got {type(min_score).__name__}"
                )
            if not -1.0 <= min_score <= 1.0:
                raise ValueError(
                    f"min_score must be within the cosine similarity range [-1, 1], got {min_score}"
                )

        # Generate query embedding using E5 query prefix
        query_text = f"query: {query.strip()}"
        query_embedding = self.model.encode(
            [query_text],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        query_vec = np.array(query_embedding[0], dtype=np.float32)

        # Calculate cosine similarity (dot product of unit normalized vectors)
        scores = np.dot(self.embeddings, query_vec)

        # Rank in descending order
        ranked_indices = np.argsort(scores)[::-1]

        results: List[Dict[str, Any]] = []
        for idx in ranked_indices:
            score = float(scores[idx])

            # Apply min_score threshold if supplied
            if min_score is not None and score < min_score:
                break

            # Retrieve section data using index mapping or section lookup
            sec_data: Optional[Dict[str, Any]] = None
            if idx < len(self.metadata):
                sec_num = str(self.metadata[idx].get("section", "")).strip()
                sec_data = self.sections_by_number.get(sec_num)

            if sec_data is None and idx < len(self.sections):
                sec_data = self.sections[idx]

            if sec_data is None:
                continue

            result_item: Dict[str, Any] = {
                "section": str(sec_data.get("section", "")),
                "chapter": sec_data.get("chapter", ""),
                "chapter_title": sec_data.get("chapter_title", ""),
                "title": sec_data.get("title", None),
                "content": sec_data.get("content", ""),
                "score": score,
            }
            results.append(result_item)

            if len(results) >= top_k:
                break

        return results
