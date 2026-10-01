"""
Pricing configuration and cost calculation for LawLense LLM usage.

Pricing is defined per 1,000,000 tokens (USD).
Rates can be configured statically in MODEL_PRICING or dynamically via environment variables:
  GROQ_PROMPT_COST_PER_MILLION
  GROQ_COMPLETION_COST_PER_MILLION

Note: Exact rates must be populated/verified from the official provider documentation
(e.g., https://groq.com/pricing). If no rate is configured, cost will report as None/N/A
with pricing_configured=False.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

# Default pricing dictionary per 1,000,000 tokens (USD).
# Populate or verify these rates from provider's official pricing documentation.
MODEL_PRICING: Dict[str, Dict[str, Optional[float]]] = {
    # openai/gpt-oss-20b on Groq
    "openai/gpt-oss-20b": {
        "prompt_cost_per_million": 0.075,
        "completion_cost_per_million": 0.30,
    },
    # Reference rates for standard Groq production models (USD per 1M tokens)
    "llama-3.3-70b-versatile": {
        "prompt_cost_per_million": 0.59,
        "completion_cost_per_million": 0.79,
    },
    "llama-3.1-8b-instant": {
        "prompt_cost_per_million": 0.05,
        "completion_cost_per_million": 0.08,
    },
}


def get_model_pricing(model: str) -> Dict[str, Optional[float]]:
    """
    Retrieve pricing rates for a given model.
    Checks environment variable overrides first:
      GROQ_PROMPT_COST_PER_MILLION
      GROQ_COMPLETION_COST_PER_MILLION
    Falls back to MODEL_PRICING lookup.
    """
    env_prompt = os.getenv("GROQ_PROMPT_COST_PER_MILLION")
    env_completion = os.getenv("GROQ_COMPLETION_COST_PER_MILLION")

    base = MODEL_PRICING.get(model, {})

    prompt_rate: Optional[float] = None
    if env_prompt is not None:
        try:
            prompt_rate = float(env_prompt)
        except ValueError:
            prompt_rate = None
    else:
        prompt_rate = base.get("prompt_cost_per_million")

    completion_rate: Optional[float] = None
    if env_completion is not None:
        try:
            completion_rate = float(env_completion)
        except ValueError:
            completion_rate = None
    else:
        completion_rate = base.get("completion_cost_per_million")

    return {
        "prompt_cost_per_million": prompt_rate,
        "completion_cost_per_million": completion_rate,
    }


def calculate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
) -> Dict[str, Any]:
    """
    Calculate cost in USD based on actual token usage and configured pricing.

    Returns:
        Dict with prompt_cost_usd, completion_cost_usd, total_cost_usd, and pricing_configured.
    """
    pricing = get_model_pricing(model)
    prompt_rate = pricing.get("prompt_cost_per_million")
    completion_rate = pricing.get("completion_cost_per_million")

    if prompt_rate is None or completion_rate is None:
        return {
            "prompt_cost_usd": None,
            "completion_cost_usd": None,
            "total_cost_usd": None,
            "pricing_configured": False,
            "pricing_rate_per_million": pricing,
        }

    prompt_cost = (prompt_tokens / 1_000_000.0) * prompt_rate
    completion_cost = (completion_tokens / 1_000_000.0) * completion_rate
    total_cost = prompt_cost + completion_cost

    return {
        "prompt_cost_usd": round(prompt_cost, 6),
        "completion_cost_usd": round(completion_cost, 6),
        "total_cost_usd": round(total_cost, 6),
        "pricing_configured": True,
        "pricing_rate_per_million": {
            "prompt_cost_per_million": prompt_rate,
            "completion_cost_per_million": completion_rate,
        },
    }
