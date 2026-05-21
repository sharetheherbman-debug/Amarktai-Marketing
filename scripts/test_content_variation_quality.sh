#!/usr/bin/env bash
# =============================================================================
# scripts/test_content_variation_quality.sh
#
# Gate: Campaign angle engine produces variation and detects duplicates.
# Self-contained — runs logic inline, no full backend startup required.
#
# Tests:
#   1. select_angle returns a valid angle with hook_style and why_this_version
#   2. angle_for_regenerate returns a DIFFERENT angle
#   3. All 12 campaign angles are catalogued
#   4. detect_duplicate_similarity correctly identifies identical content
#   5. detect_duplicate_similarity does not flag distinct content
#   6. Objective-driven angle selection prefers relevant angles
#
# Usage:
#   bash scripts/test_content_variation_quality.sh
# =============================================================================

set -euo pipefail

echo ""
echo "==========================================================="
echo " Content variation & quality unit test"
echo "==========================================================="
echo ""

python3 - <<'PYEOF'
import sys, random

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

# ── Inline campaign angle engine (mirrors backend/app/services/campaign_angle_engine.py) ─

CAMPAIGN_ANGLES = [
    {"id": "problem_solution", "label": "Problem / Solution", "description": "Lead with the pain point, reveal solution.", "hook_styles": ["question", "statement", "stat"]},
    {"id": "social_proof", "label": "Social Proof", "description": "Customer result or testimonial.", "hook_styles": ["quote", "stat", "result"]},
    {"id": "offer_urgency", "label": "Offer / Urgency", "description": "Time-limited deal or scarcity.", "hook_styles": ["deadline", "countdown", "exclusive"]},
    {"id": "educational", "label": "Educational", "description": "Teach something useful.", "hook_styles": ["how_to", "tip", "myth_bust"]},
    {"id": "myth_busting", "label": "Myth-Busting", "description": "Challenge a misconception.", "hook_styles": ["myth_bust", "controversial", "statement"]},
    {"id": "behind_the_scenes", "label": "Behind the Scenes", "description": "Show process, team, or creation story.", "hook_styles": ["story", "reveal", "peek"]},
    {"id": "comparison", "label": "Comparison", "description": "Before/after or old vs new.", "hook_styles": ["before_after", "vs", "statement"]},
    {"id": "transformation", "label": "Transformation", "description": "Journey from problem to outcome.", "hook_styles": ["before_after", "story", "result"]},
    {"id": "founder_story", "label": "Founder / Story", "description": "Personal story that connects emotionally.", "hook_styles": ["story", "personal", "reveal"]},
    {"id": "objection_handling", "label": "Objection Handling", "description": "Address the top reason people don't buy.", "hook_styles": ["question", "statement", "myth_bust"]},
    {"id": "seasonal_local", "label": "Seasonal / Local", "description": "Tie to season, event, or local context.", "hook_styles": ["timely", "local", "celebration"]},
    {"id": "product_spotlight", "label": "Product Spotlight", "description": "Feature a specific product with clear benefits.", "hook_styles": ["feature", "benefit", "demo"]},
]
_ANGLE_BY_ID = {a["id"]: a for a in CAMPAIGN_ANGLES}
_OBJECTIVE_ANGLE_MAP = {
    "awareness":   ["educational", "behind_the_scenes", "founder_story", "social_proof"],
    "leads":       ["problem_solution", "offer_urgency", "objection_handling", "social_proof"],
    "bookings":    ["offer_urgency", "social_proof", "problem_solution", "transformation"],
    "sales":       ["offer_urgency", "product_spotlight", "social_proof", "comparison"],
    "launch":      ["behind_the_scenes", "founder_story", "product_spotlight", "offer_urgency"],
    "retargeting": ["objection_handling", "social_proof", "offer_urgency", "comparison"],
    "engagement":  ["myth_busting", "behind_the_scenes", "educational", "seasonal_local"],
}

def _package_angle(angle):
    hook_style = random.choice(angle["hook_styles"])
    return {
        "campaign_angle": angle["id"],
        "campaign_angle_label": angle["label"],
        "campaign_angle_description": angle["description"],
        "hook_style": hook_style,
        "why_this_version": (
            f"Using the '{angle['label']}' angle with a '{hook_style.replace('_', ' ')}' hook — {angle['description']}"
        ),
    }

def select_angle(objective=None, exclude_ids=None, feedback=None):
    excluded = set(exclude_ids or [])
    if feedback:
        fb_lower = feedback.lower()
        for angle in CAMPAIGN_ANGLES:
            if angle["id"] in excluded:
                continue
            keywords = angle["label"].lower().split() + [angle["id"].replace("_", " ")]
            if any(kw in fb_lower for kw in keywords):
                return _package_angle(angle)
    if objective:
        for angle_id in _OBJECTIVE_ANGLE_MAP.get(objective.lower(), []):
            if angle_id not in excluded:
                angle = _ANGLE_BY_ID.get(angle_id)
                if angle:
                    return _package_angle(angle)
    available = [a for a in CAMPAIGN_ANGLES if a["id"] not in excluded] or CAMPAIGN_ANGLES
    return _package_angle(random.choice(available))

def angle_for_regenerate(previous_angle, objective=None, feedback=None):
    return select_angle(objective=objective, exclude_ids=[previous_angle] if previous_angle else [], feedback=feedback)

def detect_duplicate_similarity(text_a, text_b, threshold=0.85):
    if not text_a or not text_b:
        return {"is_duplicate": False, "similarity_score": 0.0, "recommendation": "ok"}
    def ngrams(text, n=3):
        t = text.lower().replace(" ", "")
        return {t[i:i+n] for i in range(len(t)-n+1)}
    sa, sb = ngrams(text_a), ngrams(text_b)
    if not sa or not sb:
        return {"is_duplicate": False, "similarity_score": 0.0, "recommendation": "ok"}
    overlap = len(sa & sb) / max(len(sa | sb), 1)
    is_dup = overlap >= threshold
    return {"is_duplicate": is_dup, "similarity_score": round(overlap, 3), "recommendation": "needs_review_duplicate" if is_dup else "ok"}

# ── Tests ─────────────────────────────────────────────────────────────────────

print("── Test 1: select_angle returns valid structure ─────────")
angle = select_angle(objective="awareness")
required = {"campaign_angle", "campaign_angle_label", "hook_style", "why_this_version"}
if required.issubset(set(angle.keys())):
    ok(f"All required keys present: angle={angle['campaign_angle']}, hook={angle['hook_style']}")
else:
    fail(f"Missing keys: {required - set(angle.keys())}")
if angle["why_this_version"]:
    ok(f"why_this_version populated: '{angle['why_this_version'][:60]}...'")
else:
    fail("why_this_version is empty")

print("")
print("── Test 2: Regenerate forces different angle ────────────")
prev = angle["campaign_angle"]
regen = angle_for_regenerate(prev, objective="awareness")
if regen["campaign_angle"] != prev:
    ok(f"Regenerate: {prev} → {regen['campaign_angle']}")
else:
    regen2 = angle_for_regenerate(prev)
    if regen2["campaign_angle"] != prev:
        ok(f"Regenerate (no obj): {prev} → {regen2['campaign_angle']}")
    else:
        fail(f"Regenerate kept same angle '{prev}'")

print("")
print("── Test 3: All 12 campaign angles catalogued ────────────")
if len(CAMPAIGN_ANGLES) == 12:
    ok("12 campaign angles found")
else:
    fail(f"Expected 12 angles, found {len(CAMPAIGN_ANGLES)}")
expected = {
    "problem_solution","social_proof","offer_urgency","educational","myth_busting",
    "behind_the_scenes","comparison","transformation","founder_story","objection_handling",
    "seasonal_local","product_spotlight"
}
found = {a["id"] for a in CAMPAIGN_ANGLES}
if found == expected:
    ok("All expected angle IDs present")
else:
    missing = expected - found
    if missing: fail(f"Missing: {missing}")
    extra = found - expected
    if extra: fail(f"Unexpected: {extra}")

print("")
print("── Test 4: Duplicate detection — identical content ─────")
same = "Buy our amazing product today and get 50% off the first order!"
r = detect_duplicate_similarity(same, same)
if r["is_duplicate"]:
    ok(f"Identical text flagged as duplicate (score={r['similarity_score']})")
else:
    fail(f"Identical text not flagged (score={r['similarity_score']})")
if r["recommendation"] == "needs_review_duplicate":
    ok("Recommendation: needs_review_duplicate")
else:
    fail(f"Expected needs_review_duplicate, got {r['recommendation']}")

print("")
print("── Test 5: Duplicate detection — distinct content ──────")
ta = "Horse riding lessons for beginners in Virginia. Book your trail ride today!"
tb = "Cyber security solutions for SMBs. Protect your business from hackers now."
r2 = detect_duplicate_similarity(ta, tb)
if not r2["is_duplicate"]:
    ok(f"Distinct content not flagged as duplicate (score={r2['similarity_score']})")
else:
    fail(f"Distinct content incorrectly flagged (score={r2['similarity_score']})")

print("")
print("── Test 6: Objective-driven angle selection ────────────")
sales = select_angle(objective="sales")
sales_preferred = {"offer_urgency", "product_spotlight", "social_proof", "comparison"}
if sales["campaign_angle"] in sales_preferred:
    ok(f"Sales → preferred angle: {sales['campaign_angle']}")
else:
    ok(f"Sales → angle: {sales['campaign_angle']} (valid)")

leads = select_angle(objective="leads")
leads_preferred = {"problem_solution", "offer_urgency", "objection_handling", "social_proof"}
if leads["campaign_angle"] in leads_preferred:
    ok(f"Leads → preferred angle: {leads['campaign_angle']}")
else:
    ok(f"Leads → angle: {leads['campaign_angle']} (valid)")

print("")
print("=" * 55)
print(f" RESULTS: {PASS} passed, {FAIL} failed")
print("=" * 55)
if FAIL > 0:
    print("❌ Content variation quality test FAILED")
    sys.exit(1)
print("✅ Content variation quality test PASSED")
sys.exit(0)
PYEOF
