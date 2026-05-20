#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
EMAIL="${MARKETING_TEST_EMAIL:-}"
PASSWORD="${MARKETING_TEST_PASSWORD:-}"

fail() { echo "FAIL: $1" >&2; exit 1; }
pass() { echo "PASS: $1" >&2; }

[[ -n "$EMAIL" && -n "$PASSWORD" ]] || fail "MARKETING_TEST_EMAIL and MARKETING_TEST_PASSWORD are required"

request_json() {
  local label="$1"
  local method="$2"
  local path="$3"
  local body="${4:-}"
  local auth=()
  if [[ -n "${TOKEN:-}" ]]; then auth=(-H "Authorization: Bearer $TOKEN"); fi

  local out http resp
  if [[ -n "$body" ]]; then
    out=$(curl -sS -X "$method" "$BASE_URL$path" "${auth[@]}" -H 'Content-Type: application/json' -d "$body" -w "\n%{http_code}" || true)
  else
    out=$(curl -sS -X "$method" "$BASE_URL$path" "${auth[@]}" -H 'Content-Type: application/json' -w "\n%{http_code}" || true)
  fi
  http="$(printf '%s' "$out" | tail -n1)"
  resp="$(printf '%s' "$out" | sed '$d')"

  if [[ "$http" -ge 500 ]]; then
    echo "FAIL STATUS $label: $http" >&2
    echo "FAIL BODY $label: $resp" >&2
    fail "$label returned server error"
  fi
  if [[ "$http" -lt 200 || "$http" -ge 300 ]]; then
    echo "FAIL STATUS $label: $http" >&2
    echo "FAIL BODY $label: $resp" >&2
    fail "$label returned non-2xx"
  fi
  pass "$label"
  printf '%s' "$resp"
}

LOGIN_JSON=$(request_json "login" "POST" "/api/v1/auth/login" "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
TOKEN=$(python3 - <<'PY' "$LOGIN_JSON"
import json,sys
try:
    print(json.loads(sys.argv[1]).get("access_token",""))
except Exception:
    print("")
PY
)
[[ -n "$TOKEN" ]] || fail "login missing access_token"

LIST_JSON=$(request_json "get webapps" "GET" "/api/v1/webapps/")
python3 - <<'PY' "$LIST_JSON" || fail "webapps list is not JSON array"
import json,sys
obj=json.loads(sys.argv[1])
assert isinstance(obj, list)
PY

NAME_ONLY_JSON=$(request_json "create name-only business" "POST" "/api/v1/webapps/" "{\"name\":\"Webapps Name Only Business\"}")
URL_ONLY_JSON=$(request_json "create url-only business" "POST" "/api/v1/webapps/" "{\"url\":\"example.com\"}")
NAME_URL_JSON=$(request_json "create name+url business" "POST" "/api/v1/webapps/" "{\"name\":\"Webapps Name Url Business\",\"url\":\"https://example.org\"}")

NAME_ONLY_ID=$(python3 - <<'PY' "$NAME_ONLY_JSON"
import json,sys
print(json.loads(sys.argv[1]).get("id",""))
PY
)
[[ -n "$NAME_ONLY_ID" ]] || fail "name-only create missing id"

URL_ONLY_ID=$(python3 - <<'PY' "$URL_ONLY_JSON"
import json,sys
print(json.loads(sys.argv[1]).get("id",""))
PY
)
[[ -n "$URL_ONLY_ID" ]] || fail "url-only create missing id"

NAME_URL_ID=$(python3 - <<'PY' "$NAME_URL_JSON"
import json,sys
print(json.loads(sys.argv[1]).get("id",""))
PY
)
[[ -n "$NAME_URL_ID" ]] || fail "name+url create missing id"

request_json "get webapp by id" "GET" "/api/v1/webapps/$NAME_URL_ID" >/dev/null
pass "webapps API smoke checks complete"
