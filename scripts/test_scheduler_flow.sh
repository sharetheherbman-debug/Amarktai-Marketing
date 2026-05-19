#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
API="$BASE_URL/api/v1"
EMAIL="${MARKETING_TEST_EMAIL:-}"
PASSWORD="${MARKETING_TEST_PASSWORD:-}"

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

WEBAPP_ID=$(curl -fsS -X POST "$API/webapps/" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"name":"Scheduler Test Business","url":"https://example.com","description":"Scheduler test","category":"saas","target_audience":"buyers","key_features":["speed"],"is_active":true}' | python3 - <<'PY'
import json,sys
print(json.load(sys.stdin).get("id",""))
PY
)
[[ -n "$WEBAPP_ID" ]] || fail "create webapp"

CONTENT_JSON=$(curl -fsS -X POST "$API/content/generate?webapp_id=$WEBAPP_ID&platform=instagram" "${AUTH[@]}") || fail "generate content"
CONTENT_ID=$(python3 - <<'PY' "$CONTENT_JSON"
import json,sys
print(json.loads(sys.argv[1]).get("id",""))
PY
)
[[ -n "$CONTENT_ID" ]] || fail "content id missing"

SCHEDULE_JSON=$(curl -fsS -X POST "$API/scheduler/schedule" "${AUTH[@]}" -H 'Content-Type: application/json' -d "{\"content_id\":\"$CONTENT_ID\"}") || fail "schedule endpoint failed"
echo "$SCHEDULE_JSON" | python3 -m json.tool >/dev/null || fail "schedule response not json"
pass "content scheduled"

UPCOMING=$(curl -fsS "$API/scheduler/upcoming" "${AUTH[@]}") || fail "upcoming endpoint failed"
echo "$UPCOMING" | python3 - <<'PY' "$CONTENT_ID"
import json,sys
target=sys.argv[1]
rows=json.load(sys.stdin).get("items",[])
if not any(r.get("id")==target for r in rows):
    raise SystemExit(1)
print("ok")
PY
pass "scheduled content visible in upcoming list"
