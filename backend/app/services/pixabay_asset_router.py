from __future__ import annotations

from typing import Any

from app.services.asset_relevance import score_asset_relevance


def not_supported_payload() -> dict[str, str]:
    return {
        "status": "not_supported_by_api",
        "message": "This Pixabay category is not available through the configured official API endpoint.",
    }


def normalize_pixabay_image(item: dict[str, Any], *, query: str, category: str, platform: str) -> dict[str, Any]:
    title = str(item.get("tags") or "")
    tags = [t.strip() for t in title.split(",") if t.strip()]
    scores = score_asset_relevance(query=query, title=title, tags=tags, platform=platform)
    return {
        "provider": "pixabay",
        "asset_type": "image",
        "pixabay_id": item.get("id"),
        "title": title,
        "tags": tags,
        "preview_url": item.get("previewURL"),
        "media_url": item.get("largeImageURL") or item.get("webformatURL"),
        "thumbnail_url": item.get("previewURL"),
        "webformat_url": item.get("webformatURL"),
        "large_image_url": item.get("largeImageURL"),
        "video_urls": None,
        "source_url": item.get("pageURL"),
        "source_page_url": item.get("pageURL"),
        "author": item.get("user"),
        "author_url": item.get("userImageURL"),
        "license_note": "Pixabay License",
        "attribution": f"Source: Pixabay · {item.get('user') or 'contributor'}",
        "width": item.get("imageWidth"),
        "height": item.get("imageHeight"),
        "duration": None,
        "views": item.get("views"),
        "downloads": item.get("downloads"),
        "likes": item.get("likes"),
        "comments": item.get("comments"),
        "search_query_used": query,
        "category": category,
        "media_type": "photo",
        "source_note": "pixabay official image endpoint",
        "raw_metadata": item,
        **scores,
        "relevance_score": scores["relevance_score"],
        "needs_review": scores["relevance_score"] < 70,
    }


def normalize_pixabay_video(item: dict[str, Any], *, query: str, category: str, platform: str) -> dict[str, Any]:
    title = str(item.get("tags") or "")
    tags = [t.strip() for t in title.split(",") if t.strip()]
    videos = item.get("videos") if isinstance(item.get("videos"), dict) else {}
    scores = score_asset_relevance(query=query, title=title, tags=tags, platform=platform)
    return {
        "provider": "pixabay",
        "asset_type": "video",
        "pixabay_id": item.get("id"),
        "title": title,
        "tags": tags,
        "preview_url": item.get("videos", {}).get("tiny", {}).get("url") if isinstance(videos, dict) else None,
        "media_url": item.get("videos", {}).get("medium", {}).get("url") if isinstance(videos, dict) else None,
        "thumbnail_url": item.get("picture_id"),
        "webformat_url": None,
        "large_image_url": None,
        "video_urls": videos,
        "source_url": item.get("pageURL"),
        "source_page_url": item.get("pageURL"),
        "author": item.get("user"),
        "author_url": item.get("userImageURL"),
        "license_note": "Pixabay License",
        "attribution": f"Source: Pixabay · {item.get('user') or 'contributor'}",
        "width": item.get("videos", {}).get("large", {}).get("width") if isinstance(videos, dict) else None,
        "height": item.get("videos", {}).get("large", {}).get("height") if isinstance(videos, dict) else None,
        "duration": item.get("duration"),
        "views": item.get("views"),
        "downloads": item.get("downloads"),
        "likes": item.get("likes"),
        "comments": item.get("comments"),
        "search_query_used": query,
        "category": category,
        "media_type": "video",
        "source_note": "pixabay official video endpoint",
        "raw_metadata": item,
        **scores,
        "relevance_score": scores["relevance_score"],
        "needs_review": scores["relevance_score"] < 70,
    }
