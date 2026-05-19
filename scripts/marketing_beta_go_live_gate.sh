#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
GENERIC_BUSINESS_NAME="${GENERIC_BUSINESS_NAME:-Beta Flow Business}"
WEBSITE_BUSINESS_NAME="${WEBSITE_BUSINESS_NAME:-Beta Flow Website Business}"
BUSINESS_URL="${BUSINESS_URL:-https://example.com}"
EMAIL="${MARKETING_TEST_EMAIL:-}"
PASSWORD="${MARKETING_TEST_PASSWORD:-}"

fail() { echo "NO_GO: $1"; exit 1; }
warn() { echo "WARN: $1"; }
pass() { echo "PASS: $1"; }
json_value() {
  python3 - <<'PY' "$1" "$2"
import json,sys
obj=json.loads(sys.argv[1])
path=sys.argv[2].split('.')
cur=obj
for key in path:
    if isinstance(cur, list):
        cur=cur[int(key)]
    else:
        cur=cur.get(key)
print("" if cur is None else cur)
PY
}

require_json_http_ok() {
  local label="$1"
  local method="$2"
  local path="$3"
  local body="${4:-}"
  local auth_header=()
  if [[ -n "${TOKEN:-}" ]]; then auth_header=(-H "Authorization: Bearer $TOKEN"); fi

  local output http body_file
  body_file="$(mktemp)"
  if [[ -n "$body" ]]; then
    output=$(curl -sS -X "$method" "$BASE_URL$path" "${auth_header[@]}" -H 'Content-Type: application/json' -d "$body" -w "\n%{http_code}" || true)
  else
    output=$(curl -sS -X "$method" "$BASE_URL$path" "${auth_header[@]}" -H 'Content-Type: application/json' -w "\n%{http_code}" || true)
  fi
  http="$(printf '%s' "$output" | tail -n1)"
  printf '%s' "$output" | sed '$d' > "$body_file"

  python3 - <<'PY' "$body_file" || fail "$label returned non-JSON"
import json,sys
json.load(open(sys.argv[1]))
PY

  if [[ "$http" -ge 500 ]]; then fail "$label returned $http"; fi
  if [[ "$http" -lt 200 || "$http" -ge 300 ]]; then
    warn "$label returned $http"
  else
    pass "$label"
  fi

  cat "$body_file"
  rm -f "$body_file"
}

[[ -n "$EMAIL" && -n "$PASSWORD" ]] || fail "MARKETING_TEST_EMAIL and MARKETING_TEST_PASSWORD are required"

bash "$REPO_ROOT/scripts/fix_vps_runtime_permissions.sh" || fail "permissions fix"
pass "permissions fix/check"

cd "$REPO_ROOT"
python3 -m compileall backend >/dev/null || fail "backend compile/import"
pass "backend compile/import"

cd "$REPO_ROOT/app"
npm run build >/dev/null || fail "frontend build"
pass "frontend build"

if ! grep -R "Add Business" "$REPO_ROOT/app/dist" >/dev/null 2>&1; then fail "built frontend missing Add Business copy"; fi
pass "frontend contains Add Business"
if ! grep -R "Content Studio" "$REPO_ROOT/app/dist" >/dev/null 2>&1; then fail "built frontend missing Content Studio copy"; fi
pass "frontend contains Content Studio"

UNSUPPORTED_FOUND=0
for label in Bluesky Threads Telegram Snapchat; do
  if grep -R "$label" "$REPO_ROOT/app/dist" >/dev/null 2>&1; then
    warn "built frontend still contains unsupported label: $label"
    UNSUPPORTED_FOUND=1
  fi
done

LOGIN_JSON=$(curl -sS -X POST "$BASE_URL/api/v1/auth/login" -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" || true)
TOKEN=$(python3 - <<'PY' "$LOGIN_JSON"
import json,sys
try:
    print(json.loads(sys.argv[1]).get("access_token",""))
except Exception:
    print("")
PY
)
[[ -n "$TOKEN" ]] || fail "login failed"
pass "login"

LIST_JSON=$(require_json_http_ok "webapps list" "GET" "/api/v1/webapps/")
[[ "$(python3 - <<'PY' "$LIST_JSON"
import json,sys
obj=json.loads(sys.argv[1])
print(1 if isinstance(obj, list) else 0)
PY
)" == "1" ]] || fail "webapps list did not return a JSON array"

require_json_http_ok "provider-resolution" "GET" "/api/v1/settings/provider-resolution" >/tmp/provider_resolution.json
READINESS_JSON=$(require_json_http_ok "readiness" "GET" "/api/v1/settings/readiness")
ANALYZE_JSON=$(require_json_http_ok "analyze URL" "POST" "/api/v1/webapps/analyze" "{\"name\":\"$WEBSITE_BUSINESS_NAME\",\"url\":\"$BUSINESS_URL\"}")

GENERIC_CREATE_JSON=$(require_json_http_ok "create generic business" "POST" "/api/v1/webapps/" "{\"name\":\"$GENERIC_BUSINESS_NAME\",\"description\":\"Beta gate generic business\",\"is_active\":true}")
GENERIC_WEBAPP_ID=$(json_value "$GENERIC_CREATE_JSON" "id")
[[ -n "$GENERIC_WEBAPP_ID" ]] || fail "generic business id missing after creation"
pass "generic business id returned"

WEBSITE_CREATE_JSON=$(require_json_http_ok "create website business" "POST" "/api/v1/webapps/" "{\"name\":\"$WEBSITE_BUSINESS_NAME\",\"url\":\"$BUSINESS_URL\",\"description\":\"Beta gate website business\",\"is_active\":true}")
WEBSITE_WEBAPP_ID=$(json_value "$WEBSITE_CREATE_JSON" "id")
[[ -n "$WEBSITE_WEBAPP_ID" ]] || fail "website business id missing after creation"
pass "website business id returned"

require_json_http_ok "refresh intelligence" "POST" "/api/v1/webapps/$WEBSITE_WEBAPP_ID/refresh-intelligence" >/tmp/refresh_intelligence.json
require_json_http_ok "platform integrations" "GET" "/api/v1/integrations/platforms" >/tmp/platform_integrations.json

INSTAGRAM_JSON=$(require_json_http_ok "generate instagram" "POST" "/api/v1/content/generate?webapp_id=$WEBSITE_WEBAPP_ID&platform=instagram")
FACEBOOK_JSON=$(require_json_http_ok "generate facebook" "POST" "/api/v1/content/generate?webapp_id=$WEBSITE_WEBAPP_ID&platform=facebook")
LINKEDIN_JSON=$(require_json_http_ok "generate linkedin" "POST" "/api/v1/content/generate?webapp_id=$WEBSITE_WEBAPP_ID&platform=linkedin")
GEN_ALL_JSON=$(require_json_http_ok "generate-all launch platforms" "POST" "/api/v1/content/generate-all" "{\"webapp_id\":\"$WEBSITE_WEBAPP_ID\"}")

python3 - <<'PY' "$ANALYZE_JSON" "$INSTAGRAM_JSON" "$FACEBOOK_JSON" "$LINKEDIN_JSON" "$GEN_ALL_JSON" || fail "analysis or generation validation failed"
import json,sys
analyze=json.loads(sys.argv[1])
if "scrape_status" not in analyze:
    raise SystemExit("analyze missing scrape_status")
for payload in [json.loads(sys.argv[2]), json.loads(sys.argv[3]), json.loads(sys.argv[4])]:
    if not (payload.get("caption") or payload.get("body")):
        raise SystemExit("single generation missing caption/body")
    meta=payload.get("generation_metadata") or {}
    for key in ("provider_actual", "generation_status", "cta", "scrape_status"):
        if key not in meta:
            raise SystemExit(f"single generation missing {key}")
all_payload=json.loads(sys.argv[5])
items=all_payload.get("items") or []
if not items:
    raise SystemExit("generate-all returned no items")
for entry in items:
    if entry.get("error"):
        continue
    if not (entry.get("caption") or entry.get("body")):
        raise SystemExit("generate-all item missing caption/body")
    meta=entry.get("generation_metadata") or {}
    for key in ("provider_actual", "generation_status"):
        if key not in meta:
            raise SystemExit(f"generate-all item missing {key}")
PY

DEGRADED=$(python3 - <<'PY' "$READINESS_JSON" "$INSTAGRAM_JSON" "$FACEBOOK_JSON" "$LINKEDIN_JSON" "$GEN_ALL_JSON"
import json,sys
readiness=json.loads(sys.argv[1])
objs=[json.loads(sys.argv[2]), json.loads(sys.argv[3]), json.loads(sys.argv[4])]
objs += [i for i in (json.loads(sys.argv[5]).get("items") or []) if "generation_metadata" in i]
degraded = any((obj.get("generation_metadata") or {}).get("degraded") for obj in objs)
if not readiness.get("full_go_live_ready", False):
    degraded = True
print("1" if degraded else "0")
PY
)

if [[ "$DEGRADED" == "1" ]]; then
  echo "DEGRADED_BETA_GO"
else
  echo "BETA_GO"
fi
