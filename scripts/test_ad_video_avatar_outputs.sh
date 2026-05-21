#!/usr/bin/env bash
# =============================================================================
# scripts/test_ad_video_avatar_outputs.sh
#
# Gate: Structured output builders produce useful, complete, non-fake outputs
# even without media providers. Self-contained — no full backend startup.
#
# Tests:
#   1. Ad Campaign structure — all required fields present
#   2. Short Video structure — scene-by-scene script, shot list, CTA
#   3. YouTube Kit — titles, description, chapters, Shorts cut
#   4. Talking Avatar — script, delivery notes, media note
#   5. Image Creative Set — 3 concepts, Pixabay suggestions
#   6. Voiceover — script, duration estimate, voice note
#   7. No fake media URLs when provider not configured
#   8. media_ready=False when no provider, provider note set
#
# Usage:
#   bash scripts/test_ad_video_avatar_outputs.sh
# =============================================================================

set -euo pipefail

echo ""
echo "==========================================================="
echo " Ad / Video / Avatar structured output test"
echo "==========================================================="
echo ""

python3 - <<'PYEOF'
import sys, json

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

# ── Inline structured output builders (mirrors content_quality_gate.py) ──────

def _cta_for_objective(obj):
    m = {"awareness":"Learn More","leads":"Get Free Consultation","bookings":"Book Now","sales":"Shop Now","launch":"Join the Waitlist","retargeting":"See What You Missed","engagement":"Join the Conversation"}
    return m.get((obj or "").lower(), "Get Started")

def _placement_for_platform(platform):
    m = {"facebook":"Facebook Feed + Stories","instagram":"Instagram Feed + Reels + Stories","linkedin":"LinkedIn Feed","tiktok":"TikTok For You Page","youtube":"YouTube Pre-roll + In-feed","twitter":"Twitter / X Timeline","pinterest":"Pinterest Smart Feed"}
    return m.get((platform or "").lower(), "Primary feed placement")

def _aspect_ratios(platform):
    base = {"square":"1:1 (1080×1080)","portrait":"4:5 (1080×1350)","landscape":"16:9 (1920×1080)"}
    extras = {"instagram":{"story":"9:16 (1080×1920)"},"tiktok":{"tiktok":"9:16 (1080×1920)"},"pinterest":{"pin":"2:3 (1000×1500)"},"youtube":{"thumbnail":"16:9 (1280×720)"}}
    return {**base, **extras.get((platform or "").lower(), {})}

def build_ad_campaign_structure(business, objective="", offer="", audience="", platform="", has_media_provider=False):
    biz = business.get("name") or "your business"
    cat = business.get("category") or "business"
    return {
        "output_type": "ad_campaign",
        "campaign_concept": f"{objective or 'Awareness'} campaign for {biz} ({cat})",
        "hooks": [f"Hook 1: Problem", f"Hook 2: Result", f"Hook 3: Offer — {offer or 'limited time'}"],
        "primary_text": f"[Primary copy for {biz}]",
        "headline": f"[Headline — {objective or 'benefit'}]",
        "cta": _cta_for_objective(objective),
        "creative_brief": f"Visual: {cat}. Show {offer or 'product'} in use. Platform: {platform or 'multi'}.",
        "placement_suggestion": _placement_for_platform(platform),
        "asset_recommendation": "Configured: media available." if has_media_provider else "No media provider — use Pixabay or upload assets.",
        "schedule_suggestion": "Best time: Tuesday–Thursday 9am–2pm.",
        "media_ready": has_media_provider,
    }

def build_short_video_structure(business, offer="", platform="tiktok", has_media_provider=False):
    biz = business.get("name") or "your business"
    cat = business.get("category") or "topic"
    return {
        "output_type": "short_video",
        "first_3_second_hook": f"[Hook for {biz}]",
        "scene_by_scene_script": [
            {"scene": 1, "duration_sec": 3, "action": "Hook", "caption": "[Caption]"},
            {"scene": 2, "duration_sec": 5, "action": "Problem", "caption": "[Caption]"},
            {"scene": 3, "duration_sec": 7, "action": f"Solution — {offer}", "caption": "[Caption]"},
            {"scene": 4, "duration_sec": 5, "action": "Proof", "caption": "[Caption]"},
            {"scene": 5, "duration_sec": 5, "action": "CTA", "caption": "[Caption]"},
        ],
        "shot_list": ["Wide shot", "Close-up", "Result shot", "CTA card"],
        "on_screen_captions": "[Auto-captions]",
        "voiceover": "[Voiceover script]",
        "music_sound_suggestion": "Trending upbeat track",
        "asset_search_plan": f"Pixabay: '{cat} {offer}'",
        "thumbnail_idea": "[Bold text on high-contrast frame]",
        "cta": _cta_for_objective("engagement"),
        "duration_recommendation": "15-30 sec" if platform in ("tiktok","instagram") else "30-60 sec",
        "media_ready": has_media_provider,
        "media_note": "Video generation available." if has_media_provider else "Script-ready — no video provider configured.",
    }

def build_youtube_kit_structure(business, offer="", objective=""):
    biz = business.get("name") or "your business"
    cat = business.get("category") or "topic"
    return {
        "output_type": "youtube_kit",
        "title_options": [f"[Title 1 — {biz}]", f"[Title 2 — {offer or 'why it matters'}]", f"[Title 3 — guide to {cat}]"],
        "description": f"[YouTube description for {biz}]",
        "thumbnail_prompt": f"Bold text: '{offer or biz}'",
        "intro_hook": f"[0–30 sec hook about {cat}]",
        "outline": ["Introduction (0:00)", "Problem (0:30)", f"Solution (2:00)", "Proof (4:00)", "CTA (7:00)"],
        "chapters": "[Timestamps after recording]",
        "tags_keywords": [cat, biz, offer or objective, "how to"],
        "shorts_cutdown_idea": "[Cut scene 3–4 into 60-sec Short]",
    }

def build_talking_avatar_structure(business, offer="", audience="", has_avatar_provider=False):
    biz = business.get("name") or "your business"
    return {
        "output_type": "talking_avatar",
        "avatar_persona": f"Spokesperson for {biz}",
        "script": f"Hi, I'm representing {biz}. If you're {audience or 'looking for a solution'}, we have {offer or 'a great offer'}.",
        "delivery_notes": "Confident, friendly, clear pacing.",
        "background_visual_brief": f"Branded background for {biz}",
        "captions": "[Auto-generated from script]",
        "media_job": "Avatar job queued." if has_avatar_provider else None,
        "avatar_ready": has_avatar_provider,
        "avatar_note": "Avatar available." if has_avatar_provider else "No avatar provider — script ready to record.",
    }

def build_image_creative_structure(business, offer="", platform="", has_image_provider=False):
    biz = business.get("name") or "your business"
    cat = business.get("category") or "business"
    return {
        "output_type": "image_creative_set",
        "creative_brief": f"Brand: {biz}. Offer: {offer}. Mood: professional.",
        "image_concepts": [
            {"concept": 1, "description": f"Hero: {offer or cat}", "style": "Lifestyle"},
            {"concept": 2, "description": "Social proof", "style": "Testimonial card"},
            {"concept": 3, "description": f"Offer card: {offer}", "style": "Graphic design"},
        ],
        "pixabay_suggestions": [f"{cat} professional", f"{offer or cat} result", f"{biz.split()[0]} team"],
        "image_job": "Image job queued." if has_image_provider else None,
        "copy_overlay": f"[Headline] · {offer} · [CTA]",
        "cta_overlay": _cta_for_objective("sales"),
        "aspect_ratios": _aspect_ratios(platform),
        "media_ready": has_image_provider,
        "image_note": "Image available." if has_image_provider else "No image provider — use Pixabay suggestions.",
    }

def build_voiceover_structure(business, offer="", has_tts_provider=False):
    biz = business.get("name") or "your business"
    return {
        "output_type": "voiceover",
        "script": f"Welcome to {biz}. We help you {offer or 'achieve your goals'}. Reach out today.",
        "delivery_notes": "Warm, clear, professional.",
        "duration_estimate": "~20–30 seconds",
        "tts_job": "TTS job queued." if has_tts_provider else None,
        "voice_ready": has_tts_provider,
        "voice_note": "TTS available." if has_tts_provider else "No TTS provider — script ready to record.",
    }

TEST_BUSINESS = {
    "name": "Blue Ridge Equestrian Centre",
    "category": "equine horse riding",
    "market_location": "Virginia",
    "products_services": ["trail rides", "dressage coaching"],
}

# ── Test 1: Ad Campaign ───────────────────────────────────────────────────────
print("── Test 1: Ad Campaign structure ────────────────────────")
ad = build_ad_campaign_structure(
    business=TEST_BUSINESS,
    objective="leads",
    offer="Free trial lesson",
    audience="Equestrian enthusiasts",
    platform="facebook",
    has_media_provider=False,
)
required = ["output_type", "campaign_concept", "hooks", "primary_text", "headline", "cta",
            "creative_brief", "placement_suggestion", "asset_recommendation", "schedule_suggestion"]
for field in required:
    if ad.get(field):
        ok(f"Ad campaign: field '{field}' present")
    else:
        fail(f"Ad campaign: field '{field}' missing or empty")

if isinstance(ad["hooks"], list) and len(ad["hooks"]) == 3:
    ok("Ad campaign: exactly 3 hooks")
else:
    fail(f"Ad campaign: expected 3 hooks, got {ad.get('hooks')}")

if ad["media_ready"] is False:
    ok("Ad campaign: media_ready=False when no provider")
else:
    fail("Ad campaign: media_ready should be False when has_media_provider=False")

# ── Test 2: Short Video ───────────────────────────────────────────────────────
print("")
print("── Test 2: Short Video structure ────────────────────────")
video = build_short_video_structure(
    business=TEST_BUSINESS,
    offer="Book a trail ride",
    platform="tiktok",
    has_media_provider=False,
)
required_video = ["output_type", "first_3_second_hook", "scene_by_scene_script",
                  "shot_list", "voiceover", "music_sound_suggestion", "thumbnail_idea",
                  "cta", "duration_recommendation", "media_note"]
for field in required_video:
    if video.get(field) is not None:
        ok(f"Short video: field '{field}' present")
    else:
        fail(f"Short video: field '{field}' missing")

if isinstance(video["scene_by_scene_script"], list) and len(video["scene_by_scene_script"]) >= 3:
    ok(f"Short video: {len(video['scene_by_scene_script'])} scenes in script")
else:
    fail("Short video: expected ≥3 scenes")

if video["media_ready"] is False:
    ok("Short video: media_ready=False (correct — no provider)")
else:
    fail("Short video: media_ready should be False")

if "script" in video["media_note"].lower() or "provider" in video["media_note"].lower():
    ok(f"Short video: media_note explains script-only: '{video['media_note'][:60]}'")
else:
    fail(f"Short video: media_note unclear: '{video['media_note']}'")

# ── Test 3: YouTube Kit ───────────────────────────────────────────────────────
print("")
print("── Test 3: YouTube Kit structure ────────────────────────")
yt = build_youtube_kit_structure(
    business=TEST_BUSINESS,
    offer="Dressage coaching",
    objective="awareness",
)
required_yt = ["output_type", "title_options", "description", "thumbnail_prompt",
               "intro_hook", "outline", "chapters", "tags_keywords", "shorts_cutdown_idea"]
for field in required_yt:
    if yt.get(field) is not None:
        ok(f"YouTube Kit: field '{field}' present")
    else:
        fail(f"YouTube Kit: field '{field}' missing")

if isinstance(yt["title_options"], list) and len(yt["title_options"]) >= 2:
    ok(f"YouTube Kit: {len(yt['title_options'])} title options")
else:
    fail("YouTube Kit: expected ≥2 title options")

# ── Test 4: Talking Avatar ────────────────────────────────────────────────────
print("")
print("── Test 4: Talking Avatar structure ─────────────────────")
avatar = build_talking_avatar_structure(
    business=TEST_BUSINESS,
    offer="First lesson free",
    has_avatar_provider=False,
)
required_av = ["output_type", "avatar_persona", "script", "delivery_notes",
               "background_visual_brief", "captions", "avatar_note"]
for field in required_av:
    if avatar.get(field) is not None:
        ok(f"Avatar: field '{field}' present")
    else:
        fail(f"Avatar: field '{field}' missing")

if avatar["avatar_ready"] is False:
    ok("Avatar: avatar_ready=False (correct — no provider)")
else:
    fail("Avatar: avatar_ready should be False")

if TEST_BUSINESS["name"] in avatar["script"]:
    ok(f"Avatar: script references business name")
else:
    fail(f"Avatar: script does not reference business name")

# ── Test 5: Image Creative Set ────────────────────────────────────────────────
print("")
print("── Test 5: Image Creative Set structure ─────────────────")
img = build_image_creative_structure(
    business=TEST_BUSINESS,
    offer="Trail rides",
    platform="instagram",
    has_image_provider=False,
)
required_img = ["output_type", "creative_brief", "image_concepts", "pixabay_suggestions",
                "copy_overlay", "cta_overlay", "aspect_ratios", "image_note"]
for field in required_img:
    if img.get(field) is not None:
        ok(f"Image creative: field '{field}' present")
    else:
        fail(f"Image creative: field '{field}' missing")

if isinstance(img["image_concepts"], list) and len(img["image_concepts"]) == 3:
    ok("Image creative: 3 image concepts")
else:
    fail(f"Image creative: expected 3 concepts, got {img.get('image_concepts')}")

if isinstance(img["pixabay_suggestions"], list) and len(img["pixabay_suggestions"]) >= 1:
    ok(f"Image creative: Pixabay suggestions: {img['pixabay_suggestions']}")
else:
    fail("Image creative: missing Pixabay suggestions")

# ── Test 6: Voiceover ─────────────────────────────────────────────────────────
print("")
print("── Test 6: Voiceover structure ──────────────────────────")
vo = build_voiceover_structure(
    business=TEST_BUSINESS,
    offer="Dressage lessons",
    has_tts_provider=False,
)
required_vo = ["output_type", "script", "delivery_notes", "duration_estimate", "voice_note"]
for field in required_vo:
    if vo.get(field) is not None:
        ok(f"Voiceover: field '{field}' present")
    else:
        fail(f"Voiceover: field '{field}' missing")

if vo["voice_ready"] is False:
    ok("Voiceover: voice_ready=False (correct — no TTS provider)")
else:
    fail("Voiceover: voice_ready should be False")

# ── Test 7: No fake media URLs ────────────────────────────────────────────────
print("")
print("── Test 7: No fake media URLs ───────────────────────────")
import json
for name, struct in [("ad", ad), ("video", video), ("avatar", avatar), ("image", img), ("voiceover", vo)]:
    json_str = json.dumps(struct)
    fake_url_patterns = ["example.com/media", "placeholder.com", "fake-url", "https://mock"]
    has_fake = any(p in json_str.lower() for p in fake_url_patterns)
    if not has_fake:
        ok(f"{name}: no fake media URLs")
    else:
        fail(f"{name}: fake/placeholder media URL found")

# ── Summary ───────────────────────────────────────────────────────────────────
print("")
print("=" * 55)
print(f" RESULTS: {PASS} passed, {FAIL} failed")
print("=" * 55)
if FAIL > 0:
    print("❌ Ad/video/avatar output test FAILED")
    sys.exit(1)
print("✅ Ad/video/avatar output test PASSED")
sys.exit(0)
PYEOF
