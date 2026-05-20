# Marketing Production Ready Checklist

## Restored now
- [x] Login/auth flow preserved
- [x] Add Business flow preserved
- [x] Delete Business flow preserved with related cleanup
- [x] Webapps list/create/delete routes preserved
- [x] Firecrawl scrape/analyze preserved
- [x] Content library and provenance preserved
- [x] Content rejection lifecycle preserved
- [x] Backend import/compile passes (`python3 -m compileall backend`)
- [x] 12-platform source of truth restored
- [x] Integrations UI shows all 12 platforms with action_label and analytics_supported
- [x] Content Studio selectors expose all 12 platforms with offer/product field
- [x] Business detail quick actions now expose all 12 platforms
- [x] Real scheduler items API restored
- [x] Scheduler UI restored with month/week/day/list planning modes
- [x] Scheduling from content items now creates persisted scheduler records
- [x] Reschedule endpoint added (`POST /api/v1/scheduler/items/{id}/reschedule`)
- [x] Dashboard now shows upcoming scheduled content from real scheduler data
- [x] Business grounding, hashtag strategy, and quality gate services added
- [x] hashtag_relevance_score present in hashtag strategy output
- [x] Provider decision endpoint restored (`POST /api/v1/capabilities/route`)
- [x] ProviderDecisionEngine returns full decision dict: provider, model, fallback_chain, budget_tier, expected_output_type, can_generate_asset, estimated_cost_hint, risk_notes
- [x] Qwen full catalog (43 models, 6 categories) with metadata added
- [x] GenX async router client with 11 methods added
- [x] GenX sub-routes in settings (7 endpoints) added
- [x] Qwen sub-routes in settings (3 endpoints) added
- [x] Persistent learning tables and API-backed service restored
- [x] Media jobs/assets tables and endpoints verified
- [x] Worker status endpoint covers all 4 workers including retry_queue
- [x] Agents status endpoint lists all 11 agents
- [x] Agents run endpoint added (`POST /api/v1/agents/run`)
- [x] Schema repair script updated for new runtime tables
- [x] Production flow gate script covers workers, agents, all platform tests

## Hotfix — Recovery Gates (PR: hotfix-production-recovery)

### Phase 1 — Offer/product_focus patch (persisted)
- [x] `app/src/lib/api.ts`: `contentApi.generate` accepts `offer?`
- [x] `app/src/lib/api.ts`: `contentApi.generateCreative` accepts `offer?`, `productFocus?`
- [x] `app/src/lib/api.ts`: `contentApi.generatePack` accepts `offer?`, `productFocus?`
- [x] `app/src/lib/api.ts`: `contentApi.improveItem` accepts `offer?`, `productFocus?`
- [x] Backend `GenerateCreativeRequest` and `GeneratePackRequest` accept `offer`, `product_focus`
- [x] Backend `ImproveContentRequest` accepts `offer`, `product_focus`
- [x] Backend `/content/generate` query accepts `offer` param
- [x] Frontend build: `npm run build` passes ✓
- [x] Backend compile: `python3 -m compileall backend` passes ✓

### Phase 2–3 — Shared helpers
- [x] `scripts/lib/auth.sh`: email-only login, TOKEN export, no random register
- [x] `scripts/lib/http.sh`: `api_call`, `assert_json_2xx`, `print_fail` — no JSONDecodeError

### Phase 4 — Core endpoint smoke
- [x] `scripts/test_core_endpoint_smoke.sh`: 11 endpoints checked, PASS/FAIL/NO_GO

### Phase 5 — Repaired gate scripts
- [x] `scripts/test_login_after_content_rejection.sh` — uses lib helpers, email login
- [x] `scripts/test_generated_content_visibility.sh` — uses lib helpers, email login
- [x] `scripts/test_12_platform_pack.sh` — uses lib helpers, email login
- [x] `scripts/test_scheduler_calendar_flow.sh` — uses lib helpers, email login
- [x] `scripts/test_provider_router_flow.sh` — uses lib helpers, email login
- [x] `scripts/test_business_grounding_quality.sh` — uses lib helpers, email login
- [x] `scripts/test_final_production_flow.sh` — REPO_ROOT resolved, uses lib helpers

### Phase 6 — Provider key diagnostics
- [x] `GET /api/v1/settings/provider-resolution`: now returns `key_name`, `decrypt_ok`, `configured`, `last_test_status`, `last_test_error`
- [x] `GET /api/v1/settings/providers/debug`: new endpoint with per-provider truth

### Phase 7 — Provider smoke
- [x] `scripts/test_provider_key_truth.sh`: resolution, debug, genx/qwen/hf endpoints

### Auth contract
- Login endpoint: `POST /api/v1/auth/login`
- Payload: `{"email": "...", "password": "..."}`
- Response: `{"access_token": "..."}`
- **Never use username login** — returns 422
- Random user registration disabled by default in all gate scripts


- [ ] Full autonomous publisher worker is configured and verified live
- [ ] Drag/drop scheduler UX
- [ ] End-to-end verified live execution of every advanced multimodal provider path
- [ ] Full campaign-pack bulk scheduling API
- [ ] OAuth scopes verified and live posting tested per platform
- [ ] Frontend build (requires node_modules install in deployment env)

## Current verdict
- GO-LIVE: LIMITED — all backend routes and logic complete; live provider execution depends on API keys and OAuth config in deployment

- [ ] FULL_AUTONOMY_READY depends on live provider/model validity, OAuth scopes, and worker runtime in deployment.

## Production truth reset + Pixabay phase
- [x] Provider/platform truth tightened to prevent false connected states
- [x] User-scoped reset endpoints for keys, integrations, provider state, and launch state
- [x] Provider diagnostics expanded (resolution + debug payload now include next-action fields)
- [x] Firecrawl test flow now supports real business URL / `no_test_url` behavior
- [x] Content preview and regenerate endpoints added with variation metadata
- [x] Pixabay status/test/search endpoints added, plus truthful unsupported-category responses
- [x] Media asset save/attach/delete endpoints added
- [x] Tooling status endpoint added at `GET /api/v1/media/tooling/status`
- [x] New gate scripts added for reset/platform-truth/preview-regeneration/pixabay

## No Builder Changes ✅
