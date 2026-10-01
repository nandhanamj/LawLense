"""
Groq LLM client for LawLense.

The LLM is responsible only for turning verified BNS evidence
into a natural-language explanation. Legal facts and citations
must come strictly from the retrieval/database tools.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from groq import Groq

from ai.llm.pricing import calculate_cost

load_dotenv()

logger = logging.getLogger("ai.llm.groq_client")


class GroqLegalClient:
    """
    Thin, bounded wrapper around the Groq chat-completions API.
    Handles token tracking, cost calculation, and structured logging.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "openai/gpt-oss-20b",
        max_completion_tokens: int = 500,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.max_completion_tokens = int(
            os.getenv("GROQ_MAX_TOKENS", str(max_completion_tokens))
        )
        self.timeout = timeout
        self._client: Optional[Groq] = None

    @property
    def client(self) -> Groq:
        """Lazy initialization of Groq SDK client."""
        if self._client is None:
            if not self.api_key:
                raise RuntimeError("GROQ_API_KEY is not configured.")
            self._client = Groq(api_key=self.api_key, timeout=self.timeout)
        return self._client

    def generate(
        self,
        query: str,
        evidence: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generate a grounded answer using only supplied verified legal evidence.

        Args:
            query: The user's input legal question.
            evidence: List of verified section dictionaries from MySQL.

        Returns:
            Dict containing:
                - answer (str)
                - usage (dict: prompt_tokens, completion_tokens, total_tokens)
                - cost (dict: total_cost_usd, pricing_configured, etc.)
                - model (str)
                - latency_seconds (float)
                - success (bool)
                - error (Optional[str])
        """
        start_time = time.time()

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

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_completion_tokens=self.max_completion_tokens,
                temperature=0,
            )

            latency = round(time.time() - start_time, 3)
            usage = response.usage

            prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
            completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
            total_tokens = int(getattr(usage, "total_tokens", 0) or (prompt_tokens + completion_tokens))

            cost = calculate_cost(self.model, prompt_tokens, completion_tokens)
            raw_answer = response.choices[0].message.content or ""
            # Normalize narrow non-breaking and non-breaking spaces to standard spaces
            answer_text = raw_answer.replace("\u202f", " ").replace("\u00a0", " ")

            # Structured logging (NO API KEYS OR CREDENTIALS)
            logger.info(
                "[Groq LLM Success] model=%s prompt_tokens=%d completion_tokens=%d total_tokens=%d latency=%.3fs cost_usd=%s",
                self.model,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                latency,
                cost.get("total_cost_usd"),
            )

            return {
                "answer": answer_text,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                },
                "cost": cost,
                "model": self.model,
                "latency_seconds": latency,
                "success": True,
                "error": None,
            }

        except Exception as err:
            latency = round(time.time() - start_time, 3)
            logger.error(
                "[Groq LLM Error] model=%s latency=%.3fs error=%s",
                self.model,
                latency,
                err,
            )

            return {
                "answer": "",
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
                "cost": calculate_cost(self.model, 0, 0),
                "model": self.model,
                "latency_seconds": latency,
                "success": False,
                "error": str(err),
            }