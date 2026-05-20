"""
HuggingFace + Qwen powered content generation service.

Primary text generation uses the HuggingFace Inference API (Serverless) or the
Qwen (DashScope) API depending on which keys are configured.

Priority order (lowest cost first):
  1. Qwen via HuggingFace Serverless (Qwen/Qwen2.5-72B-Instruct) – free tier
  2. HuggingFace Serverless with Mistral-7B-Instruct-v0.2 – free tier
  3. Template-based fallback (no API key required)

Also provides helpers used by the power tools:
  - summarize()         → BART summarisation
  - analyze_sentiment() → DistilBERT sentiment
  - classify_topics()   → BART zero-shot classification
  - extract_keywords()  → Qwen/Mistral keyword extraction
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
from app.core.config import settings
from app.services.genx_client import GenXClient
from app.services.social_rules import as_prompt_guidance, resolve_platform_key

# Default free model – works on the free/Pro tier without a PRO subscription
_DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"
# Qwen model served via HuggingFace Inference API (free serverless tier)
_QWEN_MODEL = "Qwen/Qwen2.5-72B-Instruct"
_HF_INFERENCE_URL = "https://api-inference.huggingface.co/models/{model}"

# Specialist model handles (all free on HF Serverless)
_SUMMARIZE_MODEL = "facebook/bart-large-cnn"
_SENTIMENT_MODEL = "distilbert-base-uncased-finetuned-sst-2-english"
_ZERO_SHOT_MODEL = "facebook/bart-large-mnli"

# Platform-specific guidance injected into the prompt
_PLATFORM_HINTS: dict[str, dict[str, str]] = {
    "youtube": {
        "format": "YouTube Shorts video script",
        "caption_hint": "engaging video description with call-to-action",
        "length": "150-300 characters",
        "hashtag_count": "5-8",
    },
    "tiktok": {
        "format": "TikTok short video caption",
        "caption_hint": "hook-first, trend-aware, energetic caption",
        "length": "100-200 characters",
        "hashtag_count": "5-10",
    },
    "instagram": {
        "format": "Instagram Reel / post caption",
        "caption_hint": "visually descriptive, story-driven caption ending with a question",
        "length": "150-300 characters",
        "hashtag_count": "10-15",
    },
    "facebook": {
        "format": "Facebook post",
        "caption_hint": "friendly, conversational post with a link or CTA",
        "length": "200-400 characters",
        "hashtag_count": "3-5",
    },
    "twitter": {
        "format": "Tweet / X post",
        "caption_hint": "punchy, insightful tweet under 280 characters",
        "length": "200-260 characters",
        "hashtag_count": "2-3",
    },
    "x": {
        "format": "Tweet / X post",
        "caption_hint": "punchy, insightful post under 280 characters",
        "length": "200-260 characters",
        "hashtag_count": "2-3",
    },
    "linkedin": {
        "format": "LinkedIn professional post",
        "caption_hint": "thought-leadership post with numbered insights or bullet points",
        "length": "400-600 characters",
        "hashtag_count": "3-5",
    },
    "pinterest": {
        "format": "Pinterest pin description",
        "caption_hint": "inspiring, keyword-rich description that tells a visual story with a clear CTA",
        "length": "150-300 characters",
        "hashtag_count": "5-10",
    },
    "reddit": {
        "format": "Reddit post title + body",
        "caption_hint": "engaging, value-first post that fits subreddit culture without being salesy",
        "length": "200-500 characters",
        "hashtag_count": "0",
    },
    "bluesky": {
        "format": "Bluesky skeet / post",
        "caption_hint": "conversational, thoughtful post similar to early Twitter style",
        "length": "100-280 characters",
        "hashtag_count": "2-4",
    },
    "threads": {
        "format": "Threads post",
        "caption_hint": "conversational, engaging post that sparks discussion",
        "length": "150-300 characters",
        "hashtag_count": "3-5",
    },
    "telegram": {
        "format": "Telegram channel message",
        "caption_hint": "informative, value-packed message with a clear link or CTA for the channel audience",
        "length": "200-400 characters",
        "hashtag_count": "2-4",
    },
    "reels": {
        "format": "Instagram Reels caption",
        "caption_hint": "hook-first reel caption with CTA",
        "length": "120-280 characters",
        "hashtag_count": "5-10",
    },
    "shorts": {
        "format": "YouTube Shorts description",
        "caption_hint": "short-form video description with clear CTA",
        "length": "120-280 characters",
        "hashtag_count": "4-8",
    },
    "snapchat": {
        "format": "Snapchat Story caption",
        "caption_hint": "short, punchy, visual caption with energy and urgency — Snap-native style",
        "length": "50-150 characters",
        "hashtag_count": "2-4",
    },
}


def _clean_json(raw: str) -> str:
    """Strip markdown code fences from model output."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


def optimize_for_platform(text: str, platform: str) -> str:
    """Apply platform-specific formatting rules to generated text.

    * Twitter  – hard-truncate to 280 characters.
    * LinkedIn – insert line breaks every 2-3 sentences for readability.
    * TikTok   – prefix with a hook question when the text doesn't start with one.
    * YouTube  – append ``#Shorts`` if not already present.
    * Others   – returned unchanged.
    """
    if not text:
        return text

    p = platform.lower()

    if p == "twitter":
        if len(text) > 280:
            text = text[:277].rsplit(" ", 1)[0] + "..."

    elif p == "linkedin":
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        chunks: list[str] = []
        buf: list[str] = []
        for sent in sentences:
            buf.append(sent)
            if len(buf) >= 2:
                chunks.append(" ".join(buf))
                buf = []
        if buf:
            chunks.append(" ".join(buf))
        text = "\n\n".join(chunks)

    elif p == "tiktok":
        if not text.lstrip().endswith("?") and not text.lstrip().startswith(
            tuple(w for w in ["What", "How", "Why", "Did", "Can", "Do", "Is", "Are", "Have", "Want"])
        ):
            text = "Want to know a secret? 👀\n" + text

    elif p == "youtube":
        if "#Shorts" not in text and "#shorts" not in text:
            text = text.rstrip() + " #Shorts"

    return text


class HuggingFaceGenerator:
    """
    Generates social media content using the HuggingFace Inference API.

    When a Qwen API key (QWEN_API_KEY) is configured the generator uses the
    Qwen/Qwen2.5-72B-Instruct model on HuggingFace Serverless for higher-quality,
    low-cost generation.  Falls back to Mistral-7B if only a HF token is set,
    and finally to template-based generation if no keys are available.

    Also provides general NLP utilities (summarise, sentiment, classify).
    """

    def __init__(
        self,
        hf_token: str,
        model: str = _DEFAULT_MODEL,
        qwen_key: str = "",
        genx_key: str = "",
    ):
        self.hf_token = hf_token
        self.qwen_key = qwen_key  # QWEN_API_KEY (DashScope or HF)
        self.genx_key = genx_key or settings.GENX_API_KEY
        self._genx = GenXClient(api_key=self.genx_key)
        self._genx_enabled = bool(self.genx_key and self._genx.ready)
        # If a Qwen key is provided, prefer the Qwen model via HF Serverless
        if qwen_key:
            self.model = _QWEN_MODEL
            self._active_token = qwen_key
        else:
            self.model = model
            self._active_token = hf_token
        self._inference_url = _HF_INFERENCE_URL.format(model=self.model)

    # ------------------------------------------------------------------
    # Content generation
    # ------------------------------------------------------------------

    async def generate_content(
        self,
        webapp_data: dict[str, Any],
        platform: str,
    ) -> dict[str, Any]:
        """Generate a complete content package for one platform."""
        normalized_platform = resolve_platform_key(platform)
        hint = _PLATFORM_HINTS.get(normalized_platform, _PLATFORM_HINTS["instagram"])
        prompt = self._build_prompt(webapp_data, normalized_platform, hint)
        raw = await self._call_text_generation(self._inference_url, prompt)
        return self._parse_response(raw, platform, webapp_data)

    async def generate_batch(
        self,
        webapp_data: dict[str, Any],
        platforms: list[str],
    ) -> dict[str, dict[str, Any]]:
        """Generate content for multiple platforms concurrently."""
        import asyncio

        results: dict[str, dict[str, Any]] = {}
        for platform in platforms:
            try:
                results[platform] = await self.generate_content(webapp_data, platform)
            except Exception as exc:
                results[platform] = self._fallback_content(webapp_data, platform, str(exc))
        return results

    # ------------------------------------------------------------------
    # Remix  (Content Remix Engine)
    # ------------------------------------------------------------------

    async def remix_to_platform(
        self,
        source_text: str,
        platform: str,
        trending_hashtags: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Remix arbitrary source content (blog post, article, etc.) into a
        platform-optimised social snippet.
        """
        hint = _PLATFORM_HINTS.get(platform, _PLATFORM_HINTS["instagram"])
        hashtag_hint = (
            f"Incorporate some of these trending hashtags where natural: {', '.join(trending_hashtags[:8])}"
            if trending_hashtags
            else "Add relevant trending hashtags."
        )

        system = (
            "You are a viral social media copywriter for AmarktAI Marketing. "
            "Transform the provided content into platform-native posts. "
            "Respond ONLY with valid JSON."
        )
        user = f"""Remix this content into a {hint['format']}:

SOURCE CONTENT:
{source_text[:2000]}

Requirements:
- Style: {hint['caption_hint']}
- Caption length: {hint['length']}
- {hashtag_hint}
- Make it native to {platform} style

JSON format:
{{
  "title": "short hook title",
  "caption": "full post caption",
  "hashtags": ["tag1", "tag2"],
  "key_points": ["point1", "point2", "point3"]
}}"""

        prompt = f"<s>[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{user} [/INST]"
        raw = await self._call_text_generation(self._inference_url, prompt)
        result = self._parse_response(raw, platform, {"name": "Content", "url": "", "description": source_text[:100], "target_audience": "general", "key_features": []})
        result["key_points"] = []
        # Try to extract key_points from raw JSON
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                obj = json.loads(_clean_json(match.group()))
                result["key_points"] = obj.get("key_points", [])
        except Exception:
            pass
        return result

    # ------------------------------------------------------------------
    # Summarisation  (used by Competitor Analyzer + Remix)
    # ------------------------------------------------------------------

    async def summarize(self, text: str, max_length: int = 150) -> str:
        """Summarise text using BART."""
        if len(text) < 100:
            return text
        if self._genx_enabled:
            prompt = (
                f"Summarize the following text in under {max_length} words while preserving key marketing insights:\n\n"
                f"{text[:1800]}"
            )
            raw = await self._call_text_generation(self._inference_url, prompt, max_tokens=220)
            return raw[:1000] if raw else text[:200]
        url = _HF_INFERENCE_URL.format(model=_SUMMARIZE_MODEL)
        payload = {
            "inputs": text[:1024],
            "parameters": {"max_length": max_length, "min_length": 30, "do_sample": False},
        }
        try:
            data = await self._post_hf(url, payload)
            if isinstance(data, list) and data:
                return data[0].get("summary_text", text[:200])
        except Exception:
            pass
        return text[:200]

    # ------------------------------------------------------------------
    # Sentiment analysis  (used by Feedback Alchemy)
    # ------------------------------------------------------------------

    async def analyze_sentiment(self, text: str) -> dict[str, Any]:
        """
        Classify text sentiment.
        Returns {"label": "POSITIVE"|"NEGATIVE"|"NEUTRAL", "score": float}
        """
        if self._genx_enabled:
            prompt = (
                "Classify sentiment for this text as POSITIVE, NEGATIVE, or NEUTRAL. "
                "Return ONLY JSON: {\"label\":\"...\",\"score\":0.0}\n\n"
                f"Text: {text[:700]}"
            )
            raw = await self._call_text_generation(self._inference_url, prompt, max_tokens=120)
            try:
                match = re.search(r"\{.*\}", raw, re.DOTALL)
                if match:
                    obj = json.loads(_clean_json(match.group()))
                    return {
                        "label": str(obj.get("label", "NEUTRAL")).upper(),
                        "score": round(float(obj.get("score", 0.5)), 3),
                    }
            except Exception:
                pass
        url = _HF_INFERENCE_URL.format(model=_SENTIMENT_MODEL)
        payload = {"inputs": text[:512]}
        try:
            data = await self._post_hf(url, payload)
            if isinstance(data, list) and data:
                top = sorted(data[0], key=lambda x: x.get("score", 0), reverse=True)[0]
                return {"label": top["label"], "score": round(top["score"], 3)}
        except Exception:
            pass
        return {"label": "NEUTRAL", "score": 0.5}

    # ------------------------------------------------------------------
    # Zero-shot classification  (competitor gap analysis)
    # ------------------------------------------------------------------

    async def classify_topics(
        self, text: str, candidate_labels: list[str]
    ) -> dict[str, float]:
        """
        Zero-shot classification.
        Returns {label: score} dict sorted by descending score.
        """
        if self._genx_enabled:
            prompt = (
                "Score how relevant each label is to the text. "
                "Return ONLY JSON object where keys are labels and values are scores between 0 and 1.\n\n"
                f"Labels: {candidate_labels}\n\nText: {text[:700]}"
            )
            raw = await self._call_text_generation(self._inference_url, prompt, max_tokens=220)
            try:
                match = re.search(r"\{.*\}", raw, re.DOTALL)
                if match:
                    obj = json.loads(_clean_json(match.group()))
                    return {k: float(v) for k, v in obj.items() if k in candidate_labels}
            except Exception:
                pass
        url = _HF_INFERENCE_URL.format(model=_ZERO_SHOT_MODEL)
        payload = {
            "inputs": text[:512],
            "parameters": {"candidate_labels": candidate_labels},
        }
        try:
            data = await self._post_hf(url, payload)
            if isinstance(data, dict):
                return dict(zip(data.get("labels", []), data.get("scores", [])))
        except Exception:
            pass
        return {lbl: 1 / len(candidate_labels) for lbl in candidate_labels}

    # ------------------------------------------------------------------
    # Keyword / hashtag extraction  (Remix + Competitor)
    # ------------------------------------------------------------------

    async def extract_keywords(self, text: str, count: int = 10) -> list[str]:
        """Extract the most relevant keywords from text using Mistral."""
        system = "You are a keyword extraction assistant. Output ONLY a JSON array of keywords."
        user = f"Extract the {count} most important marketing keywords from:\n\n{text[:800]}\n\nJSON array only:"
        prompt = f"<s>[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{user} [/INST]"
        raw = await self._call_text_generation(self._inference_url, prompt, max_tokens=200)
        try:
            match = re.search(r"\[.*?\]", raw, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            pass
        # Fallback: split on commas
        words = re.findall(r"\b[A-Za-z][A-Za-z0-9]{2,}\b", raw)
        return list(dict.fromkeys(words))[:count]

    # ------------------------------------------------------------------
    # Competitor / Feedback analysis generators
    # ------------------------------------------------------------------

    async def generate_competitor_insights(
        self,
        competitor_name: str,
        scraped_content: str,
        our_niche: str,
    ) -> dict[str, Any]:
        """Analyse competitor content and generate strategic insights."""
        system = "You are a strategic marketing analyst. Respond ONLY with JSON."
        user = f"""Analyse this competitor's content and provide strategic insights.

Competitor: {competitor_name}
Our niche: {our_niche}

Competitor content sample:
{scraped_content[:1500]}

Provide a JSON object:
{{
  "content_strategy": "brief description of their approach",
  "strengths": ["strength1", "strength2"],
  "weaknesses": ["weakness1", "weakness2"],
  "content_gaps": ["gap1", "gap2", "gap3"],
  "recommended_counter_strategies": ["strategy1", "strategy2"],
  "top_topics": ["topic1", "topic2", "topic3"],
  "estimated_posting_frequency": "X posts/day",
  "audience_engagement_level": "high|medium|low"
}}"""
        prompt = f"<s>[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{user} [/INST]"
        raw = await self._call_text_generation(self._inference_url, prompt)
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(_clean_json(match.group()))
        except Exception:
            pass
        return {
            "content_strategy": "Analysis unavailable",
            "strengths": [],
            "weaknesses": [],
            "content_gaps": [],
            "recommended_counter_strategies": [],
            "top_topics": [],
            "estimated_posting_frequency": "unknown",
            "audience_engagement_level": "medium",
        }

    async def generate_blog_post(
        self,
        webapp_data: dict[str, Any],
        topic: str | None = None,
        keywords: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a long-form SEO blog post from webapp data.
        Returns title, slug, meta_description, sections, and cta.
        """
        name = webapp_data.get("name", "")
        description = webapp_data.get("description", "")
        audience = webapp_data.get("target_audience", "general audience")
        features = ", ".join(webapp_data.get("key_features", [])[:5])
        url = webapp_data.get("url", "")

        kw_hint = f"Target keywords: {', '.join(keywords[:8])}" if keywords else ""
        topic_hint = f"Topic: {topic}" if topic else f"Topic: how {name} helps {audience}"

        system = (
            "You are an expert SEO content writer for AmarktAI Marketing. "
            "Write authoritative, long-form blog posts that rank on Google and drive organic leads. "
            "Respond ONLY with valid JSON."
        )
        user = f"""Write a complete SEO blog post for this product.

Business: {name}
Description: {description}
Target Audience: {audience}
Key Features: {features}
Website: {url}
{topic_hint}
{kw_hint}

Return ONLY a JSON object:
{{
  "title": "SEO-optimized headline (max 70 chars)",
  "slug": "url-friendly-slug",
  "meta_description": "150-160 char meta description",
  "reading_time_mins": 5,
  "sections": [
    {{"heading": "Introduction", "content": "200+ word intro paragraph"}},
    {{"heading": "Key Benefits", "content": "Detailed benefits section"}},
    {{"heading": "How It Works", "content": "Step-by-step explanation"}},
    {{"heading": "Who Is It For?", "content": "Target audience section"}},
    {{"heading": "Final Thoughts", "content": "Conclusion with call-to-action"}}
  ],
  "target_keywords": ["kw1", "kw2", "kw3", "kw4", "kw5"],
  "cta_text": "Compelling CTA sentence",
  "cta_url": "{url}"
}}"""

        prompt = f"<s>[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{user} [/INST]"
        raw = await self._call_text_generation(self._inference_url, prompt, max_tokens=900)
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(_clean_json(match.group()))
        except Exception:
            pass
        return {
            "title": f"How {name} Can Transform Your {audience} Experience",
            "slug": name.lower().replace(" ", "-"),
            "meta_description": f"Discover how {name} helps {audience}. {description[:100]}",
            "reading_time_mins": 5,
            "sections": [
                {"heading": "Introduction", "content": f"{name} is designed for {audience}. {description}"},
                {"heading": "Key Benefits", "content": f"Key features: {features}"},
                {"heading": "Get Started", "content": f"Visit {url} to learn more."},
            ],
            "target_keywords": [name, audience, "marketing", "automation"],
            "cta_text": f"Try {name} free today",
            "cta_url": url,
        }

    async def generate_video_script(
        self,
        webapp_data: dict[str, Any],
        platform: str,
    ) -> dict[str, Any]:
        """
        Generate a platform-optimised short video script using HuggingFace.
        Used for YouTube Shorts, TikTok, Instagram Reels, Snapchat Spotlight.
        """
        name = webapp_data.get("name", "the product")
        description = webapp_data.get("description", "")
        durations = {"youtube": "45-60 seconds", "tiktok": "15-30 seconds", "snapchat": "10-15 seconds"}
        duration = durations.get(platform, "30 seconds")

        system = (
            "You are a viral video scriptwriter for AmarktAI Marketing. "
            "Write concise, hook-driven video scripts. Respond ONLY with valid JSON."
        )
        user = f"""Write a {duration} {platform} video script for '{name}'.
Description: {description[:200]}

JSON format:
{{
  "title": "Video title with #Shorts if YouTube",
  "hook": "Opening hook line (0-3s)",
  "scenes": [
    {{"time": "0-3s", "visual": "...", "audio": "...", "text_overlay": "..."}}
  ],
  "cta": "Call to action text",
  "description": "Full video description for upload",
  "hashtags": ["Shorts", "tag2", "tag3"]
}}"""

        prompt = f"<s>[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{user} [/INST]"
        raw = await self._call_text_generation(self._inference_url, prompt, max_tokens=600)
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(_clean_json(match.group()))
        except Exception:
            pass
        return {
            "title": f"How {name} Works #Shorts",
            "hook": f"This is {name} and it changes everything...",
            "scenes": [
                {"time": "0-3s", "visual": "Product logo/hook", "audio": f"Meet {name}", "text_overlay": "🚀"},
                {"time": "3-20s", "visual": "Key feature demo", "audio": f"{name} helps you work smarter", "text_overlay": "Game changer!"},
                {"time": "20-30s", "visual": "CTA screen", "audio": "Try it free today!", "text_overlay": "Link in bio 👆"},
            ],
            "cta": f"Try {name} free",
            "description": f"{description}\n\n#Shorts #AI #Marketing",
            "hashtags": ["Shorts", "AI", "Marketing", "AmarktAINetwork"],
        }

    async def generate_comment_reply(
        self,
        comment_text: str,
        platform: str,
        webapp_name: str,
        sentiment: str = "neutral",
    ) -> dict[str, Any]:
        """Generate a contextual reply to a social media comment using HF."""
        system = (
            "You are a friendly, professional community manager for AmarktAI Marketing. "
            "Write genuine, helpful replies. Respond ONLY with valid JSON."
        )
        tone_hint = {
            "positive": "grateful and encouraging",
            "negative": "empathetic and solution-focused",
            "neutral": "friendly and informative",
        }.get(sentiment, "friendly")

        user = f"""Reply to this {platform} comment about {webapp_name}:

Comment: {comment_text[:300]}
Sentiment: {sentiment}
Tone required: {tone_hint}

JSON format:
{{
  "reply": "Your reply text (max 250 chars)",
  "confidence": 0.85,
  "tone": "{tone_hint}",
  "lead_potential": true
}}"""

        prompt = f"<s>[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{user} [/INST]"
        raw = await self._call_text_generation(self._inference_url, prompt, max_tokens=300)
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(_clean_json(match.group()))
        except Exception:
            pass
        return {
            "reply": f"Thanks for your comment! 😊 Feel free to check out {webapp_name} for more.",
            "confidence": 0.6,
            "tone": tone_hint,
            "lead_potential": False,
        }

    async def score_lead_intelligence(
        self,
        qualifier_text: str,
        base_score: int,
    ) -> int:
        """
        Use HF sentiment + classification to boost the lead score.
        Returns adjusted score (0-100).
        """
        try:
            sentiment = await self.analyze_sentiment(qualifier_text)
            # Positive sentiment → buyer intent
            if sentiment["label"] == "POSITIVE" and sentiment["score"] > 0.75:
                base_score = min(base_score + 15, 100)
            elif sentiment["label"] == "NEGATIVE":
                base_score = max(base_score - 10, 0)

            # Zero-shot classify for purchase intent
            intent_scores = await self.classify_topics(
                qualifier_text,
                ["ready to buy", "just browsing", "needs information", "urgent requirement"],
            )
            top_intent = max(intent_scores, key=intent_scores.get)
            if top_intent == "ready to buy":
                base_score = min(base_score + 20, 100)
            elif top_intent == "urgent requirement":
                base_score = min(base_score + 15, 100)
        except Exception:
            pass
        return base_score

    async def generate_echo_amplification(
        self,
        trigger_text: str,
        brand_voice: str,
        platforms: list[str],
    ) -> dict[str, Any]:
        """Turn a visitor query/comment into amplified social content."""
        platforms_str = ", ".join(platforms[:4])
        system = "You are a viral content strategist. Respond ONLY with valid JSON."
        user = f"""Transform this visitor interaction into amplified social content.

Visitor said: {trigger_text[:300]}
Brand voice: {brand_voice}
Target platforms: {platforms_str}

JSON format:
{{
  "virality_score": 72,
  "thread_posts": [
    {{"platform": "twitter", "content": "Thread post 1", "hashtags": ["tag1"]}},
    {{"platform": "linkedin", "content": "LinkedIn version"}}
  ],
  "story_content": [{{"platform": "instagram", "content": "Story hook"}}],
  "priority": "high"
}}"""

        prompt = f"<s>[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{user} [/INST]"
        raw = await self._call_text_generation(self._inference_url, prompt, max_tokens=500)
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(_clean_json(match.group()))
        except Exception:
            pass
        return {
            "virality_score": 50,
            "thread_posts": [{"platform": p, "content": f"Echo: {trigger_text[:100]}", "hashtags": []} for p in platforms[:2]],
            "story_content": [],
            "priority": "medium",
        }

    async def generate_seo_mirage(
        self,
        input_text: str,
        platform: str,
        url: str = "",
    ) -> dict[str, Any]:
        """Generate SEO-optimized metadata and hashtags for a post."""
        system = "You are an SEO specialist. Respond ONLY with valid JSON."
        user = f"""Create SEO-optimised metadata for this {platform} content.

Content: {input_text[:500]}
URL: {url}

JSON format:
{{
  "seo_title": "Optimised title (max 60 chars)",
  "seo_description": "150 char description",
  "alt_text": "Image alt text",
  "optimized_hashtags": ["tag1", "tag2", "tag3"],
  "algorithm_tips": ["tip1", "tip2"],
  "enhanced_caption": "SEO-enhanced version of the content",
  "keyword_density": {{"primaryKeyword": 2.5}}
}}"""

        prompt = f"<s>[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{user} [/INST]"
        raw = await self._call_text_generation(self._inference_url, prompt, max_tokens=400)
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(_clean_json(match.group()))
        except Exception:
            pass
        return {
            "seo_title": input_text[:60],
            "seo_description": input_text[:150],
            "alt_text": "Marketing content image",
            "optimized_hashtags": ["marketing", "growth", "ai"],
            "algorithm_tips": [f"Post at peak {platform} hours", "Use first comment for extra hashtags"],
            "enhanced_caption": input_text,
            "keyword_density": {},
        }

    async def generate_harmony_pricing(
        self,
        product_name: str,
        current_price: str,
        competitor_prices: list[str],
        buzz_context: str,
    ) -> dict[str, Any]:
        """Recommend optimal price and ad copy variants."""
        system = "You are a pricing strategist. Respond ONLY with valid JSON."
        user = f"""Recommend optimal pricing for this product.

Product: {product_name}
Current price: {current_price}
Competitor prices: {', '.join(competitor_prices[:5])}
Market buzz: {buzz_context[:300]}

JSON format:
{{
  "recommended_price": "$X.XX",
  "price_rationale": "Why this price",
  "ad_copy_variants": [
    {{"price_point": "$X.XX", "headline": "Ad headline", "body": "Ad body"}}
  ],
  "simulated_roi": {{"low": "2x", "mid": "3.5x", "high": "5x"}},
  "buzz_score": 65
}}"""

        prompt = f"<s>[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{user} [/INST]"
        raw = await self._call_text_generation(self._inference_url, prompt, max_tokens=400)
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(_clean_json(match.group()))
        except Exception:
            pass
        return {
            "recommended_price": current_price,
            "price_rationale": "Competitive market positioning",
            "ad_copy_variants": [{"price_point": current_price, "headline": f"Get {product_name}", "body": "Best value option"}],
            "simulated_roi": {"low": "1.5x", "mid": "2.5x", "high": "4x"},
            "buzz_score": 50,
        }

    async def generate_audience_map(
        self,
        webapp_data: dict[str, Any],
        platform: str,
        data_summary: str,
    ) -> dict[str, Any]:
        """Map psychographic audience segments."""
        system = "You are an audience research specialist. Respond ONLY with valid JSON."
        user = f"""Map audience psychographic segments for this product on {platform}.

Product: {webapp_data.get('name', '')}
Description: {webapp_data.get('description', '')}
Target: {webapp_data.get('target_audience', '')}
Data: {data_summary[:400]}

JSON format:
{{
  "segments": [
    {{"name": "Segment A", "description": "Profile", "size_pct": 35, "interests": ["int1", "int2"]}},
    {{"name": "Segment B", "description": "Profile", "size_pct": 25, "interests": ["int1"]}}
  ],
  "campaign_suggestions": [
    {{"segment": "Segment A", "campaign_idea": "Idea", "predicted_ctr": 3.2}}
  ],
  "targeting_recommendations": ["rec1", "rec2"],
  "cross_platform_insights": ["insight1"],
  "response_mirage": {{"Segment A": "Likely response", "Segment B": "Likely response"}}
}}"""

        prompt = f"<s>[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{user} [/INST]"
        raw = await self._call_text_generation(self._inference_url, prompt, max_tokens=500)
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(_clean_json(match.group()))
        except Exception:
            pass
        return {
            "segments": [
                {"name": "Core Audience", "description": webapp_data.get("target_audience", ""), "size_pct": 60, "interests": ["productivity", "automation"]},
            ],
            "campaign_suggestions": [],
            "targeting_recommendations": [f"Target {platform} users interested in {webapp_data.get('category', 'tech')}"],
            "cross_platform_insights": [],
            "response_mirage": {},
        }

    async def generate_ad_alchemy(
        self,
        product: str,
        current_copy: str,
        platform: str,
    ) -> dict[str, Any]:
        """Generate A/B tested ad copy variants."""
        system = "You are a direct-response copywriter. Respond ONLY with valid JSON."
        user = f"""Create 3 A/B ad copy variants for {platform}.

Product: {product}
Current copy: {current_copy[:300]}

JSON format:
{{
  "variants": [
    {{"variant_id": "A", "headline": "Headline A", "body": "Body A", "cta": "CTA A", "score": 72}},
    {{"variant_id": "B", "headline": "Headline B", "body": "Body B", "cta": "CTA B", "score": 85}},
    {{"variant_id": "C", "headline": "Headline C", "body": "Body C", "cta": "CTA C", "score": 68}}
  ],
  "recommended_winner": {{"variant_id": "B", "reason": "Why B wins"}},
  "global_benchmark_comparison": {{"ctr_benchmark": "2.5%", "our_predicted_ctr": "3.8%"}},
  "improvement_suggestions": ["Suggestion 1", "Suggestion 2"]
}}"""

        prompt = f"<s>[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{user} [/INST]"
        raw = await self._call_text_generation(self._inference_url, prompt, max_tokens=500)
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(_clean_json(match.group()))
        except Exception:
            pass
        return {
            "variants": [
                {"variant_id": "A", "headline": f"Try {product}", "body": current_copy[:100], "cta": "Get Started", "score": 60},
                {"variant_id": "B", "headline": f"Transform with {product}", "body": "AI-powered results", "cta": "Start Free", "score": 75},
            ],
            "recommended_winner": {"variant_id": "B", "reason": "More compelling CTA"},
            "global_benchmark_comparison": {"ctr_benchmark": "2.5%", "our_predicted_ctr": "3.2%"},
            "improvement_suggestions": ["Use numbers in headline", "Add social proof"],
        }

    async def generate_feedback_insights(
        self,
        feedback_texts: list[str],
        business_context: str,
    ) -> dict[str, Any]:
        """Transform raw feedback into marketing recommendations."""
        combined = "\n---\n".join(feedback_texts[:20])
        system = "You are a marketing strategist. Respond ONLY with JSON."
        user = f"""Analyse these customer reviews and generate marketing recommendations.

Business: {business_context}

Reviews:
{combined[:2000]}

Provide a JSON object:
{{
  "overall_sentiment": "positive|negative|mixed",
  "sentiment_score": 0.75,
  "key_themes": ["theme1", "theme2", "theme3"],
  "praise_points": ["feature1", "feature2"],
  "pain_points": ["issue1", "issue2"],
  "ad_copy_suggestions": ["copy1", "copy2", "copy3"],
  "response_templates": [
    {{"scenario": "positive review", "template": "Thank you..."}},
    {{"scenario": "negative review", "template": "We're sorry..."}}
  ],
  "ab_test_ideas": [
    {{"variant_a": "headline A", "variant_b": "headline B", "hypothesis": "..."}}
  ]
}}"""
        prompt = f"<s>[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{user} [/INST]"
        raw = await self._call_text_generation(self._inference_url, prompt)
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                return json.loads(_clean_json(match.group()))
        except Exception:
            pass
        return {
            "overall_sentiment": "mixed",
            "sentiment_score": 0.5,
            "key_themes": [],
            "praise_points": [],
            "pain_points": [],
            "ad_copy_suggestions": [],
            "response_templates": [],
            "ab_test_ideas": [],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        webapp_data: dict[str, Any],
        platform: str,
        hint: dict[str, str],
    ) -> str:
        normalized_platform = resolve_platform_key(platform)
        name = webapp_data.get("name", "our app")
        description = webapp_data.get("description", "")
        audience = webapp_data.get("target_audience", "general audience")
        features = ", ".join(webapp_data.get("key_features", [])[:4])
        url = webapp_data.get("url", "")
        social_guidance = as_prompt_guidance(normalized_platform, "b2c")

        system = (
            "You are an expert social media copywriter for AmarktAI Marketing. "
            "You create high-converting content that drives leads and engagement without spammy repetition. "
            "Do not claim private algorithm certainty. Follow platform policy-safe guidance. "
            "Market the selected business, not AmarktAI. Never use #Amarktai unless the business itself is Amarktai. "
            "Always respond with valid JSON only – no markdown, no extra text."
        )

        user = f"""Create a {hint['format']} for this business:

Business: {name}
Description: {description}
Target audience: {audience}
Key features: {features}
Website: {url}

Requirements:
- Caption style: {hint['caption_hint']}
- Caption length: {hint['length']}
- Include {hint['hashtag_count']} relevant hashtags
- The content must drive leads to the website
- Platform guidance: {social_guidance}
- Include one natural CTA and avoid repetitive/spammy phrasing
- If content is risky (regulated claims), keep wording conservative for human review
- Designed and created by AmarktAI Marketing

Respond ONLY with a JSON object with these exact keys:
{{
  "title": "short punchy title (max 100 chars)",
  "caption": "the full post caption",
  "hashtags": ["tag1", "tag2", "tag3"]
}}"""

        return f"<s>[INST] <<SYS>>\n{system}\n<</SYS>>\n\n{user} [/INST]"

    async def _call_text_generation(
        self, url: str, prompt: str, max_tokens: int = 512
    ) -> str:
        if self._genx_enabled:
            result = await self._genx.generate_text(
                prompt,
                system="You are an expert AI assistant for marketing content generation.",
                task="copy",
                max_tokens=max_tokens,
            )
            if result and result.get("text"):
                return str(result["text"])
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": 0.8,
                "top_p": 0.9,
                "do_sample": True,
                "return_full_text": False,
            },
        }
        data = await self._post_hf(url, payload)
        if isinstance(data, list) and data:
            return data[0].get("generated_text", "")
        if isinstance(data, dict):
            return data.get("generated_text", str(data))
        return str(data)

    async def _post_hf(self, url: str, payload: dict) -> Any:
        headers = {
            "Authorization": f"Bearer {self._active_token}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    def _parse_response(
        self,
        raw: str,
        platform: str,
        webapp_data: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                obj = json.loads(_clean_json(match.group()))
                title = obj.get("title") or webapp_data.get("name", "New Post")
                caption = obj.get("caption") or ""
                hashtags = obj.get("hashtags") or []
                if isinstance(hashtags, list):
                    hashtags = [h.lstrip("#") for h in hashtags]
                caption = optimize_for_platform(caption, platform)
                return {"title": title, "caption": caption, "hashtags": hashtags}
        except Exception:
            pass
        return self._fallback_content(webapp_data, platform)

    @staticmethod
    def _fallback_content(
        webapp_data: dict[str, Any],
        platform: str,
        error: str = "",
    ) -> dict[str, Any]:
        name = webapp_data.get("name", "our app")
        url = webapp_data.get("url", "")
        description = webapp_data.get("description", "")
        return {
            "title": f"Discover {name}",
            "caption": (
                f"🚀 {name} – {description[:120]}\n\n"
                f"Check it out: {url}\n\n"
                f"Designed and created by AmarktAI Marketing"
            ),
            "hashtags": ["AI", "Marketing", "Growth", "AmarktAINetwork"],
            "_generation_error": error,
        }
