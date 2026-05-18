"""
YouTube integration for posting Shorts via YouTube Data API v3.

Uses resumable upload and explicit not-configured errors when credentials are missing.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import settings
from app.integrations.platforms.base import BasePlatform, PlatformAnalytics, PostResult

logger = logging.getLogger(__name__)

_YT_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
_YT_DATA_URL = "https://www.googleapis.com/youtube/v3"


class YouTubePlatform(BasePlatform):
    """YouTube integration for posting Shorts via Data API v3."""

    def __init__(self, access_token: str, refresh_token: str | None = None) -> None:
        super().__init__(access_token, refresh_token)
        self.base_url = _YT_DATA_URL
        self.upload_url = _YT_UPLOAD_URL

    async def post_content(
        self,
        content: str,
        media_urls: list | None = None,
        title: str | None = None,
        **kwargs: Any,
    ) -> PostResult:
        """
        Post a YouTube Short using resumable upload.

        Requires a valid OAuth2 token with youtube.upload scope and a downloadable video URL.
        """
        if not self.access_token:
            return PostResult(
                success=False,
                error="YouTube access token not configured. Complete OAuth to connect your account.",
            )

        if not media_urls or not media_urls[0]:
            return PostResult(
                success=False,
                error="No video URL provided for YouTube Short upload.",
            )

        short_title = (title or content[:100]).strip() or "Short"
        description = f"{content}\n\n#Shorts"
        hashtags = kwargs.get("hashtags", [])
        tags = ["Shorts"] + hashtags

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                video_resp = await client.get(media_urls[0], follow_redirects=True)
                if video_resp.status_code != 200:
                    return PostResult(
                        success=False,
                        error=f"Failed to download video from {media_urls[0]}: HTTP {video_resp.status_code}",
                    )

                video_bytes = video_resp.content
                content_type = video_resp.headers.get("content-type", "video/mp4")

                metadata = {
                    "snippet": {
                        "title": short_title[:100],
                        "description": description[:5000],
                        "tags": tags[:30],
                        "categoryId": "22",
                    },
                    "status": {
                        "privacyStatus": "public",
                        "selfDeclaredMadeForKids": False,
                    },
                }

                init_resp = await client.post(
                    f"{self.upload_url}?uploadType=resumable&part=snippet,status",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json; charset=UTF-8",
                        "X-Upload-Content-Type": content_type,
                        "X-Upload-Content-Length": str(len(video_bytes)),
                    },
                    json=metadata,
                )

                if init_resp.status_code not in (200, 201):
                    return PostResult(
                        success=False,
                        error=f"YouTube upload initiation failed: {init_resp.status_code} {init_resp.text}",
                    )

                upload_url = init_resp.headers.get("Location")
                if not upload_url:
                    return PostResult(success=False, error="YouTube did not return a resumable upload URL.")

                upload_resp = await client.put(
                    upload_url,
                    content=video_bytes,
                    headers={
                        "Content-Type": content_type,
                        "Content-Length": str(len(video_bytes)),
                    },
                )
                if upload_resp.status_code not in (200, 201):
                    return PostResult(
                        success=False,
                        error=f"YouTube video upload failed: {upload_resp.status_code} {upload_resp.text}",
                    )

                data = upload_resp.json()
                video_id = data.get("id")
                if not video_id:
                    return PostResult(success=False, error="YouTube upload succeeded but no video ID was returned.")

                return PostResult(
                    success=True,
                    post_id=video_id,
                    url=f"https://youtube.com/shorts/{video_id}",
                )

        except httpx.TimeoutException:
            return PostResult(success=False, error="YouTube upload timed out. The video may be too large.")
        except Exception as exc:
            logger.exception("YouTube upload failed")
            return PostResult(success=False, error=f"YouTube upload error: {exc}")

    async def get_analytics(self, post_id: str) -> PlatformAnalytics:
        """Get analytics for a YouTube video via the Data API."""
        if not self.access_token:
            return PlatformAnalytics()
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{self.base_url}/videos",
                    params={"part": "statistics", "id": post_id},
                    headers={"Authorization": f"Bearer {self.access_token}"},
                )
                if resp.status_code != 200:
                    return PlatformAnalytics()
                items = resp.json().get("items", [])
                if not items:
                    return PlatformAnalytics()
                stats = items[0].get("statistics", {})
                views = int(stats.get("viewCount", 0))
                likes = int(stats.get("likeCount", 0))
                comments = int(stats.get("commentCount", 0))
                total = views if views > 0 else 1
                rate = (likes + comments) / total * 100
                return PlatformAnalytics(
                    views=views,
                    likes=likes,
                    comments=comments,
                    shares=0,
                    engagement_rate=round(rate, 2),
                )
        except Exception as exc:
            logger.warning("YouTube get_analytics failed: %s", exc)
            return PlatformAnalytics()

    async def refresh_access_token(self) -> bool:
        """Refresh YouTube access token via Google OAuth2."""
        if not self.refresh_token:
            logger.warning("YouTube token refresh skipped: refresh token is not configured.")
            return False
        if not settings.YOUTUBE_CLIENT_ID or not settings.YOUTUBE_CLIENT_SECRET:
            logger.warning("YouTube token refresh skipped: client credentials are not configured.")
            return False
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": settings.YOUTUBE_CLIENT_ID,
                        "client_secret": settings.YOUTUBE_CLIENT_SECRET,
                        "grant_type": "refresh_token",
                        "refresh_token": self.refresh_token,
                    },
                )
                if not resp.is_success:
                    logger.warning("YouTube token refresh failed: %s %s", resp.status_code, resp.text)
                    return False

                data = resp.json()
                token = data.get("access_token")
                if token:
                    self.access_token = token
                    return True
        except Exception as exc:
            logger.warning("YouTube token refresh failed: %s", exc)
        return False
