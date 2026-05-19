#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://marketing.amarktai.com}"
API_BASE_URL="${API_BASE_URL:-https://marketing.amarktai.com/api/v1}"
EMAIL="${MARKETING_TEST_EMAIL:-}"
PASSWORD="${MARKETING_TEST_PASSWORD:-}"

pass(){ echo "PASS: $1"; }
fail(){ echo "FAIL: $1"; exit 1; }

[[ -d "$REPO_ROOT/backend/app" && -f "$REPO_ROOT/app/package.json" ]] || fail "REPO_ROOT must contain backend/app and app/package.json"

echo "Resolved REPO_ROOT: $REPO_ROOT"
echo "Using PUBLIC_BASE_URL: $PUBLIC_BASE_URL"
echo "Using API_BASE_URL: $API_BASE_URL"

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
  case "$STATUS" in
    configured)
      pass "content generation configured"
      ;;
    not_configured)
      pass "content generation gracefully not_configured"
      ;;
    *)
      fail "unexpected content generation status: ${STATUS:-<empty>}"
      ;;
  esac

  curl -fsS "$API_BASE_URL/settings/readiness" -H "Authorization: Bearer $TOKEN" >/dev/null && pass "integrations/settings readiness" || fail "integrations/settings readiness"
  curl -fsS "$API_BASE_URL/analytics/summary" -H "Authorization: Bearer $TOKEN" >/dev/null && pass "analytics page data" || fail "analytics page data"
  curl -fsSI "$PUBLIC_BASE_URL/dashboard/groups" >/dev/null && pass "groups disabled route safe" || fail "groups disabled route safe"
else
  echo "SKIP: authenticated checks (set MARKETING_TEST_EMAIL and MARKETING_TEST_PASSWORD)"
fi

LEGACY_DOMAIN="builder.amarktai.com"
HYGIENE_TARGETS=()
for target in DEPLOYMENT_GUIDE.md DEPLOY_CHECKLIST.md README.md deploy scripts; do
  [[ -e "$REPO_ROOT/$target" ]] && HYGIENE_TARGETS+=("$REPO_ROOT/$target")
done

if ((${#HYGIENE_TARGETS[@]} == 0)); then
  echo "WARN: no deploy/script/doc targets found for builder-domain hygiene scan"
else
  MATCHES="$(grep -R -n "$LEGACY_DOMAIN" "${HYGIENE_TARGETS[@]}" 2>/dev/null || true)"
  DISALLOWED_MATCHES="$(printf '%s\n' "$MATCHES" | sed '/^[[:space:]]*$/d' | grep -v 'Builder is separate' || true)"
  if [[ -n "$DISALLOWED_MATCHES" ]]; then
    printf '%s\n' "$DISALLOWED_MATCHES"
    fail "builder domain references remain outside explicit 'Builder is separate' warnings"
  else
    pass "no builder-domain references outside explicit Builder-is-separate warnings"
  fi
fi

echo "Go-live smoke checks complete."
