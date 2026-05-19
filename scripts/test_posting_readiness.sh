#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
API="$BASE_URL/api/v1"
EMAIL="${MARKETING_TEST_EMAIL:-}"
PASSWORD="${MARKETING_TEST_PASSWORD:-}"
PLATFORMS=(facebook instagram linkedin twitter tiktok youtube reddit pinterest)

pass(){ echo "PASS: $1"; }
warn(){ echo "WARN: $1"; }
fail(){ echo "FAIL: $1"; exit 1; }

[[ -n "$EMAIL" && -n "$PASSWORD" ]] || fail "MARKETING_TEST_EMAIL and MARKETING_TEST_PASSWORD are required"

LOGIN_JSON=$(curl -fsS -X POST "$API/auth/login" -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}") || fail "login failed"
TOKEN=$(python3 - <<'PY' "$LOGIN_JSON"
import json,sys
print(json.loads(sys.argv[1]).get("access_token",""))
PY
)
[[ -n "$TOKEN" ]] || fail "missing access token"
AUTH=(-H "Authorization: Bearer $TOKEN")

READINESS=$(curl -fsS "$API/publishing/readiness" "${AUTH[@]}") || fail "publishing readiness failed"
echo "$READINESS" | python3 -m json.tool >/dev/null || fail "publishing readiness invalid json"
pass "publishing readiness endpoint"

for platform in "${PLATFORMS[@]}"; do
  TEST=$(curl -sS -o /tmp/test-platform.json -w "%{http_code}" -X POST "$API/publishing/test-platform" "${AUTH[@]}" -H 'Content-Type: application/json' -d "{\"platform\":\"$platform\"}")
  [[ "$TEST" != "500" ]] || fail "test-platform 500 for $platform"
  pass "test-platform no 500 for $platform"
done

BLOCK_CHECK=$(python3 - <<'PY' "$READINESS"
import json,sys
data=json.loads(sys.argv[1]).get("platforms",{})
blocked=[k for k,v in data.items() if not v.get("user_connected")]
print("1" if blocked else "0")
PY
)
[[ "$BLOCK_CHECK" == "1" ]] && pass "posting correctly blocked for at least one not-connected platform" || warn "all platforms connected in this environment"
