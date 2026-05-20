#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/auth.sh"
source "$SCRIPT_DIR/lib/http.sh"

echo "== Platform truth no false connections =="
do_login

api_call "GET" "/api/v1/integrations/platforms"
python3 - <<'PY' "$_HTTP_BODY"
import json, sys
rows = json.loads(sys.argv[1] or "[]")
for row in rows:
    connected = bool(row.get("user_connected"))
    can_post = bool(row.get("can_post_now"))
    if connected and not can_post:
        print("FAIL false connected state:", row.get("id"))
        raise SystemExit(1)
print("PASS no false connected states")
PY
