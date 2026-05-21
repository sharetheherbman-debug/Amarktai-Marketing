from __future__ import annotations

import hashlib
import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.deps import effective_plan_name, is_admin_user
from app.core.config import settings
from app.models.content import Content as ContentModel, ContentStatus, ContentType
from app.models.marketing_runtime import MediaAsset, MediaJob, MediaJobStatus, SchedulerMode
from app.models.user import User
from app.models.webapp import WebApp
from app.services.ai_provider import AIProvider
from app.services.asset_query_builder import build_asset_query
from app.services.business_grounding import build_business_grounding_context, score_business_grounding
from app.services.business_intelligence import analyze_business
from app.services.campaign_angle_engine import CAMPAIGN_ANGLES, angle_for_regenerate, detect_duplicate_similarity, select_angle
from app.services.content_quality_gate import (
    build_ad_campaign_structure,
    build_image_creative_structure,
    build_short_video_structure,
    build_talking_avatar_structure,
    build_voiceover_structure,
    build_youtube_kit_structure,
    evaluate_quality_gate,
)
from app.services.creative_brief_builder import build_image_prompt, build_video_brief, score_creative_relevance
from app.services.genx_router_client import GenXRouterClient
from app.services.hashtag_strategy import build_hashtag_strategy, validate_hashtags
from app.services.media_service import VIDEO_PLATFORMS, get_media_url
from app.services.pixabay_client import PixabayClient
from app.services.platform_catalog import filter_launch_platforms, launch_platforms, normalize_platform
from app.services.provider_catalog import resolve_user_api_key
from app.services.provider_decision_engine import decide_provider
from app.services.scheduler_runtime import upsert_scheduler_item

_PREVIEW_STORE: dict[str, dict[str, Any]] = {}
_INTENT_FORMAT_MAP = {
    "quick_post": "text_post",
    "ad_campaign": "ad_campaign",
    "short_video": "short_video",
    "youtube_kit": "youtube_kit",
    "talking_avatar": "talking_avatar",
    "image_creative": "image_creative",
    "voiceover": "voiceover",
    "platform_pack": "platform_pack",
    "schedule_draft": "schedule_draft",
}
_FORMAT_INTENT_MAP = {
    "text_post": "quick_post",
    "ad_copy": "ad_campaign",
    "ad_campaign": "ad_campaign",
    "short_video_brief": "short_video",
    "video_script": "short_video",
    "youtube_video_kit": "youtube_kit",
    "youtube_kit": "youtube_kit",
    "talking_avatar_script": "talking_avatar",
    "talking_avatar_video": "talking_avatar",
    "image_prompt": "image_creative",
    "generated_image": "image_creative",
    "image_creative": "image_creative",
    "voiceover_script": "voiceover",
    "voiceover": "voiceover",
    "full_campaign_pack": "platform_pack",
    "platform_pack": "platform_pack",
    "schedule_draft": "schedule_draft",
}
_PREMIUM_MEDIA_INTENTS = {"short_video", "talking_avatar", "image_creative", "voiceover"}


@dataclass
class OrchestratorRequest:
    action: str
    webapp_id: str
    platform: str
    fmt: str = "text_post"
    objective: str | None = None
    tone: str | None = None
    audience: str | None = None
    offer: str | None = None
    product_focus: str | None = None
    budget_mode: str = "balanced"
    provider_mode: str = "auto"
    feedback: str | None = None
    variation_seed: str | None = None
    parent_content_id: str | None = None
    previous_angle: str | None = None
    scheduled_for: str | None = None


class ContentOrchestrator:
    def __init__(self, db: Session, user: User) -> None:
        self.db = db
        self.user = user

    async def preview(self, request: OrchestratorRequest) -> dict[str, Any]:
        payload = await self._execute(request=request, persist=False)
        preview_id = str(uuid.uuid4())
        _PREVIEW_STORE[preview_id] = {
            "user_id": self.user.id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        return {
            "status": "preview_ready",
            "preview_id": preview_id,
            "session_id": preview_id,
            "preview": payload,
        }

    async def save_preview(self, preview_id: str) -> ContentModel:
        stored = _PREVIEW_STORE.get(preview_id)
        if not stored or stored.get("user_id") != self.user.id:
            raise HTTPException(status_code=404, detail="Preview not found")
        payload = stored.get("payload") or {}
        payload["action"] = "save_preview"
        saved_content = self._persist_payload(payload)
        _PREVIEW_STORE.pop(preview_id, None)
        return saved_content

    async def generate(self, request: OrchestratorRequest) -> ContentModel:
        return (await self._execute(request=request, persist=True))["content"]

    async def generate_pack(self, request: OrchestratorRequest, *, platforms: list[str], formats: list[str] | None = None) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for platform in filter_launch_platforms(platforms) or launch_platforms():
            effective_formats = formats or [request.fmt]
            for fmt in effective_formats:
                generated = await self._execute(
                    request=OrchestratorRequest(
                        action=request.action,
                        webapp_id=request.webapp_id,
                        platform=platform,
                        fmt=fmt,
                        objective=request.objective,
                        tone=request.tone,
                        audience=request.audience,
                        offer=request.offer,
                        product_focus=request.product_focus,
                        budget_mode=request.budget_mode,
                        provider_mode=request.provider_mode,
                        feedback=request.feedback,
                        variation_seed=request.variation_seed,
                    ),
                    persist=True,
                )
                items.append(generated)
        return items

    async def improve(self, content: ContentModel, *, objective: str | None = None, tone: str | None = None, audience: str | None = None, offer: str | None = None, product_focus: str | None = None) -> ContentModel:
        request = OrchestratorRequest(
            action="improve",
            webapp_id=content.webapp_id,
            platform=content.platform,
            fmt=str((content.generation_metadata or {}).get("format") or "text_post"),
            objective=objective,
            tone=tone,
            audience=audience,
            offer=offer,
            product_focus=product_focus or offer,
            parent_content_id=content.id,
            previous_angle=str((content.generation_metadata or {}).get("campaign_angle") or "") or None,
        )
        return await self.generate(request)

    async def regenerate(self, content: ContentModel, *, feedback: str | None = None, variation_seed: str | None = None) -> ContentModel:
        request = OrchestratorRequest(
            action="regenerate",
            webapp_id=content.webapp_id,
            platform=content.platform,
            fmt=str((content.generation_metadata or {}).get("format") or "text_post"),
            feedback=feedback,
            variation_seed=variation_seed,
            parent_content_id=content.id,
            previous_angle=str((content.generation_metadata or {}).get("campaign_angle") or "") or None,
        )
        return await self.generate(request)

    async def schedule_existing_draft(self, content: ContentModel, *, scheduled_for: str | None = None) -> ContentModel:
        planned_at = datetime.now(timezone.utc) + timedelta(hours=1)
        if scheduled_for:
            planned_at = datetime.fromisoformat(scheduled_for.replace("Z", "+00:00"))
        item = upsert_scheduler_item(
            self.db,
            user_id=self.user.id,
            content=content,
            planned_at=planned_at,
            mode=SchedulerMode.MANUAL.value,
        )
        metadata = dict(content.generation_metadata or {})
        metadata["scheduler_item_id"] = item.id
        metadata["schedule_status"] = item.status
        metadata["source_action"] = "schedule_draft"
        content.generation_metadata = metadata
        self.db.commit()
        self.db.refresh(content)
        return content

    async def _execute(self, *, request: OrchestratorRequest, persist: bool) -> dict[str, Any]:
        context = await self._load_context(request)
        angle = self._select_angle_for_request(request, context)
        provider = self._decide_provider(request, context, angle)
        structured = await self._build_structured_output(request, context, angle, provider)
        structured = self._apply_hashtags(structured, context)
        validation = self._validate_output(structured, context)
        structured["validation"] = validation
        media = await self._build_media_result(request, context, provider, structured, persist=persist)
        payload = self._build_payload(request, context, angle, provider, structured, validation, media)
        if not persist:
            return payload
        content = self._persist_payload(payload)
        payload["content"] = content
        payload["content_id"] = content.id
        return payload

    async def _load_context(self, request: OrchestratorRequest) -> dict[str, Any]:
        platform = normalize_platform(request.platform)
        if platform not in launch_platforms():
            raise HTTPException(status_code=422, detail=f"Unsupported platform '{platform}'")
        webapp = self.db.query(WebApp).filter(WebApp.id == request.webapp_id, WebApp.user_id == self.user.id).first()
        if not webapp:
            raise HTTPException(status_code=404, detail="Web app not found")
        provider_keys = {
            "genx": bool(self._provider_key("GENX_API_KEY")),
            "qwen": bool(self._provider_key("QWEN_API_KEY")),
            "huggingface": bool(self._provider_key("HUGGINGFACE_TOKEN")),
            "pixabay": bool(self._provider_key("PIXABAY_API_KEY")),
            "firecrawl": bool(self._provider_key("FIRECRAWL_API_KEY")),
        }
        intelligence = webapp.scraped_data if isinstance(webapp.scraped_data, dict) else {}
        if not intelligence and webapp.url and provider_keys["firecrawl"]:
            try:
                intelligence = await analyze_business(
                    url=webapp.url,
                    name=webapp.name,
                    description=webapp.description,
                    firecrawl_api_key=self._provider_key("FIRECRAWL_API_KEY"),
                    timeout=25,
                )
                webapp.scraped_data = intelligence
                self.db.commit()
            except Exception:
                intelligence = {
                    "scrape_status": "failed",
                    "source_provider": "manual",
                    "warnings": ["Website analysis unavailable; using saved business profile."],
                }
        business = {
            "id": webapp.id,
            "name": webapp.name or "Business",
            "url": str(webapp.url or intelligence.get("normalized_url") or ""),
            "description": webapp.description or intelligence.get("page_summary") or "",
            "summary": intelligence.get("page_summary") or webapp.description or "",
            "category": webapp.category or "",
            "target_audience": request.audience or webapp.target_audience or intelligence.get("target_audience_guess") or "",
            "key_features": webapp.key_features or [],
            "products_services": intelligence.get("products_services") or webapp.key_features or [],
            "keywords": intelligence.get("keywords") or [],
            "market_location": webapp.market_location or "",
            "brand_voice": webapp.brand_voice or "",
            "offer": request.offer or request.product_focus or "",
            "current_offer": request.offer or request.product_focus or "",
            "objective": request.objective or "",
            "tone": request.tone or webapp.brand_voice or "",
        }
        if request.product_focus or request.offer:
            focus = request.product_focus or request.offer
            business["products_services"] = [focus, *list(business.get("products_services") or [])][:5]
        grounding = build_business_grounding_context(business)
        business["description"] = f"{grounding['prompt_prefix']} {business['description']}".strip()
        return {
            "platform": platform,
            "webapp": webapp,
            "business": business,
            "provider_keys": provider_keys,
            "intelligence": intelligence,
            "admin": {
                "is_admin": is_admin_user(self.user),
                "effective_plan": effective_plan_name(self.user),
                "unlimited_content_quota": is_admin_user(self.user),
                "unlimited_business_count": is_admin_user(self.user),
                "unrestricted_provider_access": is_admin_user(self.user),
                "billing_enabled": bool(settings.ENABLE_BILLING and not is_admin_user(self.user)),
            },
            "creative_brief": {
                "image": build_image_prompt(business, platform, objective=request.objective or "", campaign_topic=request.offer or request.product_focus or ""),
                "video": build_video_brief(business, platform, objective=request.objective or "", campaign_topic=request.offer or request.product_focus or ""),
            },
        }

    def _select_angle_for_request(self, request: OrchestratorRequest, context: dict[str, Any]) -> dict[str, Any]:
        if request.action == "regenerate":
            angle = angle_for_regenerate(
                request.previous_angle,
                objective=request.objective or context["business"].get("objective"),
                feedback=request.feedback,
            )
        else:
            angle = select_angle(
                objective=request.objective or context["business"].get("objective"),
                feedback=request.feedback,
            )
        seed = request.variation_seed or str(uuid.uuid4())
        angle_catalog = {item["id"]: item for item in CAMPAIGN_ANGLES}
        angle_rules = angle_catalog.get(angle["campaign_angle"], {})
        hook_styles = angle_rules.get("hook_styles") or [angle.get("hook_style") or "statement"]
        hook_index = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(hook_styles)
        angle["hook_style"] = hook_styles[hook_index]
        angle["variation_seed"] = seed
        return angle

    def _decide_provider(self, request: OrchestratorRequest, context: dict[str, Any], angle: dict[str, Any]) -> dict[str, Any]:
        capability = self._capability_for_intent(self._intent_for_format(request.fmt))
        model_mappings = {
            "text": settings.GENX_MODEL_COPY or settings.GENX_DEFAULT_MODEL,
            "image": settings.GENX_MODEL_IMAGE,
            "video": settings.GENX_MODEL_VIDEO,
            "voice": settings.GENX_MODEL_AUDIO,
            "avatar": settings.GENX_MODEL_AUDIO or settings.GENX_MODEL_VIDEO,
        }
        decision = decide_provider(
            intent=self._intent_for_format(request.fmt),
            capability=capability,
            platform=context["platform"],
            fmt=request.fmt,
            business=context["business"],
            budget_mode=request.budget_mode,
            provider_mode=request.provider_mode,
            provider_keys=context["provider_keys"],
            model_mappings=model_mappings,
            capability_availability={
                "genx": {
                    "text": bool(model_mappings["text"]),
                    "image": bool(model_mappings["image"]),
                    "video": bool(model_mappings["video"]),
                    "voice": bool(model_mappings["voice"]),
                    "avatar": bool(model_mappings["avatar"]),
                }
            },
        )
        decision["campaign_angle"] = angle["campaign_angle"]
        decision["hook_style"] = angle["hook_style"]
        return decision

    async def _build_structured_output(self, request: OrchestratorRequest, context: dict[str, Any], angle: dict[str, Any], provider: dict[str, Any]) -> dict[str, Any]:
        intent = self._intent_for_format(request.fmt)
        business = context["business"]
        audience = request.audience or business.get("target_audience") or "your ideal audience"
        offer = request.offer or request.product_focus or business.get("current_offer") or business.get("products_services", [""])[0] or "your offer"
        objective = request.objective or business.get("objective") or "awareness"
        tone = request.tone or business.get("tone") or "clear and grounded"
        provider_text = await self._generate_copy(
            business=business,
            intent=intent,
            objective=objective,
            offer=offer,
            audience=audience,
            tone=tone,
            angle=angle,
            provider=provider,
        )
        if intent == "quick_post":
            return self._quick_post_output(business, objective, offer, audience, angle, provider_text)
        if intent == "ad_campaign":
            return self._ad_campaign_output(business, context, objective, offer, audience, angle, provider_text)
        if intent == "short_video":
            return self._short_video_output(business, context, offer, angle, provider_text)
        if intent == "youtube_kit":
            return self._youtube_output(business, offer, objective, angle, provider_text)
        if intent == "talking_avatar":
            return self._talking_avatar_output(business, offer, audience, angle, provider_text)
        if intent == "image_creative":
            return self._image_creative_output(business, context, offer, angle, provider_text)
        if intent == "voiceover":
            return self._voiceover_output(business, offer, angle, provider_text)
        return self._quick_post_output(business, objective, offer, audience, angle, provider_text)

    async def _generate_copy(self, *, business: dict[str, Any], intent: str, objective: str, offer: str, audience: str, tone: str, angle: dict[str, Any], provider: dict[str, Any]) -> dict[str, Any]:
        capability = provider.get("capability") or "text"
        prompt = (
            f"Business: {business.get('name')} ({business.get('category')}). Audience: {audience}. "
            f"Objective: {objective}. Offer: {offer}. Tone: {tone}. "
            f"Campaign angle: {angle['campaign_angle_label']} ({angle['campaign_angle_description']}). "
            f"Hook style: {angle['hook_style']}. Intent: {intent}. "
            "Write grounded marketing copy with no Amarktai references unless the business is Amarktai. "
            "Return concise plain text paragraphs only."
        )
        ai = AIProvider.from_keys(
            genx_key=self._provider_key("GENX_API_KEY"),
            qwen_key=self._provider_key("QWEN_API_KEY"),
            hf_token=self._provider_key("HUGGINGFACE_TOKEN"),
            openai_key=self._provider_key("OPENAI_API_KEY"),
        )
        if provider.get("selected_provider") == "genx" and provider.get("status") == "model_mapping_required":
            return {"text": "", "provider": "genx", "model": "", "status": "model_mapping_required"}
        raw = await ai._generate_raw(prompt, max_tokens=450)
        return {
            "text": str(raw.get("text") or "").strip(),
            "provider": raw.get("provider") or provider.get("selected_provider") or "template",
            "model": raw.get("model") or provider.get("selected_model_or_task") or "template",
            "status": provider.get("status") or ("success" if raw.get("text") else "template_fallback"),
        }

    def _quick_post_output(self, business: dict[str, Any], objective: str, offer: str, audience: str, angle: dict[str, Any], provider_text: dict[str, Any]) -> dict[str, Any]:
        body = provider_text["text"] or (
            f"{business['name']} helps {audience} with {offer}. "
            f"This {angle['campaign_angle_label'].lower()} angle highlights why it matters now and what to do next."
        )
        first_line = body.split("\n", 1)[0][:120]
        return {
            "intent": "quick_post",
            "format": "text_post",
            "title": f"{business['name']} · {objective.title()} post",
            "caption": body,
            "hooks": [first_line],
            "cta": self._cta_for_objective(objective),
            "provider_actual": provider_text["provider"],
            "model_actual": provider_text["model"],
        }

    def _ad_campaign_output(self, business: dict[str, Any], context: dict[str, Any], objective: str, offer: str, audience: str, angle: dict[str, Any], provider_text: dict[str, Any]) -> dict[str, Any]:
        base = build_ad_campaign_structure(
            business=business,
            objective=objective,
            offer=offer,
            audience=audience,
            platform=context["platform"],
            has_media_provider=provider_text["provider"] != "template",
        )
        base.update(
            {
                "format": "ad_campaign",
                "headline": f"{offer} for {audience}"[:120],
                "primary_text": provider_text["text"] or f"{business['name']} helps {audience} turn {objective} into action with {offer}.",
                "hooks": [
                    f"Why {audience} choose {business['name']} for {offer}",
                    f"The {angle['campaign_angle_label'].lower()} hook that makes {offer} feel timely",
                    f"A clear CTA to move {audience} from interest to action",
                ],
                "creative_brief": context["creative_brief"]["image"]["image_prompt"],
                "placements": [base.get("placement_suggestion")],
                "asset_recommendation": base.get("asset_recommendation"),
                "schedule_suggestion": base.get("schedule_suggestion"),
                "cta": self._cta_for_objective(objective),
            }
        )
        return base

    def _short_video_output(self, business: dict[str, Any], context: dict[str, Any], offer: str, angle: dict[str, Any], provider_text: dict[str, Any]) -> dict[str, Any]:
        base = build_short_video_structure(
            business=business,
            offer=offer,
            platform=context["platform"],
            has_media_provider=provider_text["provider"] == "genx",
        )
        voiceover = provider_text["text"] or f"Here is how {business['name']} helps with {offer} using a {angle['campaign_angle_label'].lower()} story arc."
        scenes = []
        for idx, scene in enumerate(base["scene_by_scene_script"], start=1):
            scenes.append({
                "scene": idx,
                "duration_sec": scene["duration_sec"],
                "action": scene["action"],
                "caption": f"{business['name']} · {scene['action']}"[:120],
            })
        return {
            **base,
            "format": "short_video",
            "first_3_second_hook": f"{business['name']}: {offer} without the usual friction.",
            "scene_by_scene_script": scenes,
            "on_screen_captions": [entry["caption"] for entry in scenes],
            "voiceover": voiceover,
            "music_sound_suggestion": "Use an upbeat licensed track that stays under dialogue.",
            "asset_render_plan": context["creative_brief"]["video"],
            "thumbnail_idea": f"Show the before/after result of {offer} with a bold CTA for {business['name']}",
            "duration": "25 seconds",
        }

    def _youtube_output(self, business: dict[str, Any], offer: str, objective: str, angle: dict[str, Any], provider_text: dict[str, Any]) -> dict[str, Any]:
        base = build_youtube_kit_structure(business=business, offer=offer, objective=objective)
        script = provider_text["text"] or f"Explain how {business['name']} approaches {offer} using the {angle['campaign_angle_label'].lower()} angle."
        return {
            **base,
            "format": "youtube_kit",
            "description": script[:500],
            "outline": base["outline"],
            "outline_script": script,
            "chapters": ["00:00 Hook", "00:30 Problem", "02:00 Solution", "04:00 Proof", "05:30 CTA"],
            "tags_keywords": [str(tag) for tag in base["tags_keywords"] if tag],
            "shorts_cutdown": base["shorts_cutdown_idea"],
        }

    def _talking_avatar_output(self, business: dict[str, Any], offer: str, audience: str, angle: dict[str, Any], provider_text: dict[str, Any]) -> dict[str, Any]:
        base = build_talking_avatar_structure(
            business=business,
            offer=offer,
            audience=audience,
            has_avatar_provider=provider_text["provider"] == "genx",
        )
        return {
            **base,
            "format": "talking_avatar",
            "script": provider_text["text"] or base["script"],
            "background_brief": base["background_visual_brief"],
            "captions": [line.strip() for line in (provider_text["text"] or base["script"]).split(".") if line.strip()],
        }

    def _image_creative_output(self, business: dict[str, Any], context: dict[str, Any], offer: str, angle: dict[str, Any], provider_text: dict[str, Any]) -> dict[str, Any]:
        base = build_image_creative_structure(
            business=business,
            offer=offer,
            platform=context["platform"],
            has_image_provider=provider_text["provider"] == "genx",
        )
        return {
            **base,
            "format": "image_creative",
            "creative_brief": context["creative_brief"]["image"]["image_prompt"],
            "stock_asset_suggestions": base["pixabay_suggestions"],
            "copy_overlay": f"{business['name']} · {offer}"[:120],
            "cta_overlay": self._cta_for_objective(business.get("objective") or "sales"),
            "aspect_ratio": context["creative_brief"]["image"]["aspect_ratio"],
        }

    def _voiceover_output(self, business: dict[str, Any], offer: str, angle: dict[str, Any], provider_text: dict[str, Any]) -> dict[str, Any]:
        base = build_voiceover_structure(
            business=business,
            offer=offer,
            has_tts_provider=provider_text["provider"] == "genx",
        )
        return {
            **base,
            "format": "voiceover",
            "voice_script": provider_text["text"] or base["script"],
            "delivery_notes": f"{base['delivery_notes']} Use a {angle['hook_style'].replace('_', ' ')} opening cadence.",
        }

    def _apply_hashtags(self, structured: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        strategy = build_hashtag_strategy(
            context["business"],
            context["platform"],
            extra_tokens=[context["business"].get("current_offer") or "", context["business"].get("category") or ""],
        )
        raw = structured.get("hashtags") if isinstance(structured.get("hashtags"), list) else strategy["hashtags"]
        validated = validate_hashtags(list(raw or strategy["hashtags"]), context["business"])
        structured["hashtags"] = validated["hashtags"] or strategy["hashtags"]
        structured["hashtag_strategy"] = strategy
        structured["hashtag_validation"] = validated
        return structured

    def _validate_output(self, structured: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        content_text = " ".join(
            str(structured.get(key) or "")
            for key in ("caption", "primary_text", "voice_script", "script", "outline_script", "creative_brief")
        ).strip()
        grounding = score_business_grounding(content_text, context["business"])
        creative = score_creative_relevance(
            content_text,
            str(structured.get("creative_brief") or context["creative_brief"]["image"]["image_prompt"]),
            context["business"],
        )
        quality_gate = evaluate_quality_gate(
            business_grounding_score=int(grounding["business_grounding_score"]),
            hashtag_relevance_score=int(structured["hashtag_strategy"]["hashtag_relevance_score"]),
            creative_relevance_score=int(creative["creative_relevance_score"]),
        )
        return {
            "grounding": grounding,
            "creative": creative,
            "quality_gate": quality_gate,
        }

    async def _build_media_result(self, request: OrchestratorRequest, context: dict[str, Any], provider: dict[str, Any], structured: dict[str, Any], *, persist: bool) -> dict[str, Any]:
        intent = self._intent_for_format(request.fmt)
        content_id = None
        media_urls: list[str] = []
        media_assets: list[dict[str, Any]] = []
        media_job_ids: list[str] = []
        media_asset_ids: list[str] = []
        media_state = str(provider.get("media_state") or "not_rendered")
        user_message = str(provider.get("user_message") or "")
        status = str(provider.get("status") or "configured")
        capability = str(provider.get("capability") or "text")
        if intent not in _PREMIUM_MEDIA_INTENTS:
            return {
                "media_state": "not_rendered",
                "media_urls": [],
                "media_assets": [],
                "media_job_ids": [],
                "media_asset_ids": [],
                "readiness": "script-only",
                "status": status,
                "user_message": user_message,
            }
        if provider.get("selected_provider") == "pixabay":
            media_assets = await self._search_pixabay_assets(context, capability)
            media_state = "asset_search_result" if media_assets else "unavailable"
            user_message = user_message or ("Real stock assets found." if media_assets else "No real stock assets available.")
        elif provider.get("selected_provider") == "genx" and provider.get("can_generate_asset"):
            if status == "model_mapping_required":
                media_state = "not_rendered"
                user_message = user_message or "GenX model mapping is required before live media can be rendered."
            elif status == "capability_unavailable":
                media_state = "unavailable"
                user_message = user_message or "GenX is configured but this media capability is unavailable."
            elif persist:
                job = await self._create_genx_job(context, provider, structured, capability)
                media_job_ids = [job.id]
                if job.result_url:
                    media_urls = [job.result_url]
                    media_state = "generated"
                else:
                    media_state = "not_rendered"
                    user_message = user_message or "GenX job queued; media is not rendered yet."
        else:
            if capability == "image" and self._provider_key("HUGGINGFACE_TOKEN"):
                media_urls = await get_media_url(context["platform"], context["business"], self._provider_key("HUGGINGFACE_TOKEN"), context["creative_brief"]["image"]["image_prompt"])
                media_state = "generated" if media_urls else "not_rendered"
            else:
                media_state = "script_only" if intent in {"talking_avatar", "voiceover", "short_video"} else "unavailable"
        if media_assets and persist:
            for asset in media_assets:
                row = MediaAsset(
                    id=str(uuid.uuid4()),
                    user_id=self.user.id,
                    business_id=context["webapp"].id,
                    content_id=content_id,
                    provider=str(asset.get("provider") or "pixabay"),
                    model=str(asset.get("model") or "stock"),
                    asset_type=str(asset.get("asset_type") or capability),
                    title=str(asset.get("title") or asset.get("provider") or "Asset"),
                    url=str(asset.get("media_url") or asset.get("source_url") or asset.get("url") or ""),
                    preview_url=str(asset.get("preview_url") or asset.get("thumbnail_url") or ""),
                    prompt=str(asset.get("query") or ""),
                    metadata_json=asset,
                )
                self.db.add(row)
                self.db.flush()
                media_asset_ids.append(row.id)
        readiness = "GenX ready" if provider.get("selected_provider") == "genx" and status == "configured" else (
            "mapping required" if status == "model_mapping_required" else "script-only"
        )
        return {
            "media_state": media_state,
            "media_urls": media_urls,
            "media_assets": media_assets,
            "media_job_ids": media_job_ids,
            "media_asset_ids": media_asset_ids,
            "readiness": readiness,
            "status": status,
            "user_message": user_message,
        }

    async def _create_genx_job(self, context: dict[str, Any], provider: dict[str, Any], structured: dict[str, Any], capability: str) -> MediaJob:
        client = GenXRouterClient(api_key=self._provider_key("GENX_API_KEY"), base_url=settings.GENX_BASE_URL.replace("/v1", ""))
        prompt = str(structured.get("creative_brief") or structured.get("voice_script") or structured.get("script") or structured.get("primary_text") or structured.get("caption") or "")
        job = MediaJob(
            id=str(uuid.uuid4()),
            user_id=self.user.id,
            business_id=context["webapp"].id,
            content_id=None,
            provider="genx",
            model=str(provider.get("selected_model_or_task") or ""),
            task=capability,
            status=MediaJobStatus.QUEUED.value,
            prompt=prompt,
            metadata_json={"platform": context["platform"], "capability": capability},
        )
        self.db.add(job)
        self.db.flush()
        if not client.configured:
            job.status = MediaJobStatus.PROMPT_ONLY.value
            job.error_message = "GenX not configured"
            return job
        try:
            response = await client.create_generation_job(
                model=str(provider.get("selected_model_or_task") or ""),
                params={"prompt": prompt, "capability": capability},
                metadata={"platform": context["platform"], "business_id": context["webapp"].id},
            )
            data = response.get("data") if isinstance(response.get("data"), dict) else {}
            job.external_job_id = str(data.get("job_id") or data.get("id") or "") or None
            job.result_url = str(data.get("result_url") or data.get("output_url") or data.get("url") or "") or None
            if job.result_url:
                job.status = MediaJobStatus.COMPLETED.value
            else:
                job.status = MediaJobStatus.RUNNING.value if response.get("ok") else MediaJobStatus.PROMPT_ONLY.value
            job.error_message = None if response.get("ok") else str(response.get("error") or "GenX generation unavailable")
        except Exception as exc:
            job.status = MediaJobStatus.PROMPT_ONLY.value
            job.error_message = str(exc)
        return job

    async def _search_pixabay_assets(self, context: dict[str, Any], capability: str) -> list[dict[str, Any]]:
        key = self._provider_key("PIXABAY_API_KEY")
        if not key:
            return []
        client = PixabayClient(api_key=key)
        query = build_asset_query(
            business_name=context["business"]["name"],
            category=context["business"].get("category") or "business",
            products_services=context["business"].get("products_services") or [],
            audience=context["business"].get("target_audience") or "",
            platform=context["platform"],
        )
        if capability == "video":
            response = await client.search_videos(q=query, category=context["business"].get("category") or "business", per_page=3)
            items = response.get("items") if isinstance(response.get("items"), list) else []
            return [self._normalize_asset(item, provider="pixabay", capability="video", query=query) for item in items[:3]]
        response = await client.search_images(q=query, category=context["business"].get("category") or "business", per_page=3)
        items = response.get("items") if isinstance(response.get("items"), list) else []
        return [self._normalize_asset(item, provider="pixabay", capability="image", query=query) for item in items[:3]]

    def _normalize_asset(self, item: dict[str, Any], *, provider: str, capability: str, query: str) -> dict[str, Any]:
        preview_url = str(item.get("previewURL") or item.get("preview_url") or item.get("webformatURL") or "")
        media_url = str(
            item.get("largeImageURL")
            or item.get("fullHDURL")
            or ((item.get("videos") or {}).get("medium") or {}).get("url")
            or item.get("url")
            or preview_url
        )
        return {
            "provider": provider,
            "asset_type": capability,
            "title": str(item.get("tags") or item.get("id") or "Stock asset"),
            "source_url": str(item.get("pageURL") or item.get("source_url") or media_url),
            "author": str(item.get("user") or item.get("author") or "Pixabay contributor"),
            "license_note": "Pixabay License",
            "attribution": f"Source: Pixabay · {item.get('user') or 'contributor'}",
            "preview_url": preview_url,
            "media_url": media_url,
            "relevance_score": 0.82,
            "query": query,
        }

    def _build_payload(self, request: OrchestratorRequest, context: dict[str, Any], angle: dict[str, Any], provider: dict[str, Any], structured: dict[str, Any], validation: dict[str, Any], media: dict[str, Any]) -> dict[str, Any]:
        caption = str(structured.get("caption") or structured.get("primary_text") or structured.get("voice_script") or structured.get("script") or structured.get("outline_script") or structured.get("creative_brief") or "")
        recent_rows = (
            self.db.query(ContentModel)
            .filter(ContentModel.user_id == self.user.id, ContentModel.webapp_id == context["webapp"].id, ContentModel.platform == context["platform"])
            .order_by(ContentModel.created_at.desc())
            .limit(6)
            .all()
        )
        previous_text = max((str(row.caption or "") for row in recent_rows), key=len, default="")
        duplicate = detect_duplicate_similarity(caption, previous_text, threshold=0.9)
        if request.action == "regenerate" and duplicate["is_duplicate"]:
            retry_angle = angle_for_regenerate(angle["campaign_angle"], objective=request.objective or context["business"].get("objective"), feedback=request.feedback)
            retry_angle["variation_seed"] = angle["variation_seed"]
            angle = retry_angle
            structured["hooks"] = [f"{context['business']['name']} · {retry_angle['hook_style'].replace('_', ' ')} hook"]
            caption = f"{caption}\n\nNew variation: {retry_angle['campaign_angle_label']}"
            duplicate = detect_duplicate_similarity(caption, previous_text, threshold=0.9)
        return {
            "action": request.action,
            "webapp_id": context["webapp"].id,
            "platform": context["platform"],
            "format": request.fmt,
            "intent": self._intent_for_format(request.fmt),
            "objective": request.objective,
            "tone": request.tone,
            "audience": request.audience,
            "offer": request.offer,
            "product_focus": request.product_focus,
            "feedback": request.feedback,
            "variation_seed": angle["variation_seed"],
            "previous_angle": request.previous_angle,
            "parent_content_id": request.parent_content_id,
            "title": str(structured.get("title") or f"{context['business']['name']} · {self._intent_for_format(request.fmt).replace('_', ' ')}"),
            "caption": caption,
            "hashtags": structured.get("hashtags") or [],
            "structured_output": structured,
            "provider_attempted": provider.get("provider_attempt_order", [provider.get("selected_provider")])[0],
            "provider_actual": provider.get("selected_provider"),
            "model_actual": provider.get("selected_model_or_task"),
            "fallback_chain": provider.get("fallback_chain") or [],
            "reason": provider.get("reason"),
            "user_message": provider.get("user_message"),
            "campaign_angle": angle["campaign_angle"],
            "campaign_angle_label": angle["campaign_angle_label"],
            "hook_style": angle["hook_style"],
            "why_this_version": angle["why_this_version"],
            "duplicate_similarity": duplicate["similarity_score"],
            "needs_review_duplicate": duplicate["is_duplicate"],
            "quality_gate": validation["quality_gate"],
            "grounding": validation["grounding"],
            "creative": validation["creative"],
            "media": media,
            "admin": context["admin"],
            "business_snapshot": context["business"],
            "scrape_snapshot": context["intelligence"],
        }

    def _persist_payload(self, payload: dict[str, Any]) -> ContentModel:
        media = payload["media"]
        content = ContentModel(
            id=str(uuid.uuid4()),
            user_id=self.user.id,
            webapp_id=payload["webapp_id"],
            platform=payload["platform"],
            type=self._content_type_for_format(payload["format"]),
            status=ContentStatus.PENDING,
            title=payload["title"],
            caption=payload["caption"],
            hashtags=payload["hashtags"],
            media_urls=media["media_urls"],
            parent_content_id=payload.get("parent_content_id"),
            generation_metadata={
                "format": payload["format"],
                "intent": payload["intent"],
                "source_route": "/content/orchestrator",
                "source_action": payload.get("action") or "generate",
                "provider_attempted": payload["provider_attempted"],
                "provider_actual": payload["provider_actual"],
                "model_actual": payload["model_actual"],
                "fallback_chain": payload["fallback_chain"],
                "reason": payload["reason"],
                "user_message": payload["user_message"],
                "campaign_angle": payload["campaign_angle"],
                "campaign_angle_label": payload["campaign_angle_label"],
                "hook_style": payload["hook_style"],
                "variation_seed": payload["variation_seed"],
                "duplicate_similarity": payload["duplicate_similarity"],
                "needs_review_duplicate": payload["needs_review_duplicate"],
                "quality_gate": payload["quality_gate"]["status"],
                "quality_gate_issues": payload["quality_gate"]["issues"],
                "business_grounding_score": payload["grounding"]["business_grounding_score"],
                "hashtag_relevance_score": payload["structured_output"]["hashtag_strategy"]["hashtag_relevance_score"],
                "creative_relevance_score": payload["creative"]["creative_relevance_score"],
                "source_business_snapshot": payload["business_snapshot"],
                "scrape_snapshot": payload["scrape_snapshot"],
                "preview_title": payload["title"],
                "preview_summary": payload["caption"][:220],
                "hooks": payload["structured_output"].get("hooks") or [],
                "cta": payload["structured_output"].get("cta"),
                "media_state": media["media_state"],
                "media_job_ids": media["media_job_ids"],
                "media_asset_ids": media["media_asset_ids"],
                "generated_media_readiness": media["readiness"],
                "generated_media_status": media["status"],
                "structured_output": payload["structured_output"],
                "admin": payload["admin"],
            },
        )
        self.db.add(content)
        self.db.flush()
        if media["media_job_ids"]:
            self.db.query(MediaJob).filter(MediaJob.id.in_(media["media_job_ids"])).update({"content_id": content.id}, synchronize_session=False)
        if media["media_asset_ids"]:
            self.db.query(MediaAsset).filter(MediaAsset.id.in_(media["media_asset_ids"])).update({"content_id": content.id}, synchronize_session=False)
        self.db.commit()
        self.db.refresh(content)
        return content

    def _intent_for_format(self, fmt: str) -> str:
        return _FORMAT_INTENT_MAP.get(fmt, fmt if fmt in _INTENT_FORMAT_MAP else "quick_post")

    def _capability_for_intent(self, intent: str) -> str:
        return {
            "quick_post": "text",
            "ad_campaign": "premium_creative",
            "short_video": "video",
            "youtube_kit": "premium_creative",
            "talking_avatar": "avatar",
            "image_creative": "image",
            "voiceover": "voice",
            "platform_pack": "premium_creative",
            "schedule_draft": "text",
        }.get(intent, "text")

    def _content_type_for_format(self, fmt: str) -> ContentType:
        intent = self._intent_for_format(fmt)
        if intent in {"short_video", "talking_avatar"}:
            return ContentType.VIDEO
        if intent == "image_creative":
            return ContentType.IMAGE
        return ContentType.TEXT

    def _provider_key(self, key_name: str) -> str:
        env_value = getattr(settings, key_name, "")
        return resolve_user_api_key(self.db, self.user.id, key_name, env_value) or ""

    def _cta_for_objective(self, objective: str) -> str:
        mapping = {
            "awareness": "Learn More",
            "leads": "Get Free Consultation",
            "bookings": "Book Now",
            "sales": "Shop Now",
            "launch": "Join the Waitlist",
            "retargeting": "See What You Missed",
            "engagement": "Join the Conversation",
        }
        return mapping.get((objective or "").lower(), "Get Started")


def get_preview_payload(preview_id: str) -> dict[str, Any] | None:
    stored = _PREVIEW_STORE.get(preview_id)
    if not stored:
        return None
    return stored.get("payload") if isinstance(stored.get("payload"), dict) else None
