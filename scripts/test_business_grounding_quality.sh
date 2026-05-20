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

BUSINESS="$(curl -sS -X POST "$API/webapps/" "${AUTH[@]}" -d '{"name":"Horse Care Pro","url":"https://example.com","description":"Horse care and riding support","category":"equine","target_audience":"Horse owners","key_features":["Horse care","Riding support","Stable advice"]}')"
WEBAPP_ID="$(python3 - <<'PY' "$BUSINESS"
import json,sys
print(json.loads(sys.argv[1]).get("id",""))
PY
)"
CONTENT="$(curl -sS -X POST "$API/content/generate?webapp_id=$WEBAPP_ID&platform=instagram" -H "Authorization: Bearer $TOKEN")"
python3 - <<'PY' "$CONTENT"
import json,sys
data=json.loads(sys.argv[1])
metadata=data.get("generation_metadata") or {}
caption=(data.get("caption") or "").lower()
hashtags=" ".join(data.get("hashtags") or []).lower()
assert "amarktai" not in hashtags, hashtags
score=metadata.get("business_grounding_score", 0)
assert score >= 70, score
assert any(term in caption for term in ["horse","equine","stable","riding"]), caption
print("PASS: business grounding quality")
PY
