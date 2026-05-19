from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from app.services.scraper import scrape_page

_STOPWORDS = {
    "about", "after", "again", "business", "could", "first", "from", "have",
    "into", "more", "their", "there", "these", "this", "that", "with", "your",
    "they", "them", "what", "when", "where", "while", "would", "will", "been",
    "also", "only", "over", "than", "then", "most", "such", "very",
}


def normalize_url(url: str | None) -> str | None:
    raw = (url or "").strip()
    if not raw:
        return None
    if "://" not in raw:
        raw = f"https://{raw}"
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        return None
    return parsed.geturl()


def _keywords(text: str, limit: int = 20) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", text.lower())
    ranked: list[str] = []
    seen: set[str] = set()
    for word in words:
        if word in _STOPWORDS or word in seen:
            continue
        seen.add(word)
        ranked.append(word)
        if len(ranked) >= limit:
            break
    return ranked


def _guess_ctas(text: str) -> list[str]:
    candidates = []
    lowered = text.lower()
    for cta in ("contact us", "book now", "get started", "learn more", "try free", "request demo", "shop now", "subscribe"):
        if cta in lowered:
            candidates.append(cta.title())
    return candidates or ["Learn more", "Get started"]


def _guess_target_audience(text: str) -> str:
    match = re.search(r"\bfor\s+([A-Za-z0-9 ,&\-]{6,80})", text, re.IGNORECASE)
    if match:
        return match.group(1).strip(" .,:;")
    return "General audience"


def _guess_voice(text: str) -> str:
    lowered = text.lower()
    if any(w in lowered for w in ("enterprise", "compliance", "professional")):
        return "Professional"
    if any(w in lowered for w in ("friendly", "community", "welcome")):
        return "Friendly"
    if any(w in lowered for w in ("innovative", "future", "ai", "modern")):
        return "Modern"
    return "Clear and informative"


def _derive_name(site_title: str, supplied_name: str | None, url: str | None) -> str:
    if supplied_name and supplied_name.strip():
        return supplied_name.strip()
    if site_title:
        return site_title.split("|")[0].split("-")[0].strip() or site_title.strip()
    if url:
        host = urlparse(url).netloc.lower().replace("www.", "")
        return host.split(".")[0].replace("-", " ").title() or "Business"
    return "Business"


async def analyze_business(
    *,
    url: str | None,
    name: str | None = None,
    description: str | None = None,
    firecrawl_api_key: str | None = None,
    timeout: int = 25,
) -> dict[str, Any]:
    normalized_url = normalize_url(url)
    warnings: list[str] = []

    if not normalized_url:
        return {
            "business_name": _derive_name("", name, None),
            "site_title": "",
            "meta_description": description or "",
            "page_summary": description or "",
            "products_services": [],
            "target_audience_guess": _guess_target_audience(description or ""),
            "value_props": [],
            "brand_voice": _guess_voice(description or ""),
            "ctas": _guess_ctas(description or ""),
            "keywords": _keywords(description or ""),
            "social_links": [],
            "source_provider": "manual",
            "scrape_status": "failed",
            "warnings": ["No valid URL supplied; using manual data only."],
            "normalized_url": None,
        }

    scraped = await scrape_page(
        normalized_url,
        timeout=max(10, timeout),
        firecrawl_api_key=firecrawl_api_key,
    )

    site_title = (scraped.title or "").strip()
    meta_description = (scraped.meta_description or "").strip()
    full_text = (scraped.full_text or "").strip()
    combined = " ".join(
        part for part in [site_title, meta_description, description or "", full_text] if part
    ).strip()

    if scraped.error:
        warnings.append(f"Scrape warning: {scraped.error}")

    headings = [h.strip() for h in (scraped.headings or []) if h.strip()]
    products_services = headings[:6]
    if not products_services and meta_description:
        products_services = [meta_description[:140]]

    value_props: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", combined):
        s = sentence.strip()
        if len(s) < 30:
            continue
        if any(k in s.lower() for k in ("help", "improve", "save", "faster", "trusted", "quality", "benefit")):
            value_props.append(s[:180])
        if len(value_props) >= 5:
            break

    scrape_status = "success"
    if scraped.error and combined:
        scrape_status = "partial"
    elif scraped.error and not combined:
        scrape_status = "failed"

    return {
        "business_name": _derive_name(site_title, name, normalized_url),
        "site_title": site_title,
        "meta_description": meta_description,
        "page_summary": (meta_description or full_text or description or "")[:600],
        "products_services": products_services,
        "target_audience_guess": _guess_target_audience(combined),
        "value_props": value_props,
        "brand_voice": _guess_voice(combined),
        "ctas": _guess_ctas(combined),
        "keywords": _keywords(combined),
        "social_links": list(dict.fromkeys(scraped.social_links or []))[:20],
        "source_provider": scraped.provider or "beautifulsoup",
        "scrape_status": scrape_status,
        "warnings": warnings,
        "normalized_url": normalized_url,
    }
