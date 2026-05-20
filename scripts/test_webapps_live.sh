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
try:
    print(json.loads(sys.argv[1]).get("access_token",""))
except Exception:
    print("")
PY
)"
if [[ -z "$TOKEN" ]]; then
  echo "FAIL: login did not return access_token" >&2
  exit 1
fi

LIST_BODY="$(request_json "WEBAPPS LIST" "GET" "/api/v1/webapps/")"
python3 - <<'PY' "$LIST_BODY"
import json,sys
obj=json.loads(sys.argv[1])
assert isinstance(obj, list)
PY

CREATE_NAME_BODY="$(request_json "CREATE NAME-ONLY" "POST" "/api/v1/webapps/" '{"name":"Live Name Only Business"}')"
CREATE_URL_BODY="$(request_json "CREATE URL-ONLY" "POST" "/api/v1/webapps/" '{"url":"https://example.com"}')"
CREATE_BOTH_BODY="$(request_json "CREATE NAME+URL" "POST" "/api/v1/webapps/" '{"name":"Live Name Url Business","url":"https://example.org","is_active":true}')"

WEBAPP_ID="$(python3 - <<'PY' "$CREATE_BOTH_BODY"
import json,sys
print(json.loads(sys.argv[1]).get("id",""))
PY
)"
if [[ -z "$WEBAPP_ID" ]]; then
  echo "FAIL: create name+url did not return id" >&2
  exit 1
fi

request_json "GET BY ID" "GET" "/api/v1/webapps/$WEBAPP_ID" >/dev/null
echo "PASS: test_webapps_live completed"
