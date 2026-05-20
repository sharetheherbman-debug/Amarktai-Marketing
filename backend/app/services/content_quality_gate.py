from __future__ import annotations

from typing import Any


def evaluate_quality_gate(
    *,
    business_grounding_score: int,
    hashtag_relevance_score: int,
    creative_relevance_score: int | None = None,
) -> dict[str, Any]:
    issues: list[str] = []
    if business_grounding_score < 70:
        issues.append("Business grounding below threshold.")
    if hashtag_relevance_score < 70:
        issues.append("Hashtag relevance below threshold.")
    if creative_relevance_score is not None and creative_relevance_score < 70:
        issues.append("Creative relevance below threshold.")
    return {
        "ready": not issues,
        "needs_review": bool(issues),
        "issues": issues,
        "status": "ready" if not issues else "needs_review",
    }
