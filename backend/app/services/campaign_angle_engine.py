"""Campaign angle engine — ensures each generation uses a distinct angle and hook.

Each piece of generated content stores a campaign_angle and hook_style.
On regeneration a different angle/hook is chosen.
On improve, user feedback guides the selection.
Duplicate similarity triggers a needs_review_duplicate flag.
"""
from __future__ import annotations

import random
from typing import Any

# ── Angle catalogue ───────────────────────────────────────────────────────────

CAMPAIGN_ANGLES: list[dict[str, Any]] = [
    {
        "id": "problem_solution",
        "label": "Problem / Solution",
        "description": "Lead with the audience pain point, then reveal the solution.",
        "hook_styles": ["question", "statement", "stat"],
    },
    {
        "id": "social_proof",
        "label": "Social Proof",
        "description": "Use a customer result, testimonial, or number to build trust.",
        "hook_styles": ["quote", "stat", "result"],
    },
    {
        "id": "offer_urgency",
        "label": "Offer / Urgency",
        "description": "Highlight a time-limited deal, discount, or scarcity signal.",
        "hook_styles": ["deadline", "countdown", "exclusive"],
    },
    {
        "id": "educational",
        "label": "Educational",
        "description": "Teach the audience something useful, build authority.",
        "hook_styles": ["how_to", "tip", "myth_bust"],
    },
    {
        "id": "myth_busting",
        "label": "Myth-Busting",
        "description": "Challenge a common misconception in the industry.",
        "hook_styles": ["myth_bust", "controversial", "statement"],
    },
    {
        "id": "behind_the_scenes",
        "label": "Behind the Scenes",
        "description": "Show the human side: process, team, or creation story.",
        "hook_styles": ["story", "reveal", "peek"],
    },
    {
        "id": "comparison",
        "label": "Comparison",
        "description": "Compare before/after, old way vs new way, or product vs alternative.",
        "hook_styles": ["before_after", "vs", "statement"],
    },
    {
        "id": "transformation",
        "label": "Transformation",
        "description": "Show the journey from problem to outcome.",
        "hook_styles": ["before_after", "story", "result"],
    },
    {
        "id": "founder_story",
        "label": "Founder / Story",
        "description": "Personal story from the founder or team that connects emotionally.",
        "hook_styles": ["story", "personal", "reveal"],
    },
    {
        "id": "objection_handling",
        "label": "Objection Handling",
        "description": "Address the top reason people don't buy.",
        "hook_styles": ["question", "statement", "myth_bust"],
    },
    {
        "id": "seasonal_local",
        "label": "Seasonal / Local",
        "description": "Tie the message to a season, event, or local context.",
        "hook_styles": ["timely", "local", "celebration"],
    },
    {
        "id": "product_spotlight",
        "label": "Product Spotlight",
        "description": "Feature a specific product or service with clear benefits.",
        "hook_styles": ["feature", "benefit", "demo"],
    },
]

_ANGLE_BY_ID: dict[str, dict[str, Any]] = {a["id"]: a for a in CAMPAIGN_ANGLES}

# Objectives mapped to preferred angle IDs (first = highest priority)
_OBJECTIVE_ANGLE_MAP: dict[str, list[str]] = {
    "awareness":   ["educational", "behind_the_scenes", "founder_story", "social_proof"],
    "leads":       ["problem_solution", "offer_urgency", "objection_handling", "social_proof"],
    "bookings":    ["offer_urgency", "social_proof", "problem_solution", "transformation"],
    "sales":       ["offer_urgency", "product_spotlight", "social_proof", "comparison"],
    "launch":      ["behind_the_scenes", "founder_story", "product_spotlight", "offer_urgency"],
    "retargeting": ["objection_handling", "social_proof", "offer_urgency", "comparison"],
    "engagement":  ["myth_busting", "behind_the_scenes", "educational", "seasonal_local"],
}


# ── Public API ────────────────────────────────────────────────────────────────

def select_angle(
    *,
    objective: str | None = None,
    exclude_ids: list[str] | None = None,
    feedback: str | None = None,
) -> dict[str, Any]:
    """Choose a campaign angle.

    Args:
        objective: The campaign goal (awareness, leads, sales, etc.)
        exclude_ids: Angle IDs already used — force a different one on regenerate.
        feedback: Free-text user feedback that may hint at a preferred angle.

    Returns:
        Selected angle dict with id, label, description, and chosen hook_style.
    """
    excluded = set(exclude_ids or [])

    # Feedback hint — if the user mentions specific concepts, try to match
    if feedback:
        fb_lower = feedback.lower()
        for angle in CAMPAIGN_ANGLES:
            if angle["id"] in excluded:
                continue
            keywords = angle["label"].lower().split() + [angle["id"].replace("_", " ")]
            if any(kw in fb_lower for kw in keywords):
                return _package_angle(angle)

    # Objective-driven priority list
    if objective:
        priority = _OBJECTIVE_ANGLE_MAP.get(objective.lower(), [])
        for angle_id in priority:
            if angle_id not in excluded:
                angle = _ANGLE_BY_ID.get(angle_id)
                if angle:
                    return _package_angle(angle)

    # Fall back to a random angle not in excluded
    available = [a for a in CAMPAIGN_ANGLES if a["id"] not in excluded]
    if not available:
        # All angles exhausted — reset and pick fresh
        available = CAMPAIGN_ANGLES
    chosen = random.choice(available)
    return _package_angle(chosen)


def _package_angle(angle: dict[str, Any]) -> dict[str, Any]:
    hook_style = random.choice(angle["hook_styles"])
    return {
        "campaign_angle": angle["id"],
        "campaign_angle_label": angle["label"],
        "campaign_angle_description": angle["description"],
        "hook_style": hook_style,
        "why_this_version": (
            f"Using the '{angle['label']}' angle with a '{hook_style.replace('_', ' ')}' hook "
            f"— {angle['description']}"
        ),
    }


def angle_for_regenerate(
    previous_angle: str | None,
    *,
    objective: str | None = None,
    feedback: str | None = None,
) -> dict[str, Any]:
    """Always choose a different angle than the previous generation."""
    exclude = [previous_angle] if previous_angle else []
    return select_angle(objective=objective, exclude_ids=exclude, feedback=feedback)


def detect_duplicate_similarity(
    text_a: str,
    text_b: str,
    threshold: float = 0.85,
) -> dict[str, Any]:
    """Lightweight similarity check using character n-gram overlap.

    Returns dict with: is_duplicate, similarity_score, recommendation.
    """
    if not text_a or not text_b:
        return {"is_duplicate": False, "similarity_score": 0.0, "recommendation": "ok"}

    def ngrams(text: str, n: int = 3) -> set[str]:
        t = text.lower().replace(" ", "")
        return {t[i : i + n] for i in range(len(t) - n + 1)}

    set_a = ngrams(text_a)
    set_b = ngrams(text_b)
    if not set_a or not set_b:
        return {"is_duplicate": False, "similarity_score": 0.0, "recommendation": "ok"}

    overlap = len(set_a & set_b) / max(len(set_a | set_b), 1)
    is_dup = overlap >= threshold
    return {
        "is_duplicate": is_dup,
        "similarity_score": round(overlap, 3),
        "recommendation": "needs_review_duplicate" if is_dup else "ok",
    }


def all_angles() -> list[dict[str, Any]]:
    """Return the full angle catalogue for API exposure."""
    return CAMPAIGN_ANGLES
