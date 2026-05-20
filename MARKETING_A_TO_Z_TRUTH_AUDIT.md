# AmarktAI Marketing — A-to-Z Truth Audit

**Date**: 2025-07-27  
**Status**: Production Recovery Audit

---

## 1. Frontend Routes (app/src)

| Route | Page | Protected |
|-------|------|-----------|
| `/` | Landing page | No |
| `/about` | About page | No |
| `/pricing` | Pricing page | No |
| `/contact` | Contact page | No |
| `/features` | Features page | No |
| `/privacy` | Privacy policy | No |
| `/terms` | Terms of service | No |
| `/login` | Login page | Public-only |
| `/register` | Register page | Public-only |
| `/forgot-password` | Forgot password | Public-only |
| `/reset-password` | Reset password | No |
| `/verify-email` | Email verification | No |
| `/dashboard` | Dashboard home | Protected |
| `/dashboard/businesses` | Business list (WebApps) | Protected |
| `/dashboard/businesses/new` | Add business | Protected |
| `/dashboard/businesses/:id` | Business detail | Protected |
| `/dashboard/webapps` | Redirect to businesses | Protected |
| `/dashboard/content` | Content Studio | Protected |
| `/dashboard/approval` | Content approval | Protected |
| `/dashboard/scheduler` | Scheduler/Calendar | Protected |
| `/dashboard/analytics` | Analytics | Protected |
| `/dashboard/settings` | Settings | Protected |
| `/dashboard/integrations` | Integrations | Protected |
| `/dashboard/engagement` | Engagement | Protected |
| `/dashboard/tools` | Power Tools | Protected |
| `/dashboard/leads` | Leads | Protected |
| `/dashboard/groups` | Groups | Protected |
| `/dashboard/blog` | SEO Blog | Protected |
| `/dashboard/admin` | Admin panel | Protected |

---

## 2. Backend Endpoints (backend/app/api)

### Auth
- POST /api/v1/auth/login
- POST /api/v1/auth/register
- POST /api/v1/auth/logout
- POST /api/v1/auth/refresh
- POST /api/v1/auth/forgot-password
- POST /api/v1/auth/reset-password

### Users
- GET /api/v1/users/me
- PUT /api/v1/users/me

### WebApps (Businesses)
- GET /api/v1/webapps
- POST /api/v1/webapps
- GET /api/v1/webapps/{id}
- PUT /api/v1/webapps/{id}
- DELETE /api/v1/webapps/{id}

### Content
- GET /api/v1/content
- POST /api/v1/content/generate
- GET /api/v1/content/{id}
- PUT /api/v1/content/{id}
- DELETE /api/v1/content/{id}
- POST /api/v1/content/{id}/approve
- POST /api/v1/content/{id}/reject
- GET /api/v1/content/library

### Scheduler
- GET /api/v1/scheduler/items
- POST /api/v1/scheduler/items
- GET /api/v1/scheduler/items/{id}
- PUT /api/v1/scheduler/items/{id}
- DELETE /api/v1/scheduler/items/{id}
- POST /api/v1/scheduler/items/{id}/mark-posted
- POST /api/v1/scheduler/items/{id}/mark-failed
- POST /api/v1/scheduler/items/{id}/reschedule
- GET /api/v1/scheduler/calendar
- POST /api/v1/scheduler/schedule
- GET /api/v1/scheduler/upcoming

### Integrations
- GET /api/v1/integrations/api-keys
- POST /api/v1/integrations/api-keys
- DELETE /api/v1/integrations/api-keys/{id}
- GET /api/v1/integrations/platforms
- GET /api/v1/integrations/platforms/{platform}/connect

### Platform Intelligence
- GET /api/v1/platform-intelligence

### Capabilities
- GET /api/v1/capabilities
- POST /api/v1/capabilities/route

### Media
- GET /api/v1/media/jobs
- GET /api/v1/media/jobs/{id}
- POST /api/v1/media/jobs/{id}/refresh
- POST /api/v1/media/jobs/{id}/cancel
- GET /api/v1/media/assets
- GET /api/v1/media/assets/{id}

### Settings
- GET /api/v1/settings/preferences
- PUT /api/v1/settings/preferences
- GET /api/v1/settings/readiness
- POST /api/v1/settings/api-key
- POST /api/v1/settings/test-genx
- POST /api/v1/settings/test-firecrawl
- GET /api/v1/settings/genx/models
- GET /api/v1/settings/genx/capabilities
- GET /api/v1/settings/genx/model-mapping
- PUT /api/v1/settings/genx/model-mapping
- POST /api/v1/settings/genx/test-capability
- GET /api/v1/settings/genx/credits
- GET /api/v1/settings/genx/pricing
- GET /api/v1/settings/qwen/models
- GET /api/v1/settings/qwen/capabilities
- POST /api/v1/settings/qwen/test-capability

### Workers
- GET /api/v1/workers/status

### Learning
- GET /api/v1/learning/status
- POST /api/v1/learning/run
- GET /api/v1/learning/insights

### Agents
- GET /api/v1/agents/status
- POST /api/v1/agents/run

### Autonomous
- POST /api/v1/autonomous/campaign-plan
- POST /api/v1/autonomous/start-campaign
- GET /api/v1/autonomous/campaigns
- GET /api/v1/autonomous/campaigns/{id}

---

## 3. Supported Platforms (All 12)

| Platform | Label | Generation | Posting | Analytics | OAuth |
|----------|-------|------------|---------|-----------|-------|
| instagram | Instagram | ✅ | Config-dependent | ✅ | Meta App |
| facebook | Facebook | ✅ | Config-dependent | ✅ | Meta App |
| linkedin | LinkedIn | ✅ | Config-dependent | ✅ | LinkedIn App |
| twitter | X / Twitter | ✅ | Config-dependent | ✅ | Twitter App |
| tiktok | TikTok | ✅ | Config-dependent | ✅ | TikTok App |
| youtube | YouTube | ✅ | Config-dependent | ✅ | Google App |
| reddit | Reddit | ✅ | Config-dependent | ✅ | Reddit App |
| pinterest | Pinterest | ✅ | Config-dependent | ✅ | Pinterest App |
| threads | Threads | ✅ | Config-dependent | ❌ | Meta App |
| bluesky | Bluesky | ✅ | Config-dependent | ❌ | Bluesky ID |
| telegram | Telegram | ✅ | Config-dependent | ❌ | Bot Token |
| snapchat | Snapchat | ✅ | Config-dependent | ❌ | Snapchat App |

---

## 4. Scheduler Implementation

**Model**: `SchedulerItem` in `backend/app/models/marketing_runtime.py`

**Fields**: id, user_id, business_id, content_id, platform, title, planned_at, status, posting_readiness, mode, notes, metadata_json, created_at, updated_at

**Status Values**: draft, scheduled, posted, failed, manual_review (via SchedulerStatus enum)

**Mode Values**: manual, auto (via SchedulerMode enum)

**Service**: `backend/app/services/scheduler_runtime.py` — upsert_scheduler_item, scheduler_item_payload, parse_iso_datetime

---

## 5. Provider Flow

```
Request → ProviderDecisionEngine.decide_provider()
  → capability + platform + format + budget_mode
  → Check provider keys (genx, qwen, huggingface)
  → Route: GenX (premium/multimodal) → Qwen (budget) → HF (fallback) → Template
```

**Files**: `provider_decision_engine.py`, `qwen_router.py`, `qwen_model_catalog.py`, `genx_router_client.py`

---

## 6. Content Generation Flow

```
POST /api/v1/content/generate
  → Load webapp/business data
  → Build business grounding context (business_grounding.py)
  → Build creative brief (creative_brief_builder.py)
  → Route to provider (provider_decision_engine.py)
  → Generate via AIProvider (ai_provider.py)
  → Apply quality gate (content_quality_gate.py)
  → Score business grounding (business_grounding.py)
  → Score hashtag relevance (hashtag_strategy.py)
  → If score < 70 → mark needs_review
  → Persist to content table
  → Return content with metadata
```

---

## 7. Content Persistence/Library Flow

- Content persisted to `content` table
- Library: GET /api/v1/content with filters
- Status lifecycle: pending → approved/rejected → scheduled → posted
- Rejection lifecycle: rejected status preserved, rejection_reason stored
- Content provenance: generation_metadata JSON field tracks provider/model/prompt

---

## 8. Media Generation Flow

```
MediaJob created → external_job_id from GenX/Qwen
  → Background polling via workers
  → Status: queued → running → completed/failed
  → On completion: MediaAsset created with result_url
  → Asset linked to content via content_id
```

**Models**: MediaJob, MediaAsset in `marketing_runtime.py`
**Endpoints**: `/api/v1/media/jobs`, `/api/v1/media/assets`

---

## 9. Learning Flow

```
LearningRun created → analyze Content + Analytics rows
  → Score platform performance
  → Generate what_worked / what_failed / recommendations
  → Persist LearningInsight per platform
  → Update BusinessPlatformPreference
  → Return insights for next-day planning
```

---

## 10. Worker/Background Job Flow

```
Celery workers (via celery_app.py):
  - scheduler_publisher: auto-post scheduled content
  - daily_learning: run learning loop daily
  - media_polling: poll GenX/Qwen job status
  - retry_queue: retry failed jobs
```

**Status**: GET /api/v1/workers/status

---

## 11. Placeholder/Fake Modules

| Module | Status | Notes |
|--------|--------|-------|
| genx_router_client.py | Partial | Missing poll, cancel, credits, pricing |
| qwen_model_catalog.py | Partial | Missing full model metadata |
| provider_decision_engine.py | Partial | Missing budget_tier, cost hints |
| smart_scheduler.py | Placeholder | Needs real calendar logic |
| media_generation.py avatar | Placeholder | HF text-to-video not available |

---

## 12. Files to Repair

1. `backend/app/services/genx_router_client.py` — add async polling, cancel, credits, pricing
2. `backend/app/services/qwen_model_catalog.py` — add full model metadata
3. `backend/app/services/provider_decision_engine.py` — add budget_tier, cost_hint, risk_notes
4. `backend/app/api/v1/endpoints/scheduler.py` — add reschedule endpoint
5. `backend/app/api/v1/endpoints/agents.py` — add /run endpoint
6. `backend/app/api/v1/endpoints/workers.py` — add retry_queue worker
7. `backend/app/api/v1/endpoints/settings.py` — add genx/qwen sub-routes
8. `app/src/components/dashboard/ContentStudio.tsx` — add all 12 platforms + 14 sections
