# Marketing Production Ready Checklist

- [x] Add Business flow supports name-only, url-only, and name+url.
- [x] Bare domains normalize to `https://`.
- [x] `/api/v1/webapps/` list/create/get/update endpoints return safe serialized JSON and avoid legacy-row serialization crashes.
- [x] Webapp creation preserves business creation even when website scraping fails.
- [x] `/api/v1/integrations/platforms` returns launch-platform readiness payload without 500s.
- [x] Integrations UI only enables OAuth connect when OAuth is configured and posting is supported.
- [x] Provider key test and debug endpoints return actionable, non-secret JSON and avoid 500s.
- [x] Integrations page shows Save / Test / Debug and visible last-result panels.
- [x] User-facing dashboard/settings copy removes beta wording.
- [x] Scheduler page shows real scheduled content or a truthful empty state.
- [x] Scheduler page shows a production-safe banner when automatic publishing is not configured.
- [x] VPS runtime permissions script fixes repo ownership/mode before deploy reset.
- [x] Deploy docs include running permission fix before git fetch/reset.
- [x] Gate script now reports endpoint failures with response body and final verdict.
- [ ] Remaining blocker: GenX provider still failing in runtime (if provider test fails in environment).
- [ ] Remaining blocker: Firecrawl provider still failing in runtime (if provider test fails in environment).
- [ ] Remaining blocker: OAuth app credentials not configured for posting.
- [ ] Remaining blocker: automatic posting worker/runtime not configured.
