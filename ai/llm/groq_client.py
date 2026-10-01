"""
Groq LLM client for LawLense.

The LLM is responsible only for turning verified BNS evidence
into a natural-language explanation. Legal facts and citations
must come from the retrieval/database tools.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from groq import Groq

load_dotenv()


class GroqLegalClient:
    """Thin wrapper around the Groq chat-completions API."""

    def __init__(
        self,
        model: str = "openai/gpt-oss-20b",
        max_completion_tokens: int = 300,
    ) -> None:
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not configured.")

        self.client = Groq(api_key=api_key)
        self.model = model
        self.max_completion_tokens = max_completion_tokens

    def generate(
        self,
        query: str,
        evidence: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate a grounded answer using only supplied legal evidence."""

        evidence_text = "\n\n".join(
            (
                f"Section {item.get('section')}"
                f" ({item.get('title') or 'Untitled'}):\n"
                f"{item.get('content') or item.get('text') or ''}"
            )
            for item in evidence
        )

        system_prompt = """You are the language-generation component of LawLense.

Your job is to explain Indian legal information using ONLY the verified
Bharatiya Nyaya Sanhita (BNS) evidence supplied by the application.

Rules:
- Do not invent legal provisions, sections, penalties, exceptions, or facts.
- Do not cite sections that are not present in the supplied evidence.
- Do not provide personalized legal advice or tell the user what they should do.
- If the supplied evidence does not answer the question, clearly say that
  the available BNS evidence is insufficient.
- Give an objective explanation in plain language.
"""

        user_prompt = f"""User question:
{query}

Verified BNS evidence:
{evidence_text}

Write a concise, objective explanation based only on the evidence above.
"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_completion_tokens=self.max_completion_tokens,
            temperature=0,
        )

        usage = response.usage

        return {
            "answer": response.choices[0].message.content or "",
            "usage": {
                "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                "completion_tokens": getattr(usage, "completion_tokens", 0),
                "total_tokens": getattr(usage, "total_tokens", 0),
            },
            "model": self.model,
        }