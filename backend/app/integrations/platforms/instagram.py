"""
Instagram integration for posting Reels and images via Meta Graph API.

Uses the container-create -> optional poll -> publish flow.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from app.core.config import settings
from app.integrations.platforms.base import BasePlatform, PlatformAnalytics, PostResult

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.facebook.com/v18.0"


class InstagramPlatform(BasePlatform):
    """Instagram integration for posting Reels and images via Meta Graph API."""

    def __init__(self, access_token: str, instagram_account_id: str, refresh_token: str | None = None) -> None:
        super().__init__(access_token, refresh_token)
        self.instagram_account_id = instagram_account_id
        self.base_url = _GRAPH_BASE

    async def post_content(
        self,
        content: str,
        media_urls: list | None = None,
        content_type: str = "REELS",
        **kwargs: Any,
    ) -> PostResult:
        """Post to Instagram via Graph API media container flow."""
        if not self.access_token:
            return PostResult(
                success=False,
                error="Instagram access token not configured. Complete OAuth to connect your account.",
            )
        if not self.instagram_account_id:
            return PostResult(
                success=False,
                error="Instagram Business Account ID not configured.",
            )
        if not media_urls or not media_urls[0]:
            return PostResult(success=False, error="No media URL provided for Instagram post.")

        ctype = (content_type or "REELS").upper()

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                container_url = f"{self.base_url}/{self.instagram_account_id}/media"

                if ctype == "REELS":
                    container_params = {
                        "media_type": "REELS",
                        "video_url": media_urls[0],
                        "caption": content,
                        "share_to_feed": "true",
                        "access_token": self.access_token,
                    }
                elif ctype == "CAROUSEL" and len(media_urls) > 1:
                    children_ids: list[str] = []
                    for url in media_urls[:10]:
                        child_resp = await client.post(
                            container_url,
                            data={
                                "image_url": url,
                                "is_carousel_item": "true",
                                "access_token": self.access_token,
                            },
                        )
                        if child_resp.is_success:
                            child_id = child_resp.json().get("id")
                            if child_id:
                                children_ids.append(child_id)
                        else:
                            logger.warning("Instagram carousel child creation failed: %s", child_resp.text)

                    if not children_ids:
                        return PostResult(success=False, error="Failed to create carousel media containers.")

                    container_params = {
                        "media_type": "CAROUSEL",
                        "children": ",".join(children_ids),
                        "caption": content,
                        "access_token": self.access_token,
                    }
                else:
                    container_params = {
                        "image_url": media_urls[0],
                        "caption": content,
                        "access_token": self.access_token,
                    }

                container_resp = await client.post(container_url, data=container_params)
                if not container_resp.is_success:
                    return PostResult(
                        success=False,
                        error=f"Instagram container creation failed: {container_resp.status_code} {container_resp.text}",
                    )

                container_id = container_resp.json().get("id")
                if not container_id:
                    return PostResult(success=False, error="Instagram did not return a container ID.")

                if ctype == "REELS":
                    for _ in range(30):
                        await asyncio.sleep(2)
                        status_resp = await client.get(
                            f"{self.base_url}/{container_id}",
                            params={"fields": "status_code", "access_token": self.access_token},
                        )
                        if status_resp.is_success:
                            status_code = status_resp.json().get("status_code")
                            if status_code == "FINISHED":
                                break
                            if status_code == "ERROR":
                                return PostResult(success=False, error="Instagram media processing failed.")
                    else:
                        return PostResult(success=False, error="Instagram media processing timed out.")

                publish_resp = await client.post(
                    f"{self.base_url}/{self.instagram_account_id}/media_publish",
                    data={"creation_id": container_id, "access_token": self.access_token},
                )
                if not publish_resp.is_success:
                    return PostResult(
                        success=False,
                        error=f"Instagram publish failed: {publish_resp.status_code} {publish_resp.text}",
                    )

                media_id = publish_resp.json().get("id")
                if not media_id:
                    return PostResult(success=False, error="Instagram publish did not return a media ID.")

                permalink = f"https://instagram.com/p/{media_id}"
                try:
                    link_resp = await client.get(
                        f"{self.base_url}/{media_id}",
                        params={"fields": "permalink", "access_token": self.access_token},
                    )
                    if link_resp.is_success:
                        permalink = link_resp.json().get("permalink", permalink)
                except Exception:
                    logger.debug("Instagram permalink fetch failed for %s", media_id)

                return PostResult(success=True, post_id=media_id, url=permalink)

        except httpx.TimeoutException:
            return PostResult(success=False, error="Instagram API request timed out.")
        except Exception as exc:
            logger.exception("Instagram posting failed")
            return PostResult(success=False, error=f"Instagram posting error: {exc}")

    async def post_reel(self, video_url: str, caption: str, hashtags: list | None = None) -> PostResult:
        """Post a Reel specifically."""
        full_caption = caption
        if hashtags:
            full_caption += "\n\n" + " ".join(f"#{tag}" for tag in hashtags)

        return await self.post_content(
            content=full_caption,
            media_urls=[video_url],
            content_type="REELS",
        )

    async def post_carousel(self, image_urls: list, caption: str) -> PostResult:
        """Post a carousel of images."""
        return await self.post_content(
            content=caption,
            media_urls=image_urls,
            content_type="CAROUSEL",
        )

    async def get_analytics(self, post_id: str) -> PlatformAnalytics:
        """Get analytics for an Instagram post via Insights API."""
        if not self.access_token:
            return PlatformAnalytics()
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self.base_url}/{post_id}/insights",
                    params={
                        "metric": "impressions,reach,likes,comments,shares",
                        "access_token": self.access_token,
                    },
                )
                if resp.status_code != 200:
                    return PlatformAnalytics()
                data = resp.json().get("data", [])
                metrics: dict[str, int] = {}
                for item in data:
                    metrics[item["name"]] = item.get("values", [{}])[0].get("value", 0)

                total = metrics.get("impressions", 0)
                engagement = metrics.get("likes", 0) + metrics.get("comments", 0) + metrics.get("shares", 0)
                rate = (engagement / total * 100) if total > 0 else 0.0
                return PlatformAnalytics(
                    views=metrics.get("impressions", 0),
                    likes=metrics.get("likes", 0),
                    comments=metrics.get("comments", 0),
                    shares=metrics.get("shares", 0),
                    engagement_rate=round(rate, 2),
                )
        except Exception as exc:
            logger.warning("Instagram get_analytics failed: %s", exc)
            return PlatformAnalytics()

    async def refresh_access_token(self) -> bool:
        """Refresh a long-lived Instagram/Meta access token."""
        if not self.access_token:
            return False
        if not settings.META_APP_ID or not settings.META_APP_SECRET:
            logger.warning("Instagram token refresh skipped: Meta app credentials are not configured.")
            return False
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{_GRAPH_BASE}/oauth/access_token",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": settings.META_APP_ID,
                        "client_secret": settings.META_APP_SECRET,
                        "fb_exchange_token": self.access_token,
                    },
                )
                if not resp.is_success:
                    logger.warning("Instagram token refresh failed: %s %s", resp.status_code, resp.text)
                    return False

                data = resp.json()
                token = data.get("access_token")
                if token:
                    self.access_token = token
                    return True
        except Exception as exc:
            logger.warning("Instagram token refresh failed: %s", exc)
        return False
