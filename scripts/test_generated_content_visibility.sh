#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
EMAIL="${MARKETING_TEST_EMAIL:-amarktainetwork@gmail.com}"
PASSWORD="${MARKETING_TEST_PASSWORD:-ChangeMeNow2026!}"

print_response() {
  local label="$1"
  local response="$2"
  local body status
  status="$(printf '%s' "$response" | tail -n1)"
  body="$(printf '%s' "$response" | sed '$d')"
  echo "=== $label ==="
  echo "STATUS: $status"
  echo "BODY: $body"
  if [[ "$status" -ge 500 ]]; then
    echo "FAIL: $label returned $status" >&2
    exit 1
  fi
}

request_json() {
  local label="$1"
  local method="$2"
  local path="$3"
  local payload="${4:-}"
  local auth_header=()
  if [[ -n "${TOKEN:-}" ]]; then
    auth_header=(-H "Authorization: Bearer $TOKEN")
  fi

  local response
  if [[ -n "$payload" ]]; then
    response="$(curl -sS -X "$method" "$BASE_URL$path" "${auth_header[@]}" -H 'Content-Type: application/json' -d "$payload" -w '\n%{http_code}' || true)"
  else
    response="$(curl -sS -X "$method" "$BASE_URL$path" "${auth_header[@]}" -H 'Content-Type: application/json' -w '\n%{http_code}' || true)"
  fi
  print_response "$label" "$response"
  printf '%s' "$response" | sed '$d'
}

LOGIN_BODY="$(request_json "LOGIN" "POST" "/api/v1/auth/login" "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")"
TOKEN="$(python3 - <<'PY' "$LOGIN_BODY"
import json,sys
print(json.loads(sys.argv[1]).get("access_token",""))
PY
)"
if [[ -z "$TOKEN" ]]; then
  echo "FAIL: login did not return token" >&2
  exit 1
fi

CREATE_BODY="$(request_json "CREATE BUSINESS" "POST" "/api/v1/webapps/" '{"name":"Visibility Gate Business","url":"https://example.com"}')"
WEBAPP_ID="$(python3 - <<'PY' "$CREATE_BODY"
import json,sys
print(json.loads(sys.argv[1]).get("id",""))
PY
)"
if [[ -z "$WEBAPP_ID" ]]; then
  echo "FAIL: business id missing" >&2
  exit 1
fi

GENERATE_BODY="$(request_json "GENERATE CONTENT" "POST" "/api/v1/content/generate?webapp_id=$WEBAPP_ID&platform=instagram")"
CONTENT_ID="$(python3 - <<'PY' "$GENERATE_BODY"
import json,sys
print(json.loads(sys.argv[1]).get("id",""))
PY
)"
if [[ -z "$CONTENT_ID" ]]; then
  echo "FAIL: generate content did not return id" >&2
  exit 1
fi

request_json "GET CONTENT ITEM" "GET" "/api/v1/content/items/$CONTENT_ID" >/dev/null

WEBAPP_CONTENT_BODY="$(request_json "GET CONTENT FOR BUSINESS" "GET" "/api/v1/content/webapp/$WEBAPP_ID")"
python3 - <<'PY' "$WEBAPP_CONTENT_BODY" "$CONTENT_ID"
import json,sys
items=json.loads(sys.argv[1])
ids={item.get("id") for item in items if isinstance(item, dict)}
assert sys.argv[2] in ids, "generated content missing from webapp listing"
PY

PACK_BODY="$(request_json "GENERATE PACK" "POST" "/api/v1/content/generate-pack" "{\"webapp_id\":\"$WEBAPP_ID\",\"platforms\":[\"instagram\"],\"auto_select_formats\":true}")"
python3 - <<'PY' "$PACK_BODY"
import json,sys
data=json.loads(sys.argv[1])
assert data.get("count",0) >= 1, "pack generation returned no items"
PY

LIBRARY_BODY="$(request_json "GET CONTENT LIBRARY" "GET" "/api/v1/content/items?webapp_id=$WEBAPP_ID")"
python3 - <<'PY' "$LIBRARY_BODY"
import json,sys
items=json.loads(sys.argv[1])
assert isinstance(items, list), "library did not return list"
assert len(items) >= 2, "expected generated + pack items in library"
PY

request_json "DELETE CONTENT ITEM" "DELETE" "/api/v1/content/items/$CONTENT_ID?confirm=true" >/dev/null

POST_DELETE_BODY="$(request_json "VERIFY DELETE" "GET" "/api/v1/content/webapp/$WEBAPP_ID")"
python3 - <<'PY' "$POST_DELETE_BODY" "$CONTENT_ID"
import json,sys
items=json.loads(sys.argv[1])
ids={item.get("id") for item in items if isinstance(item, dict)}
assert sys.argv[2] not in ids, "deleted content still present"
PY

request_json "DELETE BUSINESS" "DELETE" "/api/v1/webapps/$WEBAPP_ID?confirm=true" >/dev/null
echo "PASS: generated content visibility gate completed"
