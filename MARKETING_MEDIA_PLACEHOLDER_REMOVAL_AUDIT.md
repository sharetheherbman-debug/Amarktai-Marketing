# MARKETING_MEDIA_PLACEHOLDER_REMOVAL_AUDIT
- what was fixed: production media helpers no longer return Picsum or generic stock placeholders unless `ENABLE_DEMO_MEDIA=true`; preview/save tests assert no placeholder URLs leak in production responses.
- what remains deferred: demo-media behavior remains available only behind the explicit feature flag for non-production demonstrations.
- exact tests run: `python3 -m unittest discover -s backend/tests -p 'test_*.py'`; `cd app && npm run build`.
- pass/fail: pass.
- launch status: production placeholder leakage is blocked in covered content flows.
