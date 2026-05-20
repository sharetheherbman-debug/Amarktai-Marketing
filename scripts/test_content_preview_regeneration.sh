#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/auth.sh"
source "$SCRIPT_DIR/lib/http.sh"

echo "== Content preview + regeneration =="
do_login

if [[ -z "${MARKETING_TEST_WEBAPP_ID:-}" ]]; then
  echo "Set MARKETING_TEST_WEBAPP_ID to run this gate."
  exit 0
fi

api_call "POST" "/api/v1/content/preview" "{\"webapp_id\":\"${MARKETING_TEST_WEBAPP_ID}\",\"platform\":\"instagram\",\"format\":\"text_post\"}"
echo "preview status: $_HTTP_STATUS"

api_call "GET" "/api/v1/content/webapp/${MARKETING_TEST_WEBAPP_ID}"
CONTENT_ID="$(python3 - <<'PY' "$_HTTP_BODY"
import json, sys
items = json.loads(sys.argv[1] or "[]")
print(items[0]["id"] if items else "")
PY
)"

if [[ -n "$CONTENT_ID" ]]; then
  api_call "POST" "/api/v1/content/items/${CONTENT_ID}/regenerate" "{\"feedback\":\"different angle and CTA\",\"avoid_previous_text\":[]}"
  echo "regenerate status: $_HTTP_STATUS"
fi
