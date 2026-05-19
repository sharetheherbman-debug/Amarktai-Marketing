#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:5173}"
EMAIL="${MARKETING_TEST_EMAIL:-}" 
PASSWORD="${MARKETING_TEST_PASSWORD:-}"

pass(){ echo "PASS: $1"; }
fail(){ echo "FAIL: $1"; exit 1; }

curl -fsS "$BASE_URL/health" >/dev/null && pass "backend /health" || fail "backend /health"
curl -fsS "$BASE_URL/api/v1/health" >/dev/null && pass "backend /api/v1/health" || fail "backend /api/v1/health"
curl -fsSI "$FRONTEND_URL/" >/dev/null && pass "frontend loads" || fail "frontend loads"

if [[ -n "$EMAIL" && -n "$PASSWORD" ]]; then
  LOGIN_JSON=$(curl -fsS -X POST "$BASE_URL/api/v1/auth/login" -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}") || fail "login"
  TOKEN=$(python3 - <<'PY' "$LOGIN_JSON"
import json,sys
print(json.loads(sys.argv[1]).get('access_token',''))
PY
)
  [[ -n "$TOKEN" ]] || fail "token from login"
  pass "login"

  curl -fsS "$BASE_URL/api/v1/dashboard/stats" -H "Authorization: Bearer $TOKEN" >/dev/null && pass "dashboard protected route" || fail "dashboard protected route"

  WEBAPP_JSON=$(curl -fsS -X POST "$BASE_URL/api/v1/webapps/" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"name":"Smoke App","url":"https://example.com","description":"Smoke","category":"saas","target_audience":"founders","key_features":["speed"],"is_active":true}') || fail "create webapp"
  WEBAPP_ID=$(python3 - <<'PY' "$WEBAPP_JSON"
import json,sys
print(json.loads(sys.argv[1]).get('id',''))
PY
)
  [[ -n "$WEBAPP_ID" ]] || fail "webapp id"
  pass "create webapp/business profile"

  curl -fsS "$BASE_URL/api/v1/webapps/$WEBAPP_ID" -H "Authorization: Bearer $TOKEN" >/dev/null && pass "load webapp/business profile" || fail "load webapp/business profile"

  GEN_JSON=$(curl -fsS -X POST "$BASE_URL/api/v1/content/generate?webapp_id=$WEBAPP_ID&platform=instagram" -H "Authorization: Bearer $TOKEN") || fail "generate content request"
  STATUS=$(python3 - <<'PY' "$GEN_JSON"
import json,sys
print((json.loads(sys.argv[1]).get('generation_metadata') or {}).get('generation_status',''))
PY
)
  if [[ -n "${GENX_API_KEY:-}" ]]; then
    [[ "$STATUS" == "configured" ]] && pass "generate content configured path" || fail "generate content configured path"
  else
    [[ "$STATUS" == "not_configured" ]] && pass "generate content not_configured path" || fail "generate content not_configured path"
  fi

  curl -fsS "$BASE_URL/api/v1/settings/readiness" -H "Authorization: Bearer $TOKEN" >/dev/null && pass "integrations/settings page api" || fail "integrations/settings page api"
  curl -fsS "$BASE_URL/api/v1/analytics/summary" -H "Authorization: Bearer $TOKEN" >/dev/null && pass "analytics page api" || fail "analytics page api"
  curl -fsSI "$FRONTEND_URL/dashboard/groups" >/dev/null && pass "groups disabled route safe" || fail "groups disabled route safe"
else
  echo "SKIP: login/webapp/content checks (set MARKETING_TEST_EMAIL and MARKETING_TEST_PASSWORD)"
fi

if grep -R "builder.amarktai.com" -n /home/runner/work/Amarktai-Marketing/Amarktai-Marketing/DEPLOYMENT_GUIDE.md /home/runner/work/Amarktai-Marketing/Amarktai-Marketing/DEPLOY_CHECKLIST.md /home/runner/work/Amarktai-Marketing/Amarktai-Marketing/deploy >/dev/null; then
  fail "builder.amarktai.com references remain in deploy docs/config"
else
  pass "no builder.amarktai.com references in production deploy docs/config"
fi

echo "Local marketing checks complete."
