# Marketing Content Studio — Product Audit

> **Date:** 2026-05-21  
> **Status:** Post PR #19 — guided rebuild in progress

---

## Summary

The Content Studio previously presented a technical test-bench layout: raw section buttons as labels, backend/debug metadata in user-facing cards, a library of recent generated content dominating the main workspace, and no clear step-by-step creation flow. This audit documents the state before the rebuild and the classifications made.

---

## UI Element Classification

### Content Studio — Main Workspace

| Element | Previous state | Classification | Action taken |
|---|---|---|---|
| Section tabs (Campaign Plan, Platform Posts, Ads, …) | Non-functional label buttons with no routing | `placeholder` / `remove from main flow` | Replaced with guided 5-step flow |
| Business selector | Present | `keep user-facing` | Kept in Step 1 |
| Platform selector (single) | Present | `keep user-facing` | Expanded to multi-select in Step 3 |
| Objective field | Plain text input | `keep user-facing` | Upgraded to dropdown in Step 1 |
| Offer / Product field | Plain text input | `keep user-facing` | Kept in Step 1 |
| Tone field | Plain text input | `keep user-facing` | Kept in Step 1 |
| Audience field | Plain text area | `keep user-facing` | Kept in Step 1 |
| Budget mode dropdown | Debug/internal option | `move to Advanced details` | Removed from main flow |
| Provider mode dropdown | Debug/internal option | `move to Advanced details` | Removed from main flow |
| Active section debug box | Shows "Active section: …" | `remove from main flow` | Removed |
| Format dropdown (technical strings) | Shows raw format IDs | `move to What to Create cards` | Replaced with creation intent cards |
| Generate button | Present | `keep user-facing` | Kept in Step 4 |
| Generate all 12 button | Present | `keep user-facing` | Kept as Generate Full Pack |
| Full 12-platform pack button | Present | `keep user-facing` | Kept in Step 4 |
| Content Library card | Dominates workspace | `move to secondary area` | Moved to collapsible "Drafts & Library" drawer |

### Content Cards (Library Items)

| Field shown | Classification | Action taken |
|---|---|---|
| Platform | `keep user-facing` | Kept — shows human label |
| Format | `keep user-facing` | Shows human-readable format |
| Status badge | `keep user-facing` | Simplified — shows "Draft" for degraded |
| Caption / body | `keep user-facing` | Kept |
| Hook (hooks[0]) | `keep user-facing` | Added to card |
| CTA | `keep user-facing` | Added to card |
| Hashtags | `keep user-facing` | Added as tag chips |
| Warnings | `keep user-facing` | Shown in plain English |
| Rejection reason | `keep user-facing` | Shown in plain English |
| providerActual | `move to Advanced details` | Hidden — in accordion |
| modelActual | `move to Advanced details` | Hidden — in accordion |
| sourceAction | `move to Advanced details` | Hidden — in accordion |
| generatedBy | `move to Advanced details` | Hidden — in accordion |
| variationSeed | `move to Advanced details` | Hidden — in accordion |
| businessGroundingScore (raw) | `move to Advanced details` | Hidden — in accordion |
| hashtagRelevanceScore (raw) | `move to Advanced details` | Hidden — in accordion |
| creativeRelevanceScore (raw) | `move to Advanced details` | Hidden — in accordion |
| fallbackChain | `move to Advanced details` | Hidden — in accordion |
| mediaJobIds | `move to Advanced details` | Hidden — in accordion |
| mediaAssetIds | `move to Advanced details` | Hidden — in accordion |
| "meta" preview tab | `move to Advanced details` | Replaced by accordion |
| Provider/model badge in card body | `move to Advanced details` | Removed from main badges |

### Dashboard Home

| Element | Classification | Notes |
|---|---|---|
| Recent generated content section | `remove from main flow` | Removed — showed raw scrape_status, degraded badges |
| Business stats cards | `keep user-facing` | Kept |
| Quick actions | `keep user-facing` | Kept |

### Business Detail

| Element | Classification | Notes |
|---|---|---|
| Business name/category/URL | `keep user-facing` | Kept |
| Provider/model metadata | `move to Advanced details` | Not shown in main list |

### Drafts / Content Library

| Element | Classification | Notes |
|---|---|---|
| Full library listing | `move to secondary area` | Now in collapsible "Drafts & Library" drawer |
| Provider/model filter | `move to Advanced details` | Removed from default filters |
| Date filter | `keep user-facing` | Kept |
| Status filter | `keep user-facing` | Kept |

### Scheduler / Calendar

| Element | Classification | Notes |
|---|---|---|
| Calendar view | `keep user-facing` | Kept |
| Schedule from content | `keep user-facing` | Schedule button on each content card |

### Integrations

| Element | Classification | Notes |
|---|---|---|
| Provider keys | `keep — Integrations/Diagnostics` | Correct location |
| Test buttons | `keep — Integrations/Diagnostics` | Correct location |

### Media Assets

| Element | Classification | Notes |
|---|---|---|
| Pixabay search | `keep user-facing` | Exposed via content card — Find Assets |
| Media job IDs | `move to Advanced details` | Hidden in accordion |

---

## Missing Flows Identified

| Flow | Status |
|---|---|
| Ad campaign structured output | ✅ Added in content_quality_gate.py |
| Short video / Reel scene-by-scene script | ✅ Added in content_quality_gate.py |
| YouTube Kit (title, description, outline, chapters) | ✅ Added in content_quality_gate.py |
| Talking Avatar (script, persona, delivery notes) | ✅ Added in content_quality_gate.py |
| Image Creative Set (3 concepts, Pixabay suggestions) | ✅ Added in content_quality_gate.py |
| Voiceover (script, duration, TTS note) | ✅ Added in content_quality_gate.py |
| Campaign angle variation engine | ✅ Added in campaign_angle_engine.py |
| Schedule from content card | ✅ Schedule button on each content card |
| Pixabay attach/save to content item | 🔄 UI placeholder — backend exists |
| Provider readiness banner | ✅ Added to ContentStudio header |

---

## Reasons Content Felt Bland / Repetitive

1. **No angle engine** — Every regeneration could produce the same structural approach.
2. **No hook differentiation** — No hook_style selector per generation.
3. **No objective-driven angle selection** — Content ignored campaign objective for variation.
4. **Hashtags too generic** — Old strategy used business name tokens only, could include #AIContent.
5. **No structured output types** — Ad, video, avatar outputs were all just `caption` with no structure.
6. **No duplicate detection** — Regenerate could produce nearly identical content without flagging.

All six issues are now addressed in campaign_angle_engine.py and the updated hashtag_strategy.py.
