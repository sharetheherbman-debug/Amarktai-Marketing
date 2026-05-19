#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
FRONTEND_URL="${FRONTEND_URL:-https://marketing.amarktai.com}"
EMAIL="${MARKETING_TEST_EMAIL:-}"
PASSWORD="${MARKETING_TEST_PASSWORD:-}"

pass(){ echo "PASS: $1"; }
warn(){ echo "WARN: $1"; }
fail(){ echo "FAIL: $1"; exit 1; }

[[ -d "$REPO_ROOT/backend/app" && -f "$REPO_ROOT/app/package.json" ]] || fail "REPO_ROOT must contain backend/app and app/package.json"

echo "Resolved REPO_ROOT: $REPO_ROOT"
echo "Using BASE_URL: $BASE_URL"
echo "Using FRONTEND_URL: ${FRONTEND_URL:-<unset>}"

curl -fsS "$BASE_URL/health" >/dev/null && pass "backend /health" || fail "backend /health"
curl -fsS "$BASE_URL/api/v1/health" >/dev/null && pass "backend /api/v1/health" || fail "backend /api/v1/health"
if [[ -n "${FRONTEND_URL:-}" ]]; then
  curl -fsSI "$FRONTEND_URL/" >/dev/null && pass "frontend loads" || fail "frontend loads"
else
  warn "frontend checks skipped because FRONTEND_URL is unset"
fi

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
  case "$STATUS" in
    configured)
      pass "generate content configured path"
      ;;
    not_configured)
      pass "generate content not_configured path"
      ;;
    *)
      fail "unexpected generate content status: ${STATUS:-<empty>}"
      ;;
  esac

  curl -fsS "$BASE_URL/api/v1/settings/readiness" -H "Authorization: Bearer $TOKEN" >/dev/null && pass "integrations/settings page api" || fail "integrations/settings page api"
  curl -fsS "$BASE_URL/api/v1/analytics/summary" -H "Authorization: Bearer $TOKEN" >/dev/null && pass "analytics page api" || fail "analytics page api"
  if [[ -n "${FRONTEND_URL:-}" ]]; then
    curl -fsSI "$FRONTEND_URL/dashboard/groups" >/dev/null && pass "groups disabled route safe" || fail "groups disabled route safe"
  fi
else
  echo "SKIP: login/webapp/content checks (set MARKETING_TEST_EMAIL and MARKETING_TEST_PASSWORD)"
fi

LEGACY_DOMAIN="builder.amarktai.com"
HYGIENE_TARGETS=()
for target in DEPLOYMENT_GUIDE.md DEPLOY_CHECKLIST.md README.md deploy scripts; do
  [[ -e "$REPO_ROOT/$target" ]] && HYGIENE_TARGETS+=("$REPO_ROOT/$target")
done

if ((${#HYGIENE_TARGETS[@]} == 0)); then
  warn "no deploy/script/doc targets found for builder-domain hygiene scan"
else
  MATCHES="$(grep -R -n "$LEGACY_DOMAIN" "${HYGIENE_TARGETS[@]}" 2>/dev/null || true)"
  DISALLOWED_MATCHES="$(printf '%s\n' "$MATCHES" | sed '/^[[:space:]]*$/d' | grep -v 'Builder is separate' || true)"
  if [[ -n "$DISALLOWED_MATCHES" ]]; then
    printf '%s\n' "$DISALLOWED_MATCHES"
    fail "builder domain references remain outside explicit 'Builder is separate' warnings"
  fi
  pass "no builder-domain references outside explicit Builder-is-separate warnings"
fi

echo "Local marketing checks complete."
