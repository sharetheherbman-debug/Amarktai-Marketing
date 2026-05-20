#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
EMAIL="${MARKETING_TEST_EMAIL:-}"
PASSWORD="${MARKETING_TEST_PASSWORD:-}"
BUSINESS_NAME="${BUSINESS_NAME:-Production Flow Business}"
BUSINESS_URL="${BUSINESS_URL:-https://example.com}"

fail() { echo "NO_GO: $1" >&2; exit 1; }
warn() { echo "WARN: $1" >&2; }
pass() { echo "PASS: $1" >&2; }

json_value() {
  python3 - <<'PY' "$1" "$2"
import json,sys
obj=json.loads(sys.argv[1])
path=sys.argv[2].split('.')
cur=obj
for key in path:
    if isinstance(cur, list):
        cur=cur[int(key)]
    elif isinstance(cur, dict):
        cur=cur.get(key)
    else:
        cur=None
print("" if cur is None else cur)
PY
}

request_json() {
  local label="$1"
  local method="$2"
  local path="$3"
  local body="${4:-}"
  local auth_header=()
  if [[ -n "${TOKEN:-}" ]]; then auth_header=(-H "Authorization: Bearer $TOKEN"); fi

  local output http resp
  if [[ -n "$body" ]]; then
    output=$(curl -sS -X "$method" "$BASE_URL$path" "${auth_header[@]}" -H 'Content-Type: application/json' -d "$body" -w "\n%{http_code}" || true)
  else
    output=$(curl -sS -X "$method" "$BASE_URL$path" "${auth_header[@]}" -H 'Content-Type: application/json' -w "\n%{http_code}" || true)
  fi
  http="$(printf '%s' "$output" | tail -n1)"
  resp="$(printf '%s' "$output" | sed '$d')"

  if [[ "$http" -ge 500 ]]; then
    echo "ENDPOINT FAIL: $label ($method $path) HTTP $http" >&2
    echo "RESPONSE: $resp" >&2
    fail "$label returned 500+"
  fi
  if [[ "$http" -lt 200 || "$http" -ge 300 ]]; then
    echo "ENDPOINT WARN: $label ($method $path) HTTP $http" >&2
    echo "RESPONSE: $resp" >&2
    warn "$label returned non-2xx"
  else
    pass "$label"
  fi

  python3 - <<'PY' "$resp" || fail "$label returned non-JSON"
import json,sys
json.loads(sys.argv[1] or "{}")
PY
  printf '%s' "$resp"
}

[[ -n "$EMAIL" && -n "$PASSWORD" ]] || fail "MARKETING_TEST_EMAIL and MARKETING_TEST_PASSWORD are required"

bash "$REPO_ROOT/scripts/fix_vps_runtime_permissions.sh" || fail "permissions fix"
pass "permissions fix"

cd "$REPO_ROOT/backend"
python3 -m compileall -q app || fail "backend compile"
python3 - <<'PY' || fail "backend import"
from app.main import app
print("IMPORT_OK", getattr(app, "title", "app_loaded"))
PY
pass "backend import"

cd "$REPO_ROOT/app"
npm run build >/dev/null || fail "frontend build"
pass "frontend build"

LOGIN_JSON=$(request_json "login" "POST" "/api/v1/auth/login" "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
TOKEN=$(python3 - <<'PY' "$LOGIN_JSON"
import json,sys
try:
    print(json.loads(sys.argv[1]).get("access_token",""))
except Exception:
    print("")
PY
)
[[ -n "$TOKEN" ]] || fail "login failed"
pass "login token"

WEBAPPS_JSON=$(request_json "webapps list" "GET" "/api/v1/webapps/")
python3 - <<'PY' "$WEBAPPS_JSON" || fail "webapps list must return array"
import json,sys
assert isinstance(json.loads(sys.argv[1]), list)
PY

CREATE_JSON=$(request_json "webapp create" "POST" "/api/v1/webapps/" "{\"name\":\"$BUSINESS_NAME\",\"url\":\"$BUSINESS_URL\"}")
WEBAPP_ID=$(json_value "$CREATE_JSON" "id")
[[ -n "$WEBAPP_ID" ]] || fail "webapp create missing id"

request_json "integrations platforms" "GET" "/api/v1/integrations/platforms" >/dev/null
request_json "provider test" "POST" "/api/v1/settings/api-keys/test" "{\"key_name\":\"GENX_API_KEY\"}" >/dev/null
READINESS_JSON=$(request_json "readiness" "GET" "/api/v1/settings/readiness")
request_json "content generate" "POST" "/api/v1/content/generate?webapp_id=$WEBAPP_ID&platform=instagram" >/dev/null
request_json "content generate-all" "POST" "/api/v1/content/generate-all" "{\"webapp_id\":\"$WEBAPP_ID\"}" >/dev/null

if [[ "$(python3 - <<'PY' "$READINESS_JSON"
import json,sys
obj=json.loads(sys.argv[1])
print("1" if obj.get("full_go_live_ready") else "0")
PY
)" == "1" ]]; then
  echo "PRODUCTION_FLOW_OK"
else
  echo "LIMITED_MODE_OK"
fi
