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

## Still limited
- [ ] Full autonomous publisher worker is configured and verified live
- [ ] Drag/drop scheduler UX
- [ ] End-to-end verified live execution of every advanced multimodal provider path
- [ ] Full campaign-pack bulk scheduling API
- [ ] OAuth scopes verified and live posting tested per platform
- [ ] Frontend build (requires node_modules install in deployment env)

## Current verdict
- GO-LIVE: LIMITED — all backend routes and logic complete; live provider execution depends on API keys and OAuth config in deployment

- [ ] FULL_AUTONOMY_READY depends on live provider/model validity, OAuth scopes, and worker runtime in deployment.

## No Builder Changes ✅
