#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
EMAIL="${MARKETING_TEST_EMAIL:-amarktainetwork@gmail.com}"
PASSWORD="${MARKETING_TEST_PASSWORD:-ChangeMeNow2026!}"
API="$BASE_URL/api/v1"

login() {
  curl -sS -X POST "$API/auth/login" -H 'Content-Type: application/json' \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}"
}

TOKEN="$(login | python3 - <<'PY'
import json,sys
print(json.load(sys.stdin).get("access_token",""))
PY
)"
[ -n "$TOKEN" ] || { echo "FAIL: no token"; exit 1; }

AUTH=(-H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")
WEBAPP_BODY="$(curl -sS -X POST "$API/webapps/" "${AUTH[@]}" -d '{"name":"12 Platform Pack Business","url":"https://example.com","description":"Cyber security services for SMBs","category":"cyber security","target_audience":"SMB owners","key_features":["SOC support","Risk reduction","Compliance help"]}')"
WEBAPP_ID="$(python3 - <<'PY' "$WEBAPP_BODY"
import json,sys
print(json.loads(sys.argv[1]).get("id",""))
PY
)"
[ -n "$WEBAPP_ID" ] || { echo "FAIL: no webapp"; exit 1; }

PACK_BODY="$(curl -sS -X POST "$API/content/generate-pack" "${AUTH[@]}" -d "{\"webapp_id\":\"$WEBAPP_ID\",\"platforms\":[\"instagram\",\"facebook\",\"linkedin\",\"twitter\",\"tiktok\",\"youtube\",\"reddit\",\"pinterest\",\"threads\",\"bluesky\",\"telegram\",\"snapchat\"],\"auto_select_formats\":true}")"
python3 - <<'PY' "$PACK_BODY"
import json,sys
data=json.loads(sys.argv[1])
assert data.get("count",0) >= 12, f"expected >=12 items, got {data.get('count')}"
platforms={item.get("platform") for item in data.get("items",[]) if isinstance(item,dict)}
required={"instagram","facebook","linkedin","twitter","tiktok","youtube","reddit","pinterest","threads","bluesky","telegram","snapchat"}
missing=sorted(required-platforms)
assert not missing, f"missing platforms: {missing}"
print("PASS: 12-platform pack generated")
PY
