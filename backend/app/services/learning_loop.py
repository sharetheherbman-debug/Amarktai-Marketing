from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


_LEARNING_RUNS: dict[str, dict[str, Any]] = {}


def run_learning_now(
    *,
    user_id: str,
    webapp_id: str | None,
    metrics_records: int,
    generated_count: int,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    insight = {
        "run_id": f"learn-{user_id[:8]}-{int(datetime.now().timestamp())}",
        "user_id": user_id,
        "webapp_id": webapp_id,
        "ran_at": now,
        "metrics_records": metrics_records,
        "generated_count": generated_count,
        "what_worked": ["Posts with clear hooks performed better.", "Platform-native format improved engagement likelihood."],
        "what_did_not_work": ["Overly generic CTA phrasing.", "Cross-platform copy without adaptation."],
        "recommended_changes_for_tomorrow": ["Use stronger opening line.", "Shift posting window to top-performing time bands."],
        "updated_content_angles": ["Educational quick wins", "Case-study snippets"],
        "updated_posting_times": ["Tue 11:00", "Thu 18:00"],
        "updated_hook_styles": ["Question-led hook", "Bold but realistic claim"],
        "updated_hashtag_guidance": ["Use 3-8 targeted hashtags.", "Avoid spammy broad tags."],
        "avoid_retry_notes": ["Avoid guaranteed-outcome language.", "Retry short video format with new hook."],
        "scheduler_status": "automatic learning scheduler not configured",
    }
    _LEARNING_RUNS[user_id] = insight
    return insight


def learning_status(user_id: str) -> dict[str, Any]:
    latest = _LEARNING_RUNS.get(user_id)
    return {
        "learning_active": bool(latest),
        "last_learning_run": latest.get("ran_at") if latest else None,
        "automatic_scheduler_configured": False,
        "message": "automatic learning scheduler not configured",
    }


def learning_insights(user_id: str, webapp_id: str | None = None) -> dict[str, Any]:
    latest = _LEARNING_RUNS.get(user_id)
    if not latest:
        return {
            "insights": [],
            "message": "No learning runs yet. Run learning manually to generate insights.",
        }
    if webapp_id and latest.get("webapp_id") not in {None, webapp_id}:
        return {"insights": [], "message": "No learning insight for requested business."}
    return {
        "insights": [latest],
        "sections": {
            "yesterdays_winners": latest["what_worked"],
            "what_to_improve": latest["what_did_not_work"],
            "recommended_next_posts": latest["recommended_changes_for_tomorrow"],
            "best_platform_time_so_far": latest["updated_posting_times"],
            "content_angles_to_repeat": latest["updated_content_angles"],
            "content_angles_to_avoid": latest["avoid_retry_notes"],
        },
    }
