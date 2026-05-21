# Marketing Hashtag Grounding Audit

> **Date:** 2026-05-21

---

## Problem Statement

Previous hashtag generation could produce `#Amarktai`, `#AmarktaiMarketing`, `#AIContent`, `#MarketingAutomation` for ANY business — even a horse riding school or a cyber security firm. These tags are irrelevant and damage brand credibility.

---

## Fix Applied

**File:** `backend/app/services/hashtag_strategy.py`

### Banned by Default

```python
_BANNED_DEFAULT = {
    "#amarktai",
    "#amarktaimarketing",
    "#amarktaiai",
    "#aicontent",
    "#marketingautomation",
}
```

These tags are **only** allowed when:
1. The business name contains "Amarktai" (auto-detected), OR
2. The caller explicitly passes `allow_amarktai=True`

### Tag Sources (in priority order)

1. `business.name` — tokenised
2. `business.category` — tokenised
3. `business.market_location` — tokenised
4. `business.products_services` or `business.key_features` — tokenised
5. `business.offer` / `business.current_offer`
6. Caller-supplied `extra_tokens`

### Platform Rules

| Platform | Max tags | Style |
|---|---|---|
| Instagram | 20 | Relevant mix |
| Pinterest | 15 | Keyword rich |
| TikTok | 8 | Category/trend |
| LinkedIn | 5 | Professional |
| Facebook | 5 | Light |
| X / Twitter | 3 | Minimal |
| Threads | 3 | Minimal |
| Bluesky | 3 | Minimal |
| Reddit | 0 | None |
| YouTube | 8 | Keywords |
| Telegram | 3 | Minimal |
| Snapchat | 3 | Minimal |

---

## Test Cases Verified

### Horse / Equine Business

- Business: Blue Ridge Equestrian Centre, category: equine horse riding lessons stables
- Platform: Instagram
- Expected: equine-relevant tags (`#BlueRidge`, `#Equestrian`, `#Horse`, etc.)
- Expected: NO `#Amarktai`, `#AIContent`, `#MarketingAutomation`
- **Result: ✅ Passes `test_hashtag_business_grounding.sh`**

### Cyber Security Business

- Business: ShieldForce Security Solutions, category: cybersecurity penetration testing
- Platform: LinkedIn
- Expected: 3–5 professional tags, security-relevant
- Expected: NO Amarktai brand tags
- **Result: ✅ Passes `test_hashtag_business_grounding.sh`**

### Amarktai Business (brand tags allowed)

- Business: Amarktai Marketing Platform
- Platform: Instagram
- Expected: Brand tags allowed (detected via name containing "Amarktai")
- **Result: ✅ Brand tags are permitted for the Amarktai business itself**

### Reddit — No hashtags

- Platform: Reddit
- Expected: Empty hashtag list
- **Result: ✅ Returns `[]`**

### validate_hashtags — Removes banned tags

- Input: `["#HorseRiding", "#Amarktai", "#Equestrian", "#AIContent"]`
- Business: horse riding school (non-Amarktai)
- Expected: `#Amarktai` and `#AIContent` removed, `needs_review_hashtags: True`
- **Result: ✅ Correct**

---

## API Surface

```python
# Build hashtag strategy from business profile
result = build_hashtag_strategy(business_dict, "instagram")
# Returns: {hashtags, hashtag_relevance_score, issues, platform, limit}

# Validate existing hashtag list
validated = validate_hashtags(existing_tags, business_dict)
# Returns: {ok, hashtags, removed, issues, needs_review_hashtags}
```

---

## Audit Result

| Check | Status |
|---|---|
| `#Amarktai` never for non-Amarktai business | ✅ |
| `#AmarktaiAI` never for non-Amarktai business | ✅ |
| `#AIContent` never by default | ✅ |
| `#MarketingAutomation` never by default | ✅ |
| Platform-appropriate tag counts enforced | ✅ |
| Reddit returns empty list | ✅ |
| Tags sourced from business fields only | ✅ |
| validate_hashtags() removes and flags banned tags | ✅ |
| needs_review_hashtags flag set when tags removed | ✅ |
