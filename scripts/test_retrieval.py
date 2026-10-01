"""
Retrieval Evaluation Script for LawLens.

Tests and validates the production hybrid retrieval pipeline against the
specified benchmark legal queries:
1. "Punishment for murder"        -> Expected: Section 103
2. "What is theft punishment?"    -> Expected: Section 303/305 related sections
3. "IPC Section 302"              -> Expected: Out of scope response
4. "Punishment for cheating"      -> Expected: Section 318
5. "What is snatching?"           -> Expected: Section 304
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai.rag.retriever import SemanticRetriever


TEST_SUITE: List[Dict[str, Any]] = [
    {
        "id": "RAG-TEST-01",
        "query": "Punishment for murder",
        "expected_type": "sections",
        "expected_sections": ["103"],
        "description": "General offence punishment query; expects primary murder section 103.",
    },
    {
        "id": "RAG-TEST-02",
        "query": "What is theft punishment?",
        "expected_type": "sections",
        "expected_sections": ["303", "305"],
        "description": "Theft penalty query; expects primary theft sections 303 / 305.",
    },
    {
        "id": "RAG-TEST-03",
        "query": "IPC Section 302",
        "expected_type": "out_of_scope",
        "expected_sections": [],
        "description": "Unsupported statute (IPC); expects out of scope refusal without BNS noise.",
    },
    {
        "id": "RAG-TEST-04",
        "query": "Punishment for cheating",
        "expected_type": "sections",
        "expected_sections": ["318"],
        "description": "Cheating penalty query; expects primary cheating section 318.",
    },
    {
        "id": "RAG-TEST-05",
        "query": "What is snatching?",
        "expected_type": "sections",
        "expected_sections": ["304"],
        "description": "Snatching definition query; expects snatching section 304.",
    },
]


def run_retrieval_tests() -> int:
    """Run retrieval evaluation suite and print detailed test results."""
    print("=" * 70)
    print("LawLens RAG Hybrid Retrieval Evaluation Suite")
    print("=" * 70)
    print(f"Total Test Cases : {len(TEST_SUITE)}")
    print("Ranking Priority : 1. Exact Section | 2. Category Match | 3. BM25 | 4. Dense Cosine\n")

    retriever = SemanticRetriever()

    passed_count = 0

    for idx, test in enumerate(TEST_SUITE, 1):
        q_id = test["id"]
        query = test["query"]
        expected_type = test["expected_type"]
        expected_secs = test["expected_sections"]

        print(f"[{idx}/{len(TEST_SUITE)}] Test Case {q_id}")
        print(f"Query: {query}")

        retrieval_result = retriever.retrieve(query, top_k=3)
        status = retrieval_result.get("status")
        scope_msg = retrieval_result.get("scope_message")
        sections = retrieval_result.get("sections", [])

        retrieved_sec_numbers = [str(s.get("section", "")).strip() for s in sections]
        scores = [round(float(s.get("score", 0.0)), 4) for s in sections]

        is_correct = False
        reason = ""

        if expected_type == "out_of_scope":
            if status == "out_of_scope" and len(sections) == 0:
                is_correct = True
                reason = f"Out of scope correctly flagged: '{scope_msg}'"
            else:
                reason = f"Expected out_of_scope status with 0 sections, got status='{status}', sections={retrieved_sec_numbers}"
            print(f"Retrieved sections: {retrieved_sec_numbers if retrieved_sec_numbers else 'None (Scope Refusal)'}")
            print(f"Similarity scores: {scores if scores else 'N/A'}")

        else:  # expected_type == "sections"
            print(f"Retrieved sections: {retrieved_sec_numbers}")
            print(f"Similarity scores: {scores}")

            # Verify presence of expected sections
            if not retrieved_sec_numbers:
                reason = f"No sections retrieved, expected {expected_secs}"
            elif any(exp in retrieved_sec_numbers for exp in expected_secs):
                # Verify primary section is top rank if single expected section
                if len(expected_secs) == 1 and retrieved_sec_numbers[0] == expected_secs[0]:
                    is_correct = True
                    reason = f"Expected Section {expected_secs[0]} retrieved at rank 1"
                elif any(exp in retrieved_sec_numbers[:2] for exp in expected_secs):
                    is_correct = True
                    reason = f"Expected related section(s) {expected_secs} retrieved in top candidates"
                else:
                    reason = f"Expected sections {expected_secs} found but ranked too low: {retrieved_sec_numbers}"
            else:
                reason = f"Retrieved sections {retrieved_sec_numbers} do not contain expected {expected_secs}"

        if is_correct:
            passed_count += 1
            print(f"Correct/Incorrect: CORRECT ({reason})")
        else:
            print(f"Correct/Incorrect: INCORRECT ({reason})")

        print("-" * 70)

    print("\n" + "=" * 70)
    pass_rate = (passed_count / len(TEST_SUITE)) * 100.0
    print(f"Retrieval Evaluation Summary: {passed_count}/{len(TEST_SUITE)} Passed ({pass_rate:.1f}%)")
    print("=" * 70 + "\n")

    return 0 if passed_count == len(TEST_SUITE) else 1


if __name__ == "__main__":
    sys.exit(run_retrieval_tests())
