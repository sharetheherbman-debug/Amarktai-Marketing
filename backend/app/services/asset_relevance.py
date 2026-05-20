from __future__ import annotations

from typing import Any


def score_asset_relevance(
    *,
    query: str,
    title: str,
    tags: list[str] | None,
    platform: str = "",
) -> dict[str, int]:
    query_terms = {term.lower() for term in (query or "").split() if len(term) > 2}
    content_terms = {term.lower() for term in ((title or "") + " " + " ".join(tags or [])).split()}
    overlap = len(query_terms.intersection(content_terms))
    base = min(100, 40 + overlap * 12)
    platform_fit = min(100, base + (10 if platform in {"instagram", "tiktok", "youtube"} else 0))
    grounding = min(100, base + (5 if overlap >= 2 else 0))
    return {
        "relevance_score": base,
        "business_grounding_score": grounding,
        "platform_fit_score": platform_fit,
    }
