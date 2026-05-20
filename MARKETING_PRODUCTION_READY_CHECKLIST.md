# Marketing Production Ready Checklist

## Restored now
- [x] Login/auth flow preserved
- [x] Add Business flow preserved
- [x] Delete Business flow preserved with related cleanup
- [x] Webapps list/create/delete routes preserved
- [x] Firecrawl scrape/analyze preserved
- [x] Content library and provenance preserved
- [x] Content rejection lifecycle preserved
- [x] Frontend build passes (`cd app && npm run build`)
- [x] Backend import/compile passes (`python3 -m compileall backend`)
- [x] 12-platform source of truth restored
- [x] Integrations UI shows all 12 platforms truthfully
- [x] Content Studio selectors now expose all 12 platforms
- [x] Business detail quick actions now expose all 12 platforms
- [x] Real scheduler items API restored
- [x] Scheduler UI restored with month/week/day/list planning modes
- [x] Scheduling from content items now creates persisted scheduler records
- [x] Dashboard now shows upcoming scheduled content from real scheduler data
- [x] Business grounding, hashtag strategy, and quality gate services added
- [x] Provider decision endpoint restored (`POST /api/v1/capabilities/route`)
- [x] Qwen catalog and GenX router client modules added
- [x] Persistent learning tables and API-backed service restored
- [x] Media jobs/assets tables and endpoints added
- [x] Worker status endpoint added (`GET /api/v1/workers/status`)
- [x] Schema repair script updated for new runtime tables
- [x] New production flow scripts added

## Still limited
- [ ] Full autonomous publisher worker is configured and verified live
- [ ] Drag/drop scheduler UX
- [ ] End-to-end verified live execution of every advanced multimodal provider path
- [ ] Full campaign-pack bulk scheduling API
- [ ] All new smoke scripts executed against a running local or staging stack in this session

## Current verdict
- GO-LIVE: LIMITED

- [ ] FULL_AUTONOMY_READY depends on live provider/model validity, OAuth scopes, and worker runtime in deployment.

## No Builder Changes ✅
