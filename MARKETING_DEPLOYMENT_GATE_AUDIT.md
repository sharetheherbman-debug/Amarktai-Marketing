# Marketing Deployment Gate Audit

## Auth Contract

| Field | Value |
|-------|-------|
| Endpoint | `POST /api/v1/auth/login` |
| Payload | `{"email": "...", "password": "..."}` |
| Success | 200 + `{"access_token": "..."}` |
| Username login | ❌ Returns 422 — never use |
| Random registration | Disabled by default in all gate scripts |
| Env vars required | `MARKETING_TEST_EMAIL`, `MARKETING_TEST_PASSWORD` |

## Gate Scripts — Fixed

All scripts now:
1. Source `scripts/lib/auth.sh` and `scripts/lib/http.sh`
2. Use email-only login payload
3. Do not register random users (unless `ENABLE_TEST_REGISTRATION=true`)
4. Stop cleanly if login fails (print `NO_GO`)
5. Capture HTTP status and body for every curl
6. Parse JSON only after 2xx and non-empty body
7. Resolve `REPO_ROOT` from script path
8. Print `PASS`, `FAIL`, or `NO_GO`
9. No JSONDecodeError stack traces

| Script | Status | Notes |
|--------|--------|-------|
| `test_login_after_content_rejection.sh` | ✅ Fixed | Email login, lib helpers |
| `test_generated_content_visibility.sh` | ✅ Fixed | Email login, lib helpers |
| `test_12_platform_pack.sh` | ✅ Fixed | Email login, lib helpers |
| `test_scheduler_calendar_flow.sh` | ✅ Fixed | Email login, lib helpers |
| `test_provider_router_flow.sh` | ✅ Fixed | Email login, lib helpers |
| `test_business_grounding_quality.sh` | ✅ Fixed | Email login, lib helpers |
| `test_final_production_flow.sh` | ✅ Fixed | REPO_ROOT resolved, lib helpers |
| `test_core_endpoint_smoke.sh` | ✅ New | 11 endpoints, PASS/FAIL/NO_GO |
| `test_provider_key_truth.sh` | ✅ New | Provider truth + diagnostics |

## Core Endpoint Smoke — Expected Pass

```
/api/v1/integrations/platforms
/api/v1/platform-intelligence
/api/v1/capabilities
/api/v1/workers/status
/api/v1/agents/status
/api/v1/learning/status
/api/v1/media/jobs
/api/v1/media/assets
/api/v1/scheduler/items
/api/v1/settings/provider-resolution
/api/v1/settings/readiness
```

All confirmed returning 200 JSON in manual smoke (per problem statement).

## Shared Helpers

### `scripts/lib/auth.sh`
- Resolves `REPO_ROOT` automatically
- `BASE_URL` defaults to `http://127.0.0.1:8010`
- `do_login` — sets `TOKEN`, fails cleanly on error
- `do_register_test_user` — gated behind `ENABLE_TEST_REGISTRATION=true`

### `scripts/lib/http.sh`
- `api_call METHOD PATH [BODY]` — sets `_HTTP_STATUS` and `_HTTP_BODY`
- `assert_json_2xx METHOD PATH [BODY] [LABEL]` — fails if not 2xx or empty body
- `print_fail ENDPOINT STATUS BODY` — structured failure output
- Works without jq; uses jq when available

## Backend Compile

```bash
cd backend
./venv/bin/python -m compileall -q app
```

## Frontend Build

```bash
cd app
npm run build
```

Status: ✅ Passes after `npm ci`
