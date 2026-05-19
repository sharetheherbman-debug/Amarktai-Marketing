#!/usr/bin/env bash
set -euo pipefail

PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://marketing.amarktai.com}"
API_BASE_URL="${API_BASE_URL:-https://marketing.amarktai.com/api/v1}"
EMAIL="${MARKETING_TEST_EMAIL:-}"
PASSWORD="${MARKETING_TEST_PASSWORD:-}"

pass(){ echo "PASS: $1"; }
fail(){ echo "FAIL: $1"; exit 1; }

curl -fsSI "$PUBLIC_BASE_URL/" >/dev/null && pass "frontend loads" || fail "frontend loads"
curl -fsS "$PUBLIC_BASE_URL/health" >/dev/null && pass "/health" || fail "/health"
curl -fsS "$API_BASE_URL/health" >/dev/null && pass "/api/v1/health" || fail "/api/v1/health"

if [[ -n "$EMAIL" && -n "$PASSWORD" ]]; then
  LOGIN_JSON=$(curl -fsS -X POST "$API_BASE_URL/auth/login" -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}") || fail "login"
  TOKEN=$(python3 - <<'PY' "$LOGIN_JSON"
import json,sys
print(json.loads(sys.argv[1]).get('access_token',''))
PY
)
  [[ -n "$TOKEN" ]] || fail "token from login"
  pass "login"

  curl -fsS "$API_BASE_URL/dashboard/stats" -H "Authorization: Bearer $TOKEN" >/dev/null && pass "dashboard protected route" || fail "dashboard protected route"

  WEBAPP_JSON=$(curl -fsS -X POST "$API_BASE_URL/webapps/" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"name":"GoLive Smoke","url":"https://example.com","description":"Smoke","category":"saas","target_audience":"buyers","key_features":["speed"],"is_active":true}') || fail "create webapp/business profile"
  WEBAPP_ID=$(python3 - <<'PY' "$WEBAPP_JSON"
import json,sys
print(json.loads(sys.argv[1]).get('id',''))
PY
)
  [[ -n "$WEBAPP_ID" ]] || fail "webapp id"
  pass "create/load webapp business profile"

  GEN_JSON=$(curl -fsS -X POST "$API_BASE_URL/content/generate?webapp_id=$WEBAPP_ID&platform=instagram" -H "Authorization: Bearer $TOKEN") || fail "content generate"
  STATUS=$(python3 - <<'PY' "$GEN_JSON"
import json,sys
print((json.loads(sys.argv[1]).get('generation_metadata') or {}).get('generation_status',''))
PY
)
  if [[ -n "${GENX_API_KEY:-}" ]]; then
    [[ "$STATUS" == "configured" ]] && pass "content generation configured" || fail "content generation configured"
  else
    [[ "$STATUS" == "not_configured" ]] && pass "content generation gracefully not_configured" || fail "content generation gracefully not_configured"
  fi

  curl -fsS "$API_BASE_URL/settings/readiness" -H "Authorization: Bearer $TOKEN" >/dev/null && pass "integrations/settings readiness" || fail "integrations/settings readiness"
  curl -fsS "$API_BASE_URL/analytics/summary" -H "Authorization: Bearer $TOKEN" >/dev/null && pass "analytics page data" || fail "analytics page data"
  curl -fsSI "$PUBLIC_BASE_URL/dashboard/groups" >/dev/null && pass "groups disabled route safe" || fail "groups disabled route safe"
else
  echo "SKIP: authenticated checks (set MARKETING_TEST_EMAIL and MARKETING_TEST_PASSWORD)"
fi

if grep -R "builder.amarktai.com" -n /home/runner/work/Amarktai-Marketing/Amarktai-Marketing/DEPLOYMENT_GUIDE.md /home/runner/work/Amarktai-Marketing/Amarktai-Marketing/DEPLOY_CHECKLIST.md /home/runner/work/Amarktai-Marketing/Amarktai-Marketing/deploy >/dev/null; then
  fail "builder.amarktai.com references remain in production deploy docs/config"
else
  pass "no builder.amarktai.com references in production deploy docs/config"
fi

echo "Go-live smoke checks complete."
