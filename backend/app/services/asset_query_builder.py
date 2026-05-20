from __future__ import annotations

from typing import Any


def build_asset_query(
    *,
    business_name: str = "",
    category: str = "",
    products_services: list[str] | None = None,
    audience: str = "",
    platform: str = "",
    offer: str = "",
    objective: str = "",
) -> str:
    category_lower = (category or "").lower()
    if "equine" in category_lower or "horse" in category_lower:
        return "horse riding stable equine care horse stable horse rider arena equestrian tack"
    if "cyber" in category_lower or "security" in category_lower:
        return "cyber security data protection business secure network dashboard digital lock data cyber threat detection"

    terms: list[str] = []
    for value in [business_name, category, audience, platform, offer, objective]:
        text = (value or "").strip()
        if text:
            terms.append(text)
    for item in (products_services or [])[:4]:
        text = (item or "").strip()
        if text:
            terms.append(text)
    return " ".join(terms)[:280] or "business marketing"
