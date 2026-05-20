from __future__ import annotations

from typing import Any


def build_business_grounding_context(business: dict[str, Any]) -> dict[str, Any]:
    keywords = [str(value).strip() for value in (business.get("keywords") or []) if str(value).strip()]
    products = [str(value).strip() for value in (business.get("products_services") or business.get("key_features") or []) if str(value).strip()]
    ctas = [str(value).strip() for value in (business.get("ctas") or []) if str(value).strip()]
    context = {
        "business_name": business.get("name") or "",
        "url": business.get("url") or "",
        "scraped_summary": business.get("summary") or business.get("page_summary") or business.get("description") or "",
        "industry": business.get("category") or "",
        "product_service": ", ".join(products[:5]),
        "audience": business.get("target_audience") or "",
        "location": business.get("market_location") or "",
        "brand_voice": business.get("brand_voice") or "",
        "ctas": ctas[:5],
        "keywords": keywords[:12],
        "competitor_notes": business.get("competitor_notes") or [],
        "positioning_notes": business.get("positioning_notes") or [],
    }
    base_text = (
        f"Business name: {context['business_name']}. "
        f"URL: {context['url']}. "
        f"Website summary: {context['scraped_summary']}. "
        f"Industry/category: {context['industry']}. "
        f"Product/service: {context['product_service']}. "
        f"Audience: {context['audience']}. "
        f"Location: {context['location']}. "
        f"Brand voice: {context['brand_voice']}. "
        f"CTAs: {', '.join(context['ctas']) or 'none provided'}. "
        f"Keywords: {', '.join(context['keywords']) or 'none provided'}. "
        "Market this business, not Amarktai. Do not use #Amarktai unless this business is Amarktai."
    )
    context["prompt_prefix"] = base_text
    return context


def score_business_grounding(text: str, business: dict[str, Any]) -> dict[str, Any]:
    lower = (text or "").lower()
    score = 45
    issues: list[str] = []
    for field_name in ("name", "category", "target_audience", "market_location"):
        value = str(business.get(field_name) or "").strip().lower()
        if value and any(token in lower for token in value.split() if len(token) > 3):
            score += 10
        elif value:
            issues.append(f"{field_name} missing from generated content")
    products = [str(value).lower() for value in (business.get("products_services") or business.get("key_features") or []) if str(value).strip()]
    if any(product in lower for product in products if len(product) > 3):
        score += 15
    elif products:
        issues.append("products/services missing from generated content")
    if "#amarktai" in lower and "amarktai" not in str(business.get("name") or "").lower():
        score -= 25
        issues.append("banned Amarktai hashtag found for non-Amarktai business")
    return {
        "business_grounding_score": max(0, min(100, score)),
        "needs_review": score < 70,
        "issues": issues,
    }
