# MARKETING_REPO_SINGLE_SOURCE_OF_TRUTH_AUDIT
- what was fixed: deduplicated `backend/requirements.txt`, added the new authoritative go-live checklist/setup guide pair, and consolidated runtime content generation around the orchestrator instead of split preview/generate code paths.
- what remains deferred: older audit/checklist documents still exist for historical context and should be archived or pruned in a follow-up cleanup.
- exact tests run: `python3 -m compileall backend`; `cd app && npm ci && npm run build`.
- pass/fail: pass.
- launch status: single-source runtime improvements are in place; repository document cleanup is partially deferred.
