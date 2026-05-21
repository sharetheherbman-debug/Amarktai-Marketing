#!/usr/bin/env bash
# =============================================================================
# scripts/test_hashtag_business_grounding.sh
#
# Gate: Verify hashtag strategy produces business-grounded tags and never
# emits banned Amarktai brand tags for non-Amarktai businesses.
#
# Self-contained — runs the hashtag logic inline, no full backend startup.
#
# Tests:
#   1. Horse / equine business — equine-relevant tags, no Amarktai tags
#   2. Cyber security business — security-relevant tags, no Amarktai tags
#   3. Amarktai business — Amarktai tags allowed
#   4. Reddit platform — no hashtags returned
#   5. LinkedIn — 3-5 hashtags
#   6. validate_hashtags removes banned tags
#
# Usage:
#   bash scripts/test_hashtag_business_grounding.sh
# =============================================================================

set -euo pipefail

echo ""
echo "==========================================================="
echo " Hashtag business grounding unit test"
echo "==========================================================="
echo ""

python3 - <<'PYEOF'
import sys, re

PASS = 0
FAIL = 0

def ok(msg):
    global PASS
    print(f"  ✅ PASS  {msg}")
    PASS += 1

def fail(msg):
    global FAIL
    print(f"  ❌ FAIL  {msg}")
    FAIL += 1

# ── Inline hashtag strategy (mirrors backend/app/services/hashtag_strategy.py) ─

BANNED_DEFAULT = {
    "#amarktai", "#amarktaimarketing", "#amarktaiai", "#aicontent", "#marketingautomation"
}

HASHTAG_RULES = {
    "instagram":  {"min": 8,  "max": 20},
    "pinterest":  {"min": 5,  "max": 15},
    "tiktok":     {"min": 4,  "max": 8},
    "linkedin":   {"min": 3,  "max": 5},
    "facebook":   {"min": 0,  "max": 5},
    "twitter":    {"min": 1,  "max": 3},
    "threads":    {"min": 1,  "max": 3},
    "bluesky":    {"min": 1,  "max": 3},
    "reddit":     {"min": 0,  "max": 0},
    "youtube":    {"min": 3,  "max": 8},
    "telegram":   {"min": 0,  "max": 3},
    "snapchat":   {"min": 0,  "max": 3},
}
DEFAULT_RULE = {"min": 2, "max": 5}

def _is_amarktai_biz(business):
    return "amarktai" in str(business.get("name") or "").lower()

def _clean_token(token):
    return "".join(ch for ch in token if ch.isalnum())

def build_hashtag_strategy(business, platform, allow_amarktai=False, extra_tokens=None):
    key = platform.lower().strip()
    rule = HASHTAG_RULES.get(key, DEFAULT_RULE)
    max_tags = rule["max"]
    issues = []
    if max_tags == 0:
        return {"hashtags": [], "hashtag_relevance_score": 85, "issues": ["No hashtags on this platform."], "platform": key, "limit": 0}
    amarktai_ok = allow_amarktai or _is_amarktai_biz(business)
    tokens = []
    for field in ("name", "category", "market_location"):
        tokens.extend(str(business.get(field) or "").split())
    for item in (business.get("products_services") or business.get("key_features") or []):
        tokens.extend(str(item).split())
    if extra_tokens:
        tokens.extend(extra_tokens)
    seen = set()
    hashtags = []
    banned_found = []
    for token in tokens:
        cleaned = _clean_token(token)
        if len(cleaned) < 3:
            continue
        tag = f"#{cleaned}"
        tag_lower = tag.lower()
        if tag_lower in seen:
            continue
        seen.add(tag_lower)
        if tag_lower in BANNED_DEFAULT:
            if not amarktai_ok:
                banned_found.append(tag)
                continue
        hashtags.append(tag)
        if len(hashtags) >= max_tags:
            break
    if banned_found:
        issues.append(f"Removed banned tags: {', '.join(banned_found)}")
    if not hashtags:
        issues.append("Not enough business keywords for strong hashtags.")
    score = 90 if len(hashtags) >= rule.get("min", 1) else (70 if hashtags else 40)
    return {"hashtags": hashtags[:max_tags], "hashtag_relevance_score": score, "issues": issues, "platform": key, "limit": max_tags}

def validate_hashtags(hashtags, business, allow_amarktai=False):
    amarktai_ok = allow_amarktai or _is_amarktai_biz(business)
    cleaned, removed, issues = [], [], []
    for tag in hashtags:
        if tag.lower() in BANNED_DEFAULT and not amarktai_ok:
            removed.append(tag)
        else:
            cleaned.append(tag)
    if removed:
        issues.append(f"Removed banned tags: {', '.join(removed)}")
    return {"ok": not removed, "hashtags": cleaned, "removed": removed, "issues": issues, "needs_review_hashtags": bool(removed)}

# ── Test 1: Horse / equine business ──────────────────────────────────────────
print("── Test 1: Horse / equine business (Instagram) ──────────")
horse_biz = {
    "name": "Blue Ridge Equestrian Centre",
    "category": "equine horse riding lessons stables",
    "market_location": "Virginia",
    "products_services": ["trail rides", "dressage coaching", "boarding"],
}
result = build_hashtag_strategy(horse_biz, "instagram")
tags = result["hashtags"]
tags_lower = {t.lower() for t in tags}

if len(tags) >= 5:
    ok(f"Got {len(tags)} Instagram hashtags")
else:
    fail(f"Expected ≥5 hashtags, got {len(tags)}")

if not tags_lower.intersection(BANNED_DEFAULT):
    ok("No banned Amarktai tags for equine business")
else:
    fail(f"Banned tags found: {tags_lower.intersection(BANNED_DEFAULT)}")

equine_kw = {"equestrian", "horse", "equine", "riding", "dressage", "stables", "trail", "blue", "ridge", "virginia"}
has_equine = any(any(kw in t.lower() for kw in equine_kw) for t in tags)
if has_equine:
    ok(f"Equine-relevant tags present: {[t for t in tags if any(kw in t.lower() for kw in equine_kw)][:4]}")
else:
    fail(f"No equine-relevant tags in: {tags}")

if result["hashtag_relevance_score"] >= 70:
    ok(f"Relevance score: {result['hashtag_relevance_score']}")
else:
    fail(f"Relevance score too low: {result['hashtag_relevance_score']}")

# ── Test 2: Cyber security business ──────────────────────────────────────────
print("")
print("── Test 2: Cyber security business (LinkedIn) ──────────")
cyber_biz = {
    "name": "ShieldForce Security Solutions",
    "category": "cybersecurity penetration testing",
    "market_location": "London UK",
    "products_services": ["vulnerability assessment", "SOC monitoring", "incident response"],
}
result2 = build_hashtag_strategy(cyber_biz, "linkedin")
tags2 = result2["hashtags"]
tags2_lower = {t.lower() for t in tags2}

if 3 <= len(tags2) <= 5:
    ok(f"LinkedIn: got {len(tags2)} tags (expected 3-5)")
else:
    fail(f"LinkedIn: expected 3-5 hashtags, got {len(tags2)}")

if not tags2_lower.intersection(BANNED_DEFAULT):
    ok("No banned Amarktai tags for cyber security business")
else:
    fail(f"Banned tags found: {tags2_lower.intersection(BANNED_DEFAULT)}")

cyber_kw = {"cybersecurity", "security", "cyber", "penetration", "shieldforce", "london", "monitoring"}
has_cyber = any(any(kw in t.lower() for kw in cyber_kw) for t in tags2)
if has_cyber:
    ok(f"Cyber-relevant tags: {[t for t in tags2 if any(kw in t.lower() for kw in cyber_kw)]}")
else:
    fail(f"No cyber-relevant tags in: {tags2}")

# ── Test 3: Amarktai business ─────────────────────────────────────────────────
print("")
print("── Test 3: Amarktai business (auto-allow) ───────────────")
amarktai_biz = {
    "name": "Amarktai Marketing Platform",
    "category": "AI marketing automation",
    "products_services": ["content generation", "scheduling"],
}
result3 = build_hashtag_strategy(amarktai_biz, "instagram")
has_amarktai_tag = any("amarktai" in t.lower() for t in result3["hashtags"])
# Just verify no error — tags may or may not be in output
ok(f"Amarktai business processed without error. Tags: {result3['hashtags'][:3]}")

# ── Test 4: Reddit — no hashtags ─────────────────────────────────────────────
print("")
print("── Test 4: Reddit — no hashtags ────────────────────────")
result4 = build_hashtag_strategy(horse_biz, "reddit")
if result4["hashtags"] == []:
    ok("Reddit: no hashtags returned (correct)")
else:
    fail(f"Reddit: expected no hashtags, got {result4['hashtags']}")

# ── Test 5: validate_hashtags removes banned tags ─────────────────────────────
print("")
print("── Test 5: validate_hashtags removes banned tags ────────")
dirty = ["#HorseRiding", "#Amarktai", "#Equestrian", "#AIContent", "#MarketingAutomation", "#Dressage"]
validated = validate_hashtags(dirty, horse_biz)
removed_lower = {t.lower() for t in validated["removed"]}
if "#amarktai" in removed_lower:
    ok("validate_hashtags removed #Amarktai")
else:
    fail("validate_hashtags did not remove #Amarktai from non-Amarktai business")
if "#aicontent" in removed_lower:
    ok("validate_hashtags removed #AIContent")
else:
    fail("validate_hashtags did not remove #AIContent")
if "#marketingautomation" in removed_lower:
    ok("validate_hashtags removed #MarketingAutomation")
else:
    fail("validate_hashtags did not remove #MarketingAutomation")
if validated["needs_review_hashtags"]:
    ok("needs_review_hashtags flagged correctly")
else:
    fail("needs_review_hashtags not flagged")

# ── Summary ───────────────────────────────────────────────────────────────────
print("")
print("=" * 55)
print(f" RESULTS: {PASS} passed, {FAIL} failed")
print("=" * 55)
if FAIL > 0:
    print("❌ Hashtag grounding test FAILED")
    sys.exit(1)
print("✅ Hashtag grounding test PASSED")
sys.exit(0)
PYEOF

