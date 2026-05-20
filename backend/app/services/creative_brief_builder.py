"""
Creative Brief Builder — Phase 4

Builds structured, business-specific media prompts for every content format.
Every prompt is grounded to the selected business and its industry.

The builder selects industry-appropriate subject, setting, and style so that
generated imagery/video is directly relevant to the business being marketed.

Rules:
- Every prompt must include the business name, industry, and products/services.
- Prompts must NOT produce generic, fantasy, or unrelated imagery.
- Banned generic themes (castles, random fields, rain) unless justified by
  the campaign or business context.
- Platform aspect ratio guidance is always included.

Designed and created by AmarktAI Marketing
"""

from __future__ import annotations

from typing import Any


# Industry-specific visual rules
_INDUSTRY_VISUALS: dict[str, dict[str, Any]] = {
    "equine": {
        "subject_keywords": ["horse", "rider", "stable", "tack", "arena", "pasture", "equine care", "show jumping", "dressage"],
        "setting_keywords": ["stable yard", "equestrian centre", "outdoor arena", "paddock", "horsebox", "show ground"],
        "style": "natural outdoor photography, golden hour light, action or portrait",
        "avoid": ["random rain", "dark storm", "castles", "fantasy landscapes", "unrelated animals"],
        "tone": "lifestyle, aspirational, performance-focused",
    },
    "horse": {
        "subject_keywords": ["horse", "rider", "stable", "tack", "arena", "pasture", "equine care"],
        "setting_keywords": ["stable yard", "equestrian centre", "outdoor arena", "paddock"],
        "style": "natural outdoor photography, golden hour light",
        "avoid": ["random rain", "dark storm", "castles", "fantasy landscapes"],
        "tone": "lifestyle, aspirational",
    },
    "cyber security": {
        "subject_keywords": ["secure network", "SOC dashboard", "business team", "data lock", "threat map", "firewall", "analyst"],
        "setting_keywords": ["professional office", "tech command centre", "laptop with security UI", "data centre"],
        "style": "clean professional tech photography or vector illustration, blue/dark tones",
        "avoid": ["castles", "random fields", "fantasy landscapes", "medieval imagery", "swords"],
        "tone": "authoritative, professional, trustworthy",
    },
    "cybersecurity": {
        "subject_keywords": ["secure network", "SOC dashboard", "business team", "data lock", "threat map"],
        "setting_keywords": ["professional office", "tech command centre", "data centre"],
        "style": "clean professional tech photography, blue/dark tones",
        "avoid": ["castles", "random fields", "fantasy landscapes", "medieval imagery"],
        "tone": "authoritative, professional",
    },
    "technology": {
        "subject_keywords": ["software product", "developer", "tech professional", "interface", "device", "innovation"],
        "setting_keywords": ["modern office", "co-working space", "tech hub", "laptop setup"],
        "style": "modern clean photography or illustration",
        "avoid": ["fantasy imagery", "unrelated nature scenes"],
        "tone": "innovative, forward-thinking",
    },
    "fitness": {
        "subject_keywords": ["person exercising", "gym equipment", "outdoor workout", "trainer", "healthy lifestyle"],
        "setting_keywords": ["gym", "outdoor park", "sports facility", "studio"],
        "style": "high energy action photography",
        "avoid": ["sedentary scenes", "fast food"],
        "tone": "energetic, motivational",
    },
    "food": {
        "subject_keywords": ["food close-up", "plating", "chef", "fresh ingredients", "restaurant ambiance"],
        "setting_keywords": ["restaurant kitchen", "dining table", "market", "food studio"],
        "style": "appetising food photography, warm natural light",
        "avoid": ["industrial machinery", "generic stock office"],
        "tone": "inviting, warm, sensory",
    },
    "beauty": {
        "subject_keywords": ["beauty product", "model", "skincare routine", "makeup look", "before/after"],
        "setting_keywords": ["beauty studio", "bright clean background", "vanity setup"],
        "style": "polished beauty photography, pastel or luxury tones",
        "avoid": ["heavy industrial imagery", "dark moody unrelated themes"],
        "tone": "aspirational, clean, premium",
    },
    "real estate": {
        "subject_keywords": ["property exterior", "interior design", "sold sign", "agent with client", "neighbourhood"],
        "setting_keywords": ["house", "apartment", "commercial property", "neighbourhood street"],
        "style": "architectural or lifestyle photography",
        "avoid": ["abstract random imagery"],
        "tone": "professional, aspirational, trustworthy",
    },
    "finance": {
        "subject_keywords": ["advisor meeting", "financial charts", "professional team", "planning session"],
        "setting_keywords": ["professional office", "boardroom", "bank"],
        "style": "clean professional photography",
        "avoid": ["cartoons", "random outdoor scenes"],
        "tone": "trustworthy, authoritative, professional",
    },
    "default": {
        "subject_keywords": ["business team", "product", "service in action", "customer satisfaction"],
        "setting_keywords": ["professional environment", "branded context"],
        "style": "clean professional photography",
        "avoid": ["generic stock imagery that does not match the business"],
        "tone": "professional, authentic",
    },
}

# Platform aspect ratio guidance
_PLATFORM_ASPECT: dict[str, str] = {
    "instagram": "square 1:1 or portrait 4:5 for feed; 9:16 vertical for Stories/Reels",
    "tiktok": "9:16 vertical full-screen",
    "youtube": "16:9 horizontal",
    "pinterest": "2:3 or 1:2 tall portrait",
    "linkedin": "1.91:1 landscape or square 1:1",
    "facebook": "1.91:1 landscape or square 1:1",
    "twitter": "16:9 landscape or 1:1 square",
    "reddit": "16:9 or 1:1",
    "default": "1:1 square or 16:9 landscape",
}


def _get_industry_rules(category: str) -> dict[str, Any]:
    """Return industry-specific visual rules for a business category."""
    cat_lower = (category or "").lower()
    for key, rules in _INDUSTRY_VISUALS.items():
        if key in cat_lower:
            return rules
    return _INDUSTRY_VISUALS["default"]


def build_image_prompt(
    business: dict[str, Any],
    platform: str,
    objective: str = "",
    campaign_topic: str = "",
) -> dict[str, Any]:
    """
    Build a business-specific image prompt for AI image generation.

    Returns:
        {
            "image_prompt": str,
            "negative_prompt": str,
            "aspect_ratio": str,
            "industry_rules_applied": dict,
        }
    """
    name = business.get("name", "the business")
    category = business.get("category", "")
    description = business.get("description", "")
    products = business.get("products_services") or business.get("key_features") or []
    if isinstance(products, list):
        products_str = ", ".join(str(p) for p in products[:3])
    else:
        products_str = str(products or "")
    audience = business.get("target_audience", "")
    market = business.get("market_location", "")

    rules = _get_industry_rules(category)
    subjects = ", ".join(rules["subject_keywords"][:4])
    settings = ", ".join(rules["setting_keywords"][:3])
    style = rules["style"]
    tone = rules["tone"]
    avoid = ", ".join(rules["avoid"])
    aspect_ratio = _PLATFORM_ASPECT.get(platform.lower(), _PLATFORM_ASPECT["default"])

    campaign_line = f" Campaign focus: {campaign_topic}." if campaign_topic else ""
    objective_line = f" Objective: {objective}." if objective else ""
    products_line = f" Products/services shown: {products_str}." if products_str else ""
    audience_line = f" Target audience: {audience}." if audience else ""
    market_line = f" Market/location: {market}." if market else ""

    image_prompt = (
        f"Professional {platform} image for {name} ({category or 'business'}). "
        f"Subject: {subjects}, in a {settings} setting. "
        f"Style: {style}. Tone: {tone}. "
        f"{products_line}{audience_line}{market_line}{campaign_line}{objective_line}"
        f"The image must immediately communicate what {name} does. "
        f"Platform: {platform}, aspect ratio: {aspect_ratio}."
    )

    negative_prompt = (
        f"Avoid: {avoid}. "
        f"Do not show: Amarktai branding (unless {name} is Amarktai), "
        f"generic stock office workers, unrelated industry imagery, "
        f"fantasy elements, low quality, blurry, watermark."
    )

    return {
        "image_prompt": image_prompt,
        "negative_prompt": negative_prompt,
        "aspect_ratio": aspect_ratio,
        "industry_rules_applied": rules,
        "business_name": name,
        "category": category,
        "platform": platform,
    }


def build_video_brief(
    business: dict[str, Any],
    platform: str,
    objective: str = "",
    campaign_topic: str = "",
) -> dict[str, Any]:
    """
    Build a business-specific video script brief.

    Returns:
        {
            "video_brief_prompt": str,
            "shot_list_guidance": list[str],
            "aspect_ratio": str,
        }
    """
    name = business.get("name", "the business")
    category = business.get("category", "")
    description = business.get("description", "")
    products = business.get("products_services") or business.get("key_features") or []
    if isinstance(products, list):
        products_str = ", ".join(str(p) for p in products[:3])
    else:
        products_str = str(products or "")
    audience = business.get("target_audience", "")

    rules = _get_industry_rules(category)
    subjects = ", ".join(rules["subject_keywords"][:3])
    style = rules["style"]
    aspect_ratio = _PLATFORM_ASPECT.get(platform.lower(), _PLATFORM_ASPECT["default"])
    campaign_line = f" Campaign: {campaign_topic}." if campaign_topic else ""
    objective_line = f" Objective: {objective}." if objective else ""

    video_prompt = (
        f"Write a {platform} video script for {name} ({category or 'business'}). "
        f"Description: {description}. Products/services: {products_str}. "
        f"Target audience: {audience}.{campaign_line}{objective_line} "
        f"Visual style: {style}. Featured subjects: {subjects}. "
        f"Structure: hook (2 sec), problem/opportunity (5 sec), "
        f"{name} solution (10 sec), proof/example (8 sec), CTA (5 sec). "
        f"Platform: {platform}, aspect ratio: {aspect_ratio}. "
        f"Keep content 100% specific to {name}. Do not mention Amarktai."
    )

    shot_list = [
        f"Shot 1 — Hook: {subjects.split(',')[0].strip()} in action, eye-catching",
        f"Shot 2 — Problem: Relatable challenge for {audience or 'the audience'}",
        f"Shot 3 — Solution: {name} product/service solving the problem",
        f"Shot 4 — Proof: Customer result or product demonstration",
        f"Shot 5 — CTA: Brand logo + clear call to action text",
    ]

    return {
        "video_brief_prompt": video_prompt,
        "shot_list_guidance": shot_list,
        "aspect_ratio": aspect_ratio,
        "business_name": name,
        "category": category,
        "platform": platform,
    }


def score_creative_relevance(
    content_text: str,
    image_prompt: str,
    business: dict[str, Any],
) -> dict[str, Any]:
    """
    Score how relevant the generated content/prompt is to the business.
    Returns a score 0-100 and a list of issues.

    This is a heuristic check — real AI scoring requires a provider call.
    """
    name = (business.get("name") or "").lower()
    category = (business.get("category") or "").lower()
    products = business.get("products_services") or business.get("key_features") or []
    if isinstance(products, list):
        products_lower = [str(p).lower() for p in products]
    else:
        products_lower = [str(products).lower()]

    text_lower = (content_text or "").lower()
    prompt_lower = (image_prompt or "").lower()
    combined = text_lower + " " + prompt_lower

    score = 50  # baseline
    issues = []

    # Business name appears in content
    if name and name in combined:
        score += 15
    else:
        issues.append(f"Business name '{business.get('name', 'unknown')}' not found in content")

    # Category keywords appear
    if category:
        cat_words = category.split()
        if any(w in combined for w in cat_words if len(w) > 3):
            score += 15
        else:
            issues.append(f"Category '{category}' keywords missing from content")

    # Products/services mentioned
    if products_lower:
        found = any(p in combined for p in products_lower if len(p) > 3)
        if found:
            score += 10
        else:
            issues.append("Products/services not reflected in content")

    # Banned system hashtags check
    banned_tags = {"#amarktai", "#amarktaimarketing", "#aicontent"}
    found_banned = [t for t in banned_tags if t in combined]
    if found_banned:
        score -= 20
        issues.append(f"Banned system hashtags found: {found_banned}")

    # Banned generic visuals check (industry-specific)
    rules = _get_industry_rules(category)
    avoid_terms = [a.lower() for a in rules.get("avoid", [])]
    found_avoid = [a for a in avoid_terms if a in prompt_lower]
    if found_avoid:
        score -= 10
        issues.append(f"Generic/irrelevant visual terms found in image prompt: {found_avoid}")

    score = max(0, min(100, score))
    needs_review = score < 70

    return {
        "creative_relevance_score": score,
        "needs_review": needs_review,
        "issues": issues,
        "business_name": business.get("name", ""),
        "category": category,
    }
