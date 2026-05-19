#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
API="$BASE_URL/api/v1"
EMAIL="${MARKETING_TEST_EMAIL:-}"
PASSWORD="${MARKETING_TEST_PASSWORD:-}"
PLATFORMS=(facebook instagram linkedin twitter tiktok youtube reddit)

pass(){ echo "PASS: $1"; }
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

WEBAPP_ID=$(curl -fsS "$API/webapps/" "${AUTH[@]}" | python3 - <<'PY'
import json,sys
rows=json.load(sys.stdin)
print(rows[0]["id"] if rows else "")
PY
)
if [[ -z "$WEBAPP_ID" ]]; then
  WEBAPP_ID=$(curl -fsS -X POST "$API/webapps/" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"name":"Autonomous Test Business","url":"https://example.com","description":"Autonomous generation test","category":"saas","target_audience":"marketers","key_features":["automation"],"is_active":true}' | python3 - <<'PY'
import json,sys
print(json.load(sys.stdin).get("id",""))
PY
)
fi
[[ -n "$WEBAPP_ID" ]] || fail "unable to create/reuse webapp"
pass "webapp ready"

READINESS=$(curl -fsS "$API/settings/readiness" "${AUTH[@]}") || fail "readiness call failed"
GENX_HEALTHY=$(python3 - <<'PY' "$READINESS"
import json,sys
r=json.loads(sys.argv[1]).get("genx",{})
print("1" if (r.get("configured") and r.get("health_ok")) else "0")
PY
)

for platform in "${PLATFORMS[@]}"; do
  JSON=$(curl -fsS -X POST "$API/content/generate?webapp_id=$WEBAPP_ID&platform=$platform" "${AUTH[@]}") || fail "generation crashed for $platform"
  CONTENT_ID=$(python3 - <<'PY' "$JSON"
import json,sys
print(json.loads(sys.argv[1]).get("id",""))
PY
)
  [[ -n "$CONTENT_ID" ]] || fail "no content created for $platform"
  if [[ "$GENX_HEALTHY" == "1" ]]; then
    PROVIDER=$(python3 - <<'PY' "$JSON"
import json,sys
meta=json.loads(sys.argv[1]).get("generation_metadata") or {}
print(meta.get("provider",""))
PY
)
    [[ "$PROVIDER" == "genx" ]] || fail "provider must be genx for healthy GenX on $platform"
  fi
  pass "generated $platform content"
done

pass "autonomous generation coverage complete"
