#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
EMAIL="${MARKETING_TEST_EMAIL:-amarktainetwork@gmail.com}"
PASSWORD="${MARKETING_TEST_PASSWORD:-ChangeMeNow2026!}"
API="$BASE_URL/api/v1"

TOKEN="$(curl -sS -X POST "$API/auth/login" -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | python3 - <<'PY'
import json,sys
print(json.load(sys.stdin).get("access_token",""))
PY
)"
[ -n "$TOKEN" ] || { echo "FAIL: no token"; exit 1; }

BODY="$(curl -sS -X POST "$API/capabilities/route" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"capability":"platform_copy","platform":"instagram","format":"text_post","budget_mode":"budget","business":{"name":"Budget Test Business","category":"cyber security"}}')"
python3 - <<'PY' "$BODY"
import json,sys
data=json.loads(sys.argv[1])
assert data.get("selected_provider"), data
assert isinstance(data.get("fallback_chain"), list) and data["fallback_chain"], data
print("PASS: provider router flow")
PY
