# Marketing Content Quality Audit

> **Date:** 2026-05-21

---

## Hashtag Strategy

### Banned Tags (default)
The following tags are **never** generated unless the business name explicitly contains "Amarktai" or the caller opts in:

- `#Amarktai`
- `#AmarktaiMarketing`
- `#AmarktaiAI`
- `#AIContent`
- `#MarketingAutomation`

### Platform Rules

| Platform | Min tags | Max tags | Style |
|---|---|---|---|
| Instagram | 8 | 20 | Relevant mix |
| Pinterest | 5 | 15 | Keyword rich |
| TikTok | 4 | 8 | Category/trend |
| LinkedIn | 3 | 5 | Professional |
| Facebook | 0 | 5 | Light |
| X / Twitter | 1 | 3 | Minimal |
| Threads | 1 | 3 | Minimal |
| Bluesky | 1 | 3 | Minimal |
| Reddit | 0 | 0 | None |
| YouTube | 3 | 8 | Keywords |
| Telegram | 0 | 3 | Minimal |
| Snapchat | 0 | 3 | Minimal |

### Tag Sources (in order of priority)
1. Business name tokens
2. Category tokens
3. Market/location
4. Products/services list
5. Offer/current offer
6. Platform-specific trend keywords (manual)

### Relevance Scoring
- Score 90: Enough tags to meet platform minimum
- Score 70: Fewer than minimum but some tags present
- Score 40: No tags generated (trigger `needs_review_hashtags`)

---

## Campaign Angle Engine

### 12 Angles Available

| ID | Label | Objective fit |
|---|---|---|
| `problem_solution` | Problem / Solution | leads, awareness |
| `social_proof` | Social Proof | leads, bookings, sales |
| `offer_urgency` | Offer / Urgency | sales, leads, bookings |
| `educational` | Educational | awareness, engagement |
| `myth_busting` | Myth-Busting | engagement, awareness |
| `behind_the_scenes` | Behind the Scenes | awareness, launch, engagement |
| `comparison` | Comparison | sales, retargeting |
| `transformation` | Transformation | awareness, leads |
| `founder_story` | Founder / Story | awareness, launch |
| `objection_handling` | Objection Handling | leads, retargeting |
| `seasonal_local` | Seasonal / Local | engagement, awareness |
| `product_spotlight` | Product Spotlight | sales, launch |

### Variation Rules
1. Each generation stores `campaign_angle` and `hook_style`
2. Regenerate **must** exclude previous angle
3. Improve uses user feedback to hint at angle
4. Duplicate similarity ≥ 85% triggers `needs_review_duplicate`

---

## Content Quality Gate

### Thresholds
- Business grounding score < 70 → `needs_review`
- Hashtag relevance score < 70 → `needs_review`
- Creative relevance score < 70 (when provided) → `needs_review`

### Status Values
- `ready` — all scores ≥ 70
- `needs_review` — one or more scores below threshold
- `needs_review_duplicate` — similarity to existing content ≥ 85%
- `needs_review_hashtags` — banned/irrelevant tags removed

---

## Audit Result

| Check | Status |
|---|---|
| `#Amarktai` never for non-Amarktai business | ✅ Enforced in hashtag_strategy.py |
| Platform-appropriate tag counts | ✅ Per-platform rules in _HASHTAG_RULES |
| Banned tags validated and removed | ✅ validate_hashtags() |
| 12 campaign angles available | ✅ campaign_angle_engine.py |
| Regenerate forces different angle | ✅ angle_for_regenerate() |
| Duplicate detection | ✅ detect_duplicate_similarity() |
| Structured outputs for all 6 creation types | ✅ content_quality_gate.py |
| No fake media URLs in outputs | ✅ media_note explains script-only |
