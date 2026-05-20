#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/auth.sh"
source "$SCRIPT_DIR/lib/http.sh"

echo "== Provider reset flow =="
do_login

api_call "GET" "/api/v1/settings/provider-resolution"
echo "provider-resolution status: $_HTTP_STATUS"

api_call "POST" "/api/v1/settings/api-keys/reset-all"
echo "reset keys status: $_HTTP_STATUS"

api_call "POST" "/api/v1/integrations/reset-all"
echo "reset integrations status: $_HTTP_STATUS"

api_call "GET" "/api/v1/integrations/platforms"
python3 - <<'PY' "$_HTTP_BODY"
import json, sys
data = json.loads(sys.argv[1] or "[]")
bad = [row.get("id") for row in data if row.get("user_connected")]
if bad:
    print("FAIL connected platforms remain:", bad)
    raise SystemExit(1)
print("PASS no platforms report connected")
PY
