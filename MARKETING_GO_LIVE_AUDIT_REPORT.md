# MARKETING_GO_LIVE_AUDIT_REPORT

## Tested commit

- Commit SHA: `d1193a7b8884bf7c6d72ea54d3d99ed1fcbd8532`

## Exact scripts/checks run in this audit session

1. `python -m compileall backend`
2. `cd app && npm run lint` *(baseline repo lint still fails on pre-existing frontend rules)*
3. `cd app && npm run build`
4. `python -m compileall backend` *(post-change)*
5. `cd app && npm run build` *(post-change)*

## New go-live gate scripts added

- `scripts/test_genx_models.sh`
- `scripts/test_autonomous_generation.sh`
- `scripts/test_scheduler_flow.sh`
- `scripts/test_posting_readiness.sh`
- `scripts/test_learning_loop.sh`
- `scripts/marketing_full_go_live_gate.sh`

## Pass/fail table (this session)

| Check | Status | Notes |
|---|---|---|
| Backend compile/import | PASS | `python -m compileall backend` succeeds |
| Frontend build | PASS | `npm run build` succeeds |
| Frontend lint | FAIL (pre-existing) | Existing repo-wide lint issues unrelated to this hardening pass |
| GenX model discovery endpoint | IMPLEMENTED | `/api/v1/settings/genx/models` |
| GenX per-model test endpoint | IMPLEMENTED | `/api/v1/settings/genx/test-models` |
| Readiness GenX hardening fields | IMPLEMENTED | `configured/health_ok/models_tested/required_models_ok/failed_models/last_checked_at` |
| Publishing readiness endpoints | IMPLEMENTED | `/api/v1/publishing/readiness`, `/test-platform`, `/post-now` |
| Scheduler endpoints | IMPLEMENTED | `/api/v1/scheduler/schedule`, `/upcoming` |
| Social rules endpoints | IMPLEMENTED | `/api/v1/social-rules`, `/api/v1/social-rules/{platform}` |
| Learning-status extended fields | IMPLEMENTED | includes mode/blockers/last/next run fields |
| Full authenticated smoke scripts | NOT EXECUTED IN SANDBOX | Require `MARKETING_TEST_EMAIL` + `MARKETING_TEST_PASSWORD` against a running target |

## GenX model status

- Required model health cannot be declared from repository-only static audit.
- Runtime verification now enforced through:
  - `POST /api/v1/settings/genx/test-models`
  - `scripts/test_genx_models.sh`
- Go-live readiness now marks `go_live_ready=false` when required GenX model checks are failing/missing.

## Providers configured (truth model)

- Provider readiness is now surfaced from `/api/v1/settings/readiness`.
- GenX readiness is no longer treated as simply “key exists”; it now includes runtime health + required-model checks.

## Social platforms posting truth

Per-platform readiness now exposes:

- `oauth_configured`
- `user_connected`
- `token_valid`
- `scopes_ok`
- `posting_supported`
- `analytics_supported`
- `rate_limit_known`
- `can_post_now`
- `missing`

Current implementation intentionally marks unsupported/incomplete live-posting paths as **posting not implemented** and blocks autonomous posting for those paths.

## Platform posting categories (truthful policy)

- **Can be ready for real posting when credentials + connection + token + scopes + target mapping are valid:** facebook, instagram, linkedin, reddit, pinterest
- **Generate/schedule-only or blocked for posting in current implementation:** twitter/x, tiktok, youtube (explicit “posting not implemented” guard in `/publishing/post-now`)

## Missing keys and blockers (runtime-dependent)

Typical blockers remain runtime/environment dependent until deployed secrets are present:

- `GENX_API_KEY` (and valid model configuration)
- OAuth app credentials per platform
- User OAuth connections/tokens/scopes
- Optional: `FIRECRAWL_API_KEY`, `RESEND_API_KEY`, Stripe keys/webhook

## Autonomous mode status

- Status model:
  - `enabled` only when required readiness gates pass
  - `blocked` when posting/approval gates are unmet
  - `degraded` when GenX is not configured/healthy
- This is now surfaced via generation metadata + readiness/publishing checks rather than optimistic assumptions.

## Final go/no-go verdict

**Conditional NO-GO for “All systems go” at this exact moment in this sandbox**.

Reason:

- Authenticated end-to-end gate scripts were not executable here without live credentials/runtime target.
- “All systems go” must only be declared after `scripts/marketing_full_go_live_gate.sh` passes with required production keys and integrations configured.

When those scripts pass on the live target with required keys, go-live can be promoted to **GO**.
