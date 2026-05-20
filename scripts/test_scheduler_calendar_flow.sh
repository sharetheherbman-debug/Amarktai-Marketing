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
AUTH=(-H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")

BUSINESS="$(curl -sS -X POST "$API/webapps/" "${AUTH[@]}" -d '{"name":"Scheduler Flow Business","url":"https://example.com","description":"Local equine training business","category":"equine","target_audience":"Horse owners","key_features":["Training","Livery"]}')"
WEBAPP_ID="$(python3 - <<'PY' "$BUSINESS"
import json,sys
print(json.loads(sys.argv[1]).get("id",""))
PY
)"
CONTENT="$(curl -sS -X POST "$API/content/generate?webapp_id=$WEBAPP_ID&platform=instagram" -H "Authorization: Bearer $TOKEN")"
CONTENT_ID="$(python3 - <<'PY' "$CONTENT"
import json,sys
print(json.loads(sys.argv[1]).get("id",""))
PY
)"
PLANNED_AT="$(python3 - <<'PY'
from datetime import datetime, timedelta, timezone
print((datetime.now(timezone.utc)+timedelta(hours=2)).isoformat())
PY
)"
ITEM="$(curl -sS -X POST "$API/scheduler/items" "${AUTH[@]}" -d "{\"content_id\":\"$CONTENT_ID\",\"planned_at\":\"$PLANNED_AT\"}")"
ITEM_ID="$(python3 - <<'PY' "$ITEM"
import json,sys
data=json.loads(sys.argv[1]); assert data.get("status")=="scheduled", data
print(data.get("id",""))
PY
)"
[ -n "$ITEM_ID" ] || { echo "FAIL: no scheduler item id"; exit 1; }

CAL="$(curl -sS "$API/scheduler/calendar?start=$(python3 - <<'PY'
from datetime import datetime, timezone
print(datetime.now(timezone.utc).isoformat())
PY
)&end=$(python3 - <<'PY'
from datetime import datetime, timedelta, timezone
print((datetime.now(timezone.utc)+timedelta(days=3)).isoformat())
PY
)" -H "Authorization: Bearer $TOKEN")"
python3 - <<'PY' "$CAL" "$ITEM_ID"
import json,sys
items=json.loads(sys.argv[1]).get("items",[])
ids={item.get("id") for item in items}
assert sys.argv[2] in ids, f"scheduler item {sys.argv[2]} missing from calendar"
print("PASS: scheduler calendar flow")
PY
