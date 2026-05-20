# MARKETING BUSINESS GROUNDING AUDIT

**Date:** 2026-05-20  
**Repo:** sharetheherbman-debug/Amarktai-Marketing  

---

## Problem

Generated content was not specific to the selected business:
- Hashtags pointed to `#Amarktai` / `#AmarktaiMarketing` instead of the business
- Horse/equine business received random rain imagery
- Cyber security business received castles and fantasy fields

---

## Root Causes

### 1. AI Provider System Prompt Was Generic

**File:** `backend/app/services/ai_provider.py`

**Before:**
```python
system="You are an expert social media assistant for AmarktAI Marketing."
```

**After:**
```python
system=(
    "You are an expert social media content creator. "
    "Your job is to write content that markets a specific business. "
    "Always keep content grounded to the business name, industry, and "
    "products/services provided. "
    "Never mention Amarktai, AmarktAI, or AI tool names unless the business "
    "itself is Amarktai. "
    "Hashtags must reflect the business industry and audience, not the AI platform."
)
```

### 2. Generation Prompt Lacked Business Context

**Before:**
```python
prompt = f"Write a short {platform} social media post for {name}. Description: {description}."
```

**After:** Prompt now includes:
- Business name + description
- Category/industry
- Products/services (up to 3)
- Target audience
- Market/location
- Brand voice
- Keywords for hashtags
- Explicit instruction: "Market {name} specifically. Do NOT mention Amarktai..."

### 3. No Banned Hashtag Filter

**After:** `_filter_hashtags()` in `content.py` removes:
- `#amarktai`
- `#amarktaimarketing`  
- `#aicontent`

...unless the business name contains "Amarktai". Applied to all generation paths:
`/generate`, `/generate-all`, `/generate-creative`, rejection regen.

### 4. Image Prompts Were Not Business-Specific

**File:** `backend/app/services/media_generation.py`

**Before:** `"Create a high-quality {platform} image prompt for {name} targeting {audience}."`

**After:** Includes category, products/services, audience, explicit instruction to
show imagery relevant to the industry and not use Amarktai branding.

### 5. Business Snapshot Not Stored

**After:** `source_business_snapshot` stored with every generated item, capturing
the exact business state (name, category, products, audience, location, brand_voice)
at the time of generation.

---

## Creative Brief Builder (new service)

**File:** `backend/app/services/creative_brief_builder.py`

Provides industry-specific visual rules:

| Industry | Subjects | Avoid |
|---|---|---|
| Equine/Horse | horses, riders, stable, tack, arena, pasture | random rain, castles, dark storm |
| Cyber Security | SOC dashboard, business team, data lock, threat map | castles, fields, fantasy, swords |
| Technology | software, developer, interface, device | fantasy imagery |
| Fitness | workout, trainer, gym equipment | sedentary, fast food |
| Food | food close-up, chef, fresh ingredients | industrial machinery |
| Default | business team, product, service | generic stock imagery |

### `build_image_prompt(business, platform, objective)` 
Returns grounded prompt + negative prompt + aspect ratio guidance.

### `build_video_brief(business, platform, objective)`
Returns grounded video brief + shot list guidance.

### `score_creative_relevance(content_text, image_prompt, business)`
Returns `creative_relevance_score` (0–100) + issues list.

---

## New Endpoint

`POST /api/v1/content/items/{id}/review-grounding`

Returns:
- `business_grounding_score` (0–100)
- `creative_relevance_score` (0–100)
- `hashtag_relevance_score` (0–100)
- `needs_review` (bool, true if any score < 70)
- `issues` (list of specific problems)
- `suggested_fix` (list of remediation actions)

---

## Acceptance Status

| Requirement | Status |
|---|---|
| Equine business gets horse/equine/riding/stable-specific content | ✅ Grounding enforced via prompt |
| Cyber security gets cyber/security/technology visuals | ✅ Industry rules applied |
| Hashtags are business-specific, not Amarktai-specific | ✅ Banned hashtag filter added |
| Prompt snapshots prove selected business was used | ✅ source_business_snapshot stored |

---

## What Remains

- Real AI grounding validation (requires provider call with grounding scorer model)
- Automatic regeneration when `creative_relevance_score < 70`
- Per-category training/fine-tuning of image prompt vocabulary
