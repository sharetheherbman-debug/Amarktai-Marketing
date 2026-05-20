# MARKETING CREATIVE RELEVANCE AUDIT

**Date:** 2026-05-20  
**Repo:** sharetheherbman-debug/Amarktai-Marketing  

---

## Problem

Generated imagery/video prompts were unrelated to the business being marketed:
- Horse business → random rain/dark weather
- Cyber security business → castles, fields, fantasy landscapes
- All businesses → Amarktai-branded content

---

## Root Cause

Image prompts in `media_generation.py` used only the business name and audience,
with no category, products, or industry context. The AI had no signal to select
relevant visual themes.

---

## Fixes

### 1. `generate_image_prompt()` — Now Business-Specific

**Before:**
```python
prompt = f"Create a high-quality {platform} image prompt for {name} targeting {audience}."
```

**After (includes):**
- Business name + description
- Industry/category
- Products/services
- Target audience
- Explicit instruction: "image must be directly relevant to {name} and its industry"
- Instruction to NOT use Amarktai branding
- Instruction: "Show imagery that immediately communicates what {name} does"

### 2. `generate_video_script()` — Now Business-Specific

Includes category, products, explicit "grounded to what {name} actually does" instruction.

### 3. Creative Brief Builder

**File:** `backend/app/services/creative_brief_builder.py`

`build_image_prompt(business, platform, objective)` produces:
- `image_prompt`: Full grounded prompt with subject, setting, style, context
- `negative_prompt`: Explicit avoid list (fantasy, castles, unrelated imagery, Amarktai branding)
- `aspect_ratio`: Platform-correct aspect ratio

Example for equine business on Instagram:
```
Professional instagram image for Sunrise Equestrian Centre (equine).
Subject: horse, rider, stable, tack, in a stable yard, equestrian centre, outdoor arena setting.
Style: natural outdoor photography, golden hour light, action or portrait.
Tone: lifestyle, aspirational, performance-focused.
Products/services: Horse riding lessons, Livery services, Equine health care.
...
Platform: instagram, aspect ratio: square 1:1 or portrait 4:5 for feed; 9:16 vertical for Stories/Reels.
```

Negative prompt:
```
Avoid: random rain, dark storm, castles, fantasy landscapes, unrelated animals.
Do not show: Amarktai branding, generic stock office workers, unrelated industry imagery...
```

---

## Creative Relevance Scoring

`score_creative_relevance(content_text, image_prompt, business)` checks:

| Check | Score Impact |
|---|---|
| Business name in content/prompt | +15 |
| Category keywords present | +15 |
| Products/services mentioned | +10 |
| Banned system hashtags found | −20 |
| Industry avoid-terms in prompt | −10 |

**Threshold:** Score < 70 → `needs_review: true`

---

## Review Grounding Endpoint

`POST /api/v1/content/items/{id}/review-grounding`

Returns all three scores + issues + suggested fixes.
Frontend can show a "Review needed" badge when `needs_review: true`.

---

## Industry Visual Rules

### Equine / Horse
- **Subjects:** horses, riders, stable yard, tack, arenas, pasture, equine care, show prep
- **Avoid:** random rain, dark storm, castles, fantasy landscapes, unrelated animals

### Cyber Security
- **Subjects:** secure networks, SOC dashboards, business teams, lock/data visuals, threat maps, professional tech
- **Avoid:** castles, random fields, fantasy landscapes, medieval imagery, swords

### Technology
- **Subjects:** software product, developer, tech professional, interface, device
- **Avoid:** fantasy imagery, unrelated nature scenes

### Fitness
- **Subjects:** person exercising, gym equipment, outdoor workout, trainer
- **Avoid:** sedentary scenes, fast food

### Food
- **Subjects:** food close-up, plating, chef, fresh ingredients
- **Avoid:** industrial machinery, generic stock office

---

## What Remains

- Auto-regeneration hook: if `creative_relevance_score < 70` on save → regenerate before returning
- Deep-learning-based relevance scoring (requires provider call)
- Platform-specific creative templates per industry
- Negative prompt injection into actual image generation API calls
