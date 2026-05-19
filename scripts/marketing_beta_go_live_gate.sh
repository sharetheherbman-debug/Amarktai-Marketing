#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
BUSINESS_NAME="${BUSINESS_NAME:-Example Business}"
BUSINESS_URL="${BUSINESS_URL:-https://example.com}"
EMAIL="${MARKETING_TEST_EMAIL:-}"
PASSWORD="${MARKETING_TEST_PASSWORD:-}"

fail() { echo "NO_GO: $1"; exit 1; }
warn() { echo "WARN: $1"; }
pass() { echo "PASS: $1"; }

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

require_json_http_ok "provider-resolution" "GET" "/api/v1/settings/provider-resolution" >/tmp/provider_resolution.json
require_json_http_ok "readiness" "GET" "/api/v1/settings/readiness" >/tmp/readiness.json
require_json_http_ok "analyze" "POST" "/api/v1/webapps/analyze" "{\"name\":\"$BUSINESS_NAME\",\"url\":\"$BUSINESS_URL\"}" >/tmp/analyze.json

CREATE_JSON=$(require_json_http_ok "create business profile" "POST" "/api/v1/webapps/" "{\"name\":\"$BUSINESS_NAME\",\"url\":\"$BUSINESS_URL\",\"description\":\"Beta gate profile\",\"is_active\":true}")
WEBAPP_ID=$(python3 - <<'PY' "$CREATE_JSON"
import json,sys
obj=json.loads(sys.argv[1])
print(obj.get("id",""))
PY
)
[[ -n "$WEBAPP_ID" ]] || fail "webapp id missing after creation"

INSTAGRAM_JSON=$(require_json_http_ok "generate instagram" "POST" "/api/v1/content/generate?webapp_id=$WEBAPP_ID&platform=instagram")
FACEBOOK_JSON=$(require_json_http_ok "generate facebook" "POST" "/api/v1/content/generate?webapp_id=$WEBAPP_ID&platform=facebook")
LINKEDIN_JSON=$(require_json_http_ok "generate linkedin" "POST" "/api/v1/content/generate?webapp_id=$WEBAPP_ID&platform=linkedin")
GEN_ALL_JSON=$(require_json_http_ok "generate-all launch platforms" "POST" "/api/v1/content/generate-all" "{\"webapp_id\":\"$WEBAPP_ID\"}")

python3 - <<'PY' "$INSTAGRAM_JSON" "$FACEBOOK_JSON" "$LINKEDIN_JSON" "$GEN_ALL_JSON" || fail "caption/body or metadata validation failed"
import json,sys
single=[json.loads(sys.argv[1]),json.loads(sys.argv[2]),json.loads(sys.argv[3])]
for i,item in enumerate(single):
    if not (item.get("caption") or item.get("body")):
        raise SystemExit(f"single generation {i} missing caption/body")
    meta=item.get("generation_metadata") or {}
    if "provider_actual" not in meta or "generation_status" not in meta:
        raise SystemExit(f"single generation {i} missing truthful generation_metadata")
all_payload=json.loads(sys.argv[4])
items=all_payload.get("items") or []
if not items:
    raise SystemExit("generate-all returned no items")
for entry in items:
    if "error" in entry:
        continue
    if not (entry.get("caption") or entry.get("body")):
        raise SystemExit("generate-all item missing caption/body")
    meta=entry.get("generation_metadata") or {}
    if "provider_actual" not in meta or "generation_status" not in meta:
        raise SystemExit("generate-all item missing truthful generation_metadata")
PY

DEGRADED=$(python3 - <<'PY' "$INSTAGRAM_JSON" "$FACEBOOK_JSON" "$LINKEDIN_JSON" "$GEN_ALL_JSON"
import json,sys
objs=[json.loads(x) for x in sys.argv[1:4]]
objs += [i for i in (json.loads(sys.argv[4]).get("items") or []) if "generation_metadata" in i]
print("1" if any((o.get("generation_metadata") or {}).get("degraded") for o in objs) else "0")
PY
)

if [[ "$DEGRADED" == "1" ]]; then
  echo "DEGRADED_BETA_GO"
else
  echo "BETA_GO"
fi
