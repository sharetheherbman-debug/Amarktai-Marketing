# Marketing Ad / Video / Avatar Flow Audit

> **Date:** 2026-05-21

---

## Overview

Previously, all content types returned only a `caption` with no structural differentiation between a quick post and an ad campaign or a video script. This audit documents the structured output builders now added to `backend/app/services/content_quality_gate.py`.

---

## Ad Campaign Structure

**Builder:** `build_ad_campaign_structure()`

| Field | Description | Always present |
|---|---|---|
| `output_type` | "ad_campaign" | ✅ |
| `campaign_concept` | Business + objective summary | ✅ |
| `hooks` | 3 distinct hook angles | ✅ |
| `primary_text` | Main ad body copy | ✅ |
| `headline` | Ad headline | ✅ |
| `cta` | Call-to-action text | ✅ |
| `creative_brief` | Visual direction for designer | ✅ |
| `placement_suggestion` | Where to run the ad | ✅ |
| `asset_recommendation` | Pixabay / provider note | ✅ |
| `schedule_suggestion` | Best time guidance | ✅ |
| `media_ready` | Whether media provider is configured | ✅ |

---

## Short Video / Reel / TikTok Structure

**Builder:** `build_short_video_structure()`

| Field | Description | Always present |
|---|---|---|
| `output_type` | "short_video" | ✅ |
| `first_3_second_hook` | Opening hook text | ✅ |
| `scene_by_scene_script` | List of scenes with timing, action, caption | ✅ |
| `shot_list` | Camera directions | ✅ |
| `on_screen_captions` | Caption note | ✅ |
| `voiceover` | Matched voiceover script | ✅ |
| `music_sound_suggestion` | Music/sound direction | ✅ |
| `asset_search_plan` | Pixabay search query | ✅ |
| `thumbnail_idea` | Thumbnail concept | ✅ |
| `cta` | Call-to-action | ✅ |
| `duration_recommendation` | Platform-appropriate length | ✅ |
| `media_ready` | Whether video provider is configured | ✅ |
| `media_note` | Plain-English note on provider status | ✅ |

---

## YouTube Kit Structure

**Builder:** `build_youtube_kit_structure()`

| Field | Description | Always present |
|---|---|---|
| `output_type` | "youtube_kit" | ✅ |
| `title_options` | 3 title variants | ✅ |
| `description` | Full YouTube description | ✅ |
| `thumbnail_prompt` | Thumbnail creative brief | ✅ |
| `intro_hook` | 0–30s hook script | ✅ |
| `outline` | Video outline with timestamps | ✅ |
| `chapters` | Chapter markers note | ✅ |
| `tags_keywords` | YouTube keyword tags | ✅ |
| `shorts_cutdown_idea` | How to cut a YouTube Short | ✅ |

---

## Talking Avatar Structure

**Builder:** `build_talking_avatar_structure()`

| Field | Description | Always present |
|---|---|---|
| `output_type` | "talking_avatar" | ✅ |
| `avatar_persona` | Persona description | ✅ |
| `script` | Full avatar script (references business name + offer) | ✅ |
| `delivery_notes` | Pacing, emphasis guidance | ✅ |
| `background_visual_brief` | Background/visual direction | ✅ |
| `captions` | Caption note for SRT/VTT | ✅ |
| `avatar_ready` | Whether avatar provider is configured | ✅ |
| `avatar_note` | Plain-English provider status note | ✅ |

---

## Image Creative Set Structure

**Builder:** `build_image_creative_structure()`

| Field | Description | Always present |
|---|---|---|
| `output_type` | "image_creative_set" | ✅ |
| `creative_brief` | Brand/mood/offer summary | ✅ |
| `image_concepts` | 3 concept descriptions with style notes | ✅ |
| `pixabay_suggestions` | 3 Pixabay search queries | ✅ |
| `copy_overlay` | Headline + CTA overlay text | ✅ |
| `cta_overlay` | CTA text | ✅ |
| `aspect_ratios` | Platform-appropriate ratios | ✅ |
| `media_ready` | Whether image provider is configured | ✅ |
| `image_note` | Plain-English provider status note | ✅ |

---

## Voiceover Structure

**Builder:** `build_voiceover_structure()`

| Field | Description | Always present |
|---|---|---|
| `output_type` | "voiceover" | ✅ |
| `script` | Full voiceover script | ✅ |
| `delivery_notes` | Tone/pacing guidance | ✅ |
| `duration_estimate` | Estimated reading time | ✅ |
| `voice_ready` | Whether TTS provider is configured | ✅ |
| `voice_note` | Plain-English TTS status note | ✅ |

---

## No-Provider Guarantee

All builders return a **complete, useful output** even when no media provider is configured:
- `media_ready` / `avatar_ready` / `voice_ready` = `False`
- `media_note` / `avatar_note` / `voice_note` explains "script-ready, no provider configured"
- No fake media URLs are generated
- Pixabay search suggestions are always populated for image-based types

---

## Audit Result

| Check | Status |
|---|---|
| All 6 creation types have structured builders | ✅ |
| No fake media URLs when provider missing | ✅ |
| Script/brief always generated regardless of provider | ✅ |
| Media note explains provider status in plain English | ✅ |
| Platform-appropriate aspect ratios in image output | ✅ |
| Pixabay suggestions in image and video outputs | ✅ |
