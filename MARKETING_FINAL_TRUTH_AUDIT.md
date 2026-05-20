# MARKETING FINAL TRUTH AUDIT

Generated from current repository truth before restoration work.

## 1. Dashboard routes and status

Source of truth: `/home/runner/work/Amarktai-Marketing/Amarktai-Marketing/app/src/App.tsx`, `/home/runner/work/Amarktai-Marketing/Amarktai-Marketing/app/src/components/layout/DashboardLayout.tsx`

| Route | File | Status | Notes |
| --- | --- | --- | --- |
| `/dashboard` | `app/src/app/dashboard/page.tsx` | implemented, incomplete | Guided flow exists, but it loads recent content instead of real scheduler-backed upcoming items and does not expose full production workflow. |
| `/dashboard/businesses` | `app/src/app/webapps/page.tsx` | implemented | Canonical business list route. |
| `/dashboard/businesses/new` | `app/src/app/webapps/new/page.tsx` | implemented | Add Business flow exists. |
| `/dashboard/businesses/:id` | `app/src/app/businesses/detail/page.tsx` | implemented, incomplete | Website analysis and generation actions exist, but quick actions only expose 4 platforms and no real scheduler handoff. |
| `/dashboard/webapps` | `app/src/App.tsx` redirect | duplicate | Redirects to `/dashboard/businesses`. |
| `/dashboard/webapps/new` | `app/src/App.tsx` redirect | duplicate | Redirects to `/dashboard/businesses/new`. |
| `/dashboard/webapps/edit/:id` | `app/src/app/webapps/edit/page.tsx` | implemented | Edit route kept under legacy path. |
| `/dashboard/webapps/:id` | `app/src/App.tsx` | duplicate | Duplicate detail route pointing to `BusinessDetailPage`. |
| `/dashboard/content` | `app/src/app/content/page.tsx` + `app/src/components/dashboard/ContentStudio.tsx` | implemented, broken/incomplete | Content Studio exists, but platform selector is limited to 8 and creation controls do not expose the full production suite. |
| `/dashboard/approval` | `app/src/app/approval/page.tsx` | implemented | Approval page exists. |
| `/dashboard/scheduler` | `app/src/app/scheduler/page.tsx` | broken/placeholder replacement | Current page only lists `/api/v1/scheduler/upcoming`; no month/week/day calendar, no CRUD, no filters, no real scheduler records. |
| `/dashboard/analytics` | `app/src/app/analytics/page.tsx` | implemented | Analytics page exists. |
| `/dashboard/settings` | `app/src/app/settings/page.tsx` | implemented | Settings page exists. |
| `/dashboard/integrations` | `app/src/app/integrations/page.tsx` | implemented, incomplete | Integrations page renders only 8 platform cards from local `socialPlatforms` constant. |
| `/dashboard/engagement` | `app/src/app/engagement/page.tsx` | implemented | Engagement page exists. |
| `/dashboard/tools` | `app/src/app/tools/page.tsx` | implemented | Tools page exists. |
| `/dashboard/leads` | `app/src/app/leads/page.tsx` | implemented | Leads page exists. |
| `/dashboard/groups` | `app/src/app/groups/page.tsx` | implemented | Groups page exists. |
| `/dashboard/blog` | `app/src/app/blog/page.tsx` | implemented | Blog page exists. |
| `/dashboard/admin` | `app/src/app/admin/page.tsx` | implemented | Admin page exists. |

### Hidden / unused dashboard-adjacent files

| File | Status | Notes |
| --- | --- | --- |
| `app/src/app/platforms/page.tsx` | hidden | Page file exists but no route is registered in `app/src/App.tsx`. |
| `app/src/app/businesses/detail/page.tsx` filesystem route | hidden by router indirection | Actual router uses `/dashboard/businesses/:id`, not `/dashboard/businesses/detail`. |
| `app/src/components/dashboard/ContentCalendar.tsx` | hidden/bypassed | Richer calendar UI component exists but is not used by `app/src/app/scheduler/page.tsx`. |
| `app/src/components/dashboard/SmartScheduler.tsx` | hidden/bypassed | Richer scheduler/heatmap component exists but is not used by the live scheduler page. |

## 2. Backend endpoint inventory and status

Source of truth: `/home/runner/work/Amarktai-Marketing/Amarktai-Marketing/backend/app/api/v1/router.py` and endpoint modules under `backend/app/api/v1/endpoints`

### Auth
- Implemented:
  - `POST /api/v1/auth/register`
  - `POST /api/v1/auth/login`
  - `GET /api/v1/auth/me`
  - `POST /api/v1/auth/refresh`
  - `GET /api/v1/auth/verify-email`
  - `POST /api/v1/auth/forgot-password`
  - `POST /api/v1/auth/reset-password`

### Webapps / businesses
- Implemented:
  - `GET /api/v1/webapps/`
  - `GET /api/v1/webapps/{webapp_id}`
  - `POST /api/v1/webapps/`
  - `POST /api/v1/webapps/analyze`
  - `POST /api/v1/webapps/{webapp_id}/scrape`
  - `POST /api/v1/webapps/{webapp_id}/refresh-intelligence`
  - `PUT /api/v1/webapps/{webapp_id}`
  - `DELETE /api/v1/webapps/{webapp_id}`
  - `POST /api/v1/webapps/{webapp_id}/media`
  - `DELETE /api/v1/webapps/{webapp_id}/media/{asset_id}`
- Notes:
  - Firecrawl-backed business analysis is wired through `backend/app/services/business_intelligence.py` and `backend/app/services/scraper.py`.

### Content
- Implemented:
  - `GET /api/v1/content/`
  - `GET /api/v1/content/items`
  - `GET /api/v1/content/items/{content_id}`
  - `GET /api/v1/content/provenance`
  - `GET /api/v1/content/webapp/{webapp_id}`
  - `DELETE /api/v1/content/items/{content_id}`
  - `POST /api/v1/content/items/{content_id}/reject`
  - `POST /api/v1/content/items/{content_id}/schedule`
  - `POST /api/v1/content/items/{content_id}/duplicate`
  - `POST /api/v1/content/items/{content_id}/improve`
  - `POST /api/v1/content/items/{content_id}/review-grounding`
  - `GET /api/v1/content/pending`
  - `GET /api/v1/content/{content_id}`
  - `POST /api/v1/content/generate`
  - `POST /api/v1/content/generate-all`
  - `POST /api/v1/content/generate-creative`
  - `POST /api/v1/content/generate-pack`
  - `POST /api/v1/content/{content_id}/approve`
  - `POST /api/v1/content/{content_id}/reject`
  - `POST /api/v1/content/approve-all`
  - `PUT /api/v1/content/{content_id}`
- Broken/incomplete:
  - `generate-all` and `generate-pack` are limited by `backend/app/services/platform_catalog.py` to 8 launch platforms.
  - Scheduling currently mutates `content.scheduled_for` directly and does not create a separate scheduler record.

### Media
- Implemented:
  - Webapp media upload/delete only via `/api/v1/webapps/{webapp_id}/media`
- Missing:
  - `GET /api/v1/media/jobs`
  - `GET /api/v1/media/jobs/{id}`
  - `POST /api/v1/media/jobs/{id}/refresh`
  - `POST /api/v1/media/jobs/{id}/cancel`
  - `GET /api/v1/media/assets`
  - `GET /api/v1/media/assets/{id}`
- Current truth:
  - No `media_jobs` or `media_assets` table/model exists in `backend/app/models`.

### Scheduler / calendar
- Implemented:
  - `POST /api/v1/scheduler/schedule`
  - `GET /api/v1/scheduler/upcoming`
  - `GET /api/v1/dashboard/scheduler/heatmap`
  - `GET /api/v1/dashboard/scheduler/posts`
  - `GET /api/v1/dashboard/calendar`
- Broken/incomplete:
  - No CRUD endpoints for real scheduler items.
  - No scheduler table/model exists.
  - Dashboard calendar/scheduler endpoints are separate from the live scheduler page and are not the source of truth.

### Integrations / platforms
- Implemented:
  - `GET /api/v1/integrations/platforms`
  - `GET /api/v1/integrations/platforms/{platform}/connect`
  - `POST /api/v1/integrations/platforms/{platform}/disconnect`
  - `PATCH /api/v1/integrations/platforms/{platform}`
  - `GET|POST /api/v1/integrations/platforms/callback`
  - `GET /api/v1/platforms/`
  - `GET /api/v1/platforms/{platform}`
  - `GET /api/v1/platforms/{platform}/audit`
  - `POST /api/v1/platforms/{platform}/connect`
  - `POST /api/v1/platforms/{platform}/create-business-page`
  - `PATCH /api/v1/platforms/{platform}/budget`
  - `POST /api/v1/platforms/{platform}/disconnect`
- Broken/incomplete:
  - `GET /api/v1/integrations/platforms` only iterates `launch_platforms()` from `backend/app/services/platform_catalog.py`, currently 8.
  - Posting readiness only defines readiness maps for 8 platforms in `backend/app/services/posting_readiness.py`.

### Provider settings / capabilities
- Implemented:
  - `GET /api/v1/settings/genx/models`
  - `GET /api/v1/settings/genx/capabilities`
  - `POST /api/v1/settings/genx/test-models`
  - `POST /api/v1/settings/firecrawl/test`
  - `GET /api/v1/settings/readiness`
  - `GET /api/v1/settings/provider-resolution`
  - `POST /api/v1/settings/genx/debug-test`
  - `POST /api/v1/settings/firecrawl/debug-test`
  - `GET /api/v1/settings/huggingface/tasks`
  - `POST /api/v1/settings/huggingface/test-task`
  - `GET /api/v1/capabilities`
- Missing:
  - `POST /api/v1/capabilities/route`

### Agents
- Implemented:
  - `GET /api/v1/agents/status`

### Learning
- Implemented:
  - `POST /api/v1/learning/run-now`
  - `GET /api/v1/learning/status`
  - `GET /api/v1/learning/insights`
  - `GET /api/v1/learning/insights/{webapp_id}`
- Broken/incomplete:
  - `backend/app/services/learning_loop.py` is in-memory only and loses state on restart.

### Autonomous campaigns
- Implemented:
  - `POST /api/v1/autonomous/campaign-plan`
  - `POST /api/v1/autonomous/start-campaign`
  - `GET /api/v1/autonomous/campaigns`
  - `GET /api/v1/autonomous/campaigns/{campaign_id}`
  - `POST /api/v1/autonomous/batch-approve`
  - `POST /api/v1/autonomous/post/{content_id}`
  - `GET /api/v1/autonomous/queue-status`
  - `POST /api/v1/autonomous/sync-analytics`
  - `GET /api/v1/autonomous/best-posting-times`
  - `GET /api/v1/autonomous/morning-digest`
- Incomplete:
  - No persistent worker truth endpoint exists for scheduler/media/learning workers.

## 3. Supported social platforms currently in code

### 12-platform references already present somewhere in repo
- `instagram`
- `facebook`
- `linkedin`
- `twitter`
- `tiktok`
- `youtube`
- `reddit`
- `pinterest`
- `threads`
- `bluesky`
- `telegram`
- `snapchat`

Evidence:
- `app/src/types/index.ts`
- `backend/app/models/platform_connection.py`
- `backend/app/api/v1/endpoints/integrations.py` OAuth config map
- `backend/app/api/v1/endpoints/platforms.py`
- `app/src/lib/mockData.ts`

## 4. Platforms that should be supported

Required full set:
1. instagram
2. facebook
3. linkedin
4. twitter / x
5. tiktok
6. youtube
7. reddit
8. pinterest
9. threads
10. bluesky
11. telegram
12. snapchat

## 5. Missing platform coverage

Current missing from live 8-platform source of truth:
- threads
- bluesky
- telegram
- snapchat

Evidence:
- `backend/app/services/platform_catalog.py`
- `app/src/app/integrations/page.tsx`
- `app/src/components/dashboard/ContentStudio.tsx`
- `app/src/app/businesses/detail/page.tsx`
- `backend/app/services/posting_readiness.py`
- `backend/app/services/social_rules.py`
- `backend/app/services/platform_intelligence.py`

## 6. Current scheduler/calendar implementation and whether it is the correct original one

- Live scheduler page: `app/src/app/scheduler/page.tsx`
  - Current state: simplified upcoming list only.
  - Verdict: **not the correct production scheduler/calendar**.
- Backend scheduler API: `backend/app/api/v1/endpoints/scheduler.py`
  - Current state: only `POST /schedule` and `GET /upcoming`.
  - Verdict: **not a production scheduler API**.
- Dashboard calendar/scheduler data:
  - `backend/app/api/v1/endpoints/dashboard.py`
  - `app/src/components/dashboard/ContentCalendar.tsx`
  - `app/src/components/dashboard/SmartScheduler.tsx`
  - Verdict: richer but bypassed/fragmented and not the live source of truth.

## 7. Old/correct scheduler/calendar component/API removed or bypassed

- Bypassed frontend components:
  - `app/src/components/dashboard/ContentCalendar.tsx`
  - `app/src/components/dashboard/SmartScheduler.tsx`
- Bypassed dashboard APIs:
  - `GET /api/v1/dashboard/scheduler/heatmap`
  - `GET /api/v1/dashboard/scheduler/posts`
  - `GET /api/v1/dashboard/calendar`
- Current live page does not use them:
  - `app/src/app/scheduler/page.tsx`

## 8. Current content generation flow

### Where prompts are built
- Template fallback prompt:
  - `backend/app/api/v1/endpoints/content.py::_template_from_intelligence`
- HF/Qwen text prompt:
  - `backend/app/services/hf_generator.py::_build_prompt`
- Creative/media prompt builders:
  - `backend/app/services/creative_brief_builder.py`
  - `backend/app/services/media_generation.py`

### Where business data enters the prompt
- `backend/app/api/v1/endpoints/content.py::generate_content`
  - builds `webapp_data` from `WebApp` + `scraped_data`
- `backend/app/api/v1/endpoints/content.py::generate_creative`
  - builds `webapp_data` from `WebApp`

### Where platform rules enter the prompt
- `backend/app/services/social_rules.py::as_prompt_guidance`
- `backend/app/services/hf_generator.py` platform hint map
- `backend/app/services/platform_format_strategy.py`
- `backend/app/services/platform_intelligence.py::review_content`

### Where hashtags are created
- `backend/app/api/v1/endpoints/content.py::_template_from_intelligence`
- Provider-generated hashtag output parsed in `backend/app/services/hf_generator.py` / `backend/app/services/ai_provider.py`
- Filtering only, not strategy:
  - `backend/app/api/v1/endpoints/content.py::_filter_hashtags`

### Where media prompts are created
- `backend/app/services/creative_brief_builder.py`
- `backend/app/services/media_generation.py`

### Where content is persisted
- `backend/app/api/v1/endpoints/content.py::generate_content`
- `backend/app/api/v1/endpoints/content.py::generate_creative`
- `backend/app/models/content.py`

## 9. Current provider flow

### GenX
- Client:
  - `backend/app/services/genx_client.py`
- Routed by:
  - `backend/app/services/ai_provider.py`
- Current limitation:
  - Uses chat-completions path assumptions and task fallback list, not async multimodal job routing.

### Qwen
- Routed by:
  - `backend/app/services/ai_provider.py::_call_qwen`
- Current limitation:
  - Hardcoded text-only DashScope path and tiny model list (`qwen-turbo`, `qwen-plus`).

### Hugging Face
- Routed by:
  - `backend/app/services/hf_generator.py`
  - `backend/app/services/huggingface_task_router.py`
- Current limitation:
  - Capability usage is not centrally selected by a provider decision engine.

### Firecrawl
- Routed by:
  - `backend/app/services/business_intelligence.py`
  - `backend/app/services/scraper.py`
- Current state:
  - Present and used for business scraping/intelligence.

### Template fallback
- Routed by:
  - `backend/app/api/v1/endpoints/content.py::_template_from_intelligence`
  - `backend/app/services/hf_generator.py::_fallback_content`

## 10. Missing models/services

### Missing service modules
- `backend/app/services/business_grounding.py`
- `backend/app/services/hashtag_strategy.py`
- `backend/app/services/content_quality_gate.py`
- `backend/app/services/provider_decision_engine.py`
- `backend/app/services/genx_router_client.py`
- `backend/app/services/qwen_model_catalog.py`
- `backend/app/services/qwen_router.py`

### Missing tables/models or persistent layers
- `media_jobs`
- `media_assets`
- `learning_runs`
- `learning_insights`
- `business_platform_preferences`
- dedicated scheduler items table/model

### Missing worker/status API
- `GET /api/v1/workers/status`

## Immediate forensic conclusions

1. The repository already contains 12-platform awareness in several places, but the live backend and frontend source-of-truth path was reduced to 8 by `backend/app/services/platform_catalog.py` and matching frontend constants.
2. The live scheduler page and scheduler API were replaced by a much weaker list-only flow and are not production-ready.
3. Content generation persistence and provenance exist, but business grounding, hashtag strategy, provider routing, and quality gates are incomplete.
4. Learning is not persistent.
5. Media jobs/assets are not implemented as real records.
