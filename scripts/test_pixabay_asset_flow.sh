#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/auth.sh"
source "$SCRIPT_DIR/lib/http.sh"

echo "== Pixabay asset flow =="
do_login

api_call "GET" "/api/v1/media/pixabay/search?q=business+marketing"
echo "search status: $_HTTP_STATUS"

api_call "GET" "/api/v1/media/pixabay/music"
python3 - <<'PY' "$_HTTP_BODY"
import json, sys
data = json.loads(sys.argv[1] or "{}")
status = data.get("status")
if status != "not_supported_by_api":
    print("FAIL expected not_supported_by_api, got:", status)
    raise SystemExit(1)
print("PASS unsupported category is truthful")
PY
