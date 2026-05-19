"""
Web scraper — Firecrawl primary, BeautifulSoup fallback.

Priority:
  1. Firecrawl API (when FIRECRAWL_API_KEY is set) — richer, JS-rendered
  2. httpx + BeautifulSoup — always-available, no API key required

Runs over httpx so it is compatible with async FastAPI handlers.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v2/scrape"

_SOCIAL_DOMAINS = {"twitter.com", "x.com", "instagram.com", "facebook.com",
                   "linkedin.com", "tiktok.com", "youtube.com", "pinterest.com"}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AmarktAIBot/1.0; "
        "+https://amarktai.com/bot)"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


@dataclass
class ScrapedPage:
    url: str
    title: str = ""
    meta_description: str = ""
    headings: list[str] = field(default_factory=list)
    paragraphs: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    social_links: list[str] = field(default_factory=list)
    full_text: str = ""
    error: str | None = None
    provider: str = "beautifulsoup"


# ---------------------------------------------------------------------------
# Firecrawl primary path
# ---------------------------------------------------------------------------

async def _scrape_via_firecrawl(url: str, api_key: str, timeout: int = 30) -> ScrapedPage | None:
    """
    Attempt to scrape a URL through the Firecrawl API.
    Returns None if the call fails so the caller can fall back to BeautifulSoup.
    """
    result = ScrapedPage(url=url, provider="firecrawl")
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                _FIRECRAWL_SCRAPE_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "url": url,
                    "formats": ["markdown", "extract"],
                    "extract": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "headings": {"type": "array", "items": {"type": "string"}},
                                "services": {"type": "array", "items": {"type": "string"}},
                                "brand_voice": {"type": "string"},
                                "target_audience": {"type": "string"},
                            },
                        }
                    },
                },
            )
            if resp.status_code != 200:
                logger.warning("Firecrawl returned %s for %s", resp.status_code, url)
                return None
            data = resp.json()
    except Exception as exc:
        logger.warning("Firecrawl request failed for %s: %s", url, exc)
        return None

    # Parse Firecrawl response
    if not data.get("success"):
        return None

    page_data = data.get("data", {})
    metadata = page_data.get("metadata", {})
    extract = page_data.get("extract", {})
    markdown = page_data.get("markdown", "") or ""

    result.title = (
        extract.get("title")
        or metadata.get("title")
        or metadata.get("ogTitle")
        or ""
    )
    result.meta_description = (
        extract.get("description")
        or metadata.get("description")
        or metadata.get("ogDescription")
        or ""
    )

    # Headings from extract or parse markdown
    if extract.get("headings"):
        result.headings = [h for h in extract["headings"] if isinstance(h, str)][:20]
    else:
        for line in markdown.splitlines():
            stripped = line.lstrip("#").strip()
            if line.startswith("#") and stripped:
                result.headings.append(stripped)
            if len(result.headings) >= 20:
                break

    # Paragraphs from markdown
    for line in markdown.splitlines():
        line = line.strip()
        if len(line) > 40 and not line.startswith("#") and not line.startswith("|"):
            result.paragraphs.append(line)
        if len(result.paragraphs) >= 10:
            break

    # Social links from metadata
    for key in ("ogUrl", "twitter:site", "og:url"):
        val = metadata.get(key, "")
        if val and val.startswith("http"):
            parts = val.split("/")
            if len(parts) > 2:
                domain = parts[2].lower().lstrip("www.")
                if any(s in domain for s in _SOCIAL_DOMAINS):
                    result.social_links.append(val)

    # Full text
    texts = [result.title, result.meta_description] + result.headings + result.paragraphs
    extra_context = []
    if extract.get("brand_voice"):
        extra_context.append(f"Brand voice: {extract['brand_voice']}")
    if extract.get("target_audience"):
        extra_context.append(f"Target audience: {extract['target_audience']}")
    if extract.get("services"):
        extra_context.append("Services: " + ", ".join(extract["services"][:10]))
    full = " ".join(texts + extra_context)
    result.full_text = full[:5000]

    return result


# ---------------------------------------------------------------------------
# BeautifulSoup fallback
# ---------------------------------------------------------------------------

def _parse_html(url: str, html: str) -> ScrapedPage:
    result = ScrapedPage(url=url, provider="beautifulsoup")
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "noscript", "aside", "form"]):
        tag.decompose()

    title_tag = soup.find("title")
    result.title = title_tag.get_text(strip=True) if title_tag else ""

    meta = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    if meta and meta.get("content"):  # type: ignore[union-attr]
        result.meta_description = meta["content"]  # type: ignore[index]

    for h in soup.find_all(["h1", "h2", "h3"]):
        text = h.get_text(strip=True)
        if text and len(text) > 3:
            result.headings.append(text)

    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if len(text) > 40:
            result.paragraphs.append(text)

    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        if href.startswith("http"):
            domain = href.split("/")[2].lower().lstrip("www.")
            if any(s in domain for s in _SOCIAL_DOMAINS):
                result.social_links.append(href)
            else:
                result.links.append(href)

    texts = [result.title, result.meta_description] + result.headings + result.paragraphs
    result.full_text = " ".join(texts)[:4000]
    return result


async def _scrape_via_beautifulsoup(url: str, timeout: int = 20) -> ScrapedPage:
    result = ScrapedPage(url=url, provider="beautifulsoup")
    try:
        async with httpx.AsyncClient(
            headers=_HEADERS,
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
    except Exception as exc:
        result.error = str(exc)
        return result
    return _parse_html(url, html)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def scrape_page(
    url: str,
    timeout: int = 20,
    firecrawl_api_key: str | None = None,
) -> ScrapedPage:
    """
    Scrape a public web page.

    Uses Firecrawl as the primary provider when ``firecrawl_api_key`` is
    supplied (or when FIRECRAWL_API_KEY is set in settings).  Falls back to
    httpx + BeautifulSoup automatically.
    """
    # Resolve API key from settings if not passed explicitly
    if not firecrawl_api_key:
        try:
            from app.core.config import settings
            firecrawl_api_key = settings.FIRECRAWL_API_KEY or None
        except (ImportError, AttributeError) as exc:
            logger.debug("Could not load FIRECRAWL_API_KEY from settings: %s", exc)
            firecrawl_api_key = None

    if firecrawl_api_key:
        fc_result = await _scrape_via_firecrawl(url, firecrawl_api_key, timeout=max(timeout, 30))
        if fc_result is not None:
            logger.info("Firecrawl scrape succeeded for %s", url)
            return fc_result
        logger.info("Firecrawl scrape failed for %s — falling back to BeautifulSoup", url)

    return await _scrape_via_beautifulsoup(url, timeout=timeout)


async def scrape_multiple(urls: list[str], firecrawl_api_key: str | None = None) -> list[ScrapedPage]:
    """Scrape multiple pages concurrently, returning results in order."""
    import asyncio

    tasks = [scrape_page(url, firecrawl_api_key=firecrawl_api_key) for url in urls]
    return await asyncio.gather(*tasks)


async def test_firecrawl_key(api_key: str, *, url: str = "https://example.com") -> dict[str, str | bool]:
    result = await _scrape_via_firecrawl(url, api_key, timeout=30)
    if result is None:
        return {"ok": False, "error": "Firecrawl test scrape failed."}
    if result.error:
        return {"ok": False, "error": result.error}
    return {"ok": True, "error": ""}
