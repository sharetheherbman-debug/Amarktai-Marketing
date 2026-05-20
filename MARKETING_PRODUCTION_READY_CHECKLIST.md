# Marketing Production Ready Checklist

**Updated:** 2026-05-20 (post-PR-#14 stabilisation)

## Core Platform (All Maintained ✅)
- [x] Login, Add Business, webapps list/create/get/update remain active.
- [x] Business deletion now requires explicit confirmation and performs owned-only cleanup.
- [x] Smoke/test business cleanup endpoint added for current user only.
- [x] Firecrawl scrape/analyze and integrations/platform readiness remain available.
- [x] Existing `/api/v1/content/generate` and `/api/v1/content/generate-all` still work in limited mode.
- [x] Provider truth endpoints used as source of UI/runtime truth:
  - `/api/v1/settings/provider-resolution`
  - `/api/v1/settings/readiness`
  - `/api/v1/settings/api-keys/test`
  - `/api/v1/settings/genx/debug-test`
  - `/api/v1/settings/firecrawl/debug-test`
- [x] GenX models/capabilities endpoints:
  - `/api/v1/settings/genx/models`
  - `/api/v1/settings/genx/capabilities`
- [x] Hugging Face task router endpoints:
  - `/api/v1/settings/huggingface/tasks`
  - `/api/v1/settings/huggingface/test-task`
- [x] Unified capabilities endpoint:
  - `/api/v1/capabilities`
- [x] Platform intelligence endpoints:
  - `/api/v1/platform-intelligence`
  - `/api/v1/platform-intelligence/{platform}`
  - `/api/v1/platform-intelligence/review-content`
- [x] Creative multimodal endpoints:
  - `/api/v1/content/generate-creative`
  - `/api/v1/content/generate-pack`
- [x] Agent status endpoint:
  - `/api/v1/agents/status`
- [x] Learning endpoints:
  - `/api/v1/learning/run-now`
  - `/api/v1/learning/status`
  - `/api/v1/learning/insights`
  - `/api/v1/learning/insights/{webapp_id}`
- [x] Autonomous campaign endpoints:
  - `/api/v1/autonomous/start-campaign`
  - `/api/v1/autonomous/campaigns`
  - `/api/v1/autonomous/campaigns/{id}`
- [x] Frontend build passes.
- [x] Backend import/compile passes.

## Stability Fixes (PR-#14+ ✅)
- [x] AuthProvider only logs out on 401 — NOT on 500/network errors
- [x] Each dashboard boot call isolated (businesses, readiness, content, library)
- [x] ErrorBoundary on dashboard layout and content page
- [x] Content library: each bad row caught individually, never 500s
- [x] Rejection is a safe state transition (`POST /content/items/{id}/reject`)

## Content Provenance (✅)
- [x] `source_route`, `source_action`, `business_name`, `source_business_snapshot` on every item
- [x] `GET /api/v1/content/provenance` endpoint
- [x] Content library UI shows provenance on each card

## Business Grounding (✅)
- [x] AI provider system prompt: business-specific, no Amarktai mention
- [x] Generation prompts include category, products, audience, location, brand voice
- [x] Banned hashtag filter: #Amarktai, #AmarktaiMarketing, #AIContent
- [x] `creative_brief_builder.py` with industry visual rules

## Creative Relevance (✅)
- [x] `build_image_prompt()` and `build_video_brief()` — grounded, with negative prompts
- [x] `score_creative_relevance()` — heuristic scorer
- [x] `POST /content/items/{id}/review-grounding` endpoint

## Remaining for Full Autonomous Go-Live

| Item | Priority |
|---|---|
| Dashboard capability status panel (GenX video/voice/avatar) | P1 |
| Content Studio format options tied to capability discovery | P1 |
| Cleanup endpoint for smoke/test content | P2 |
| Item detail modal | P2 |
| Auto-regenerate when grounding score < 70 | P2 |
| scripts/test_business_grounding_quality.sh | P2 |
| scripts/test_provider_capability_truth.sh | P2 |
| MARKETING_PROVIDER_CAPABILITY_MATRIX.md | P3 |

- [ ] FULL_AUTONOMY_READY depends on live provider/model validity, OAuth scopes, and worker runtime in deployment.

## No Builder Changes ✅

