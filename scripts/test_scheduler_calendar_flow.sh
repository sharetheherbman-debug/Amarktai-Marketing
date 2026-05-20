#!/usr/bin/env bash
# =============================================================================
# scripts/test_scheduler_calendar_flow.sh
#
# Gate: Schedule a content item and verify it appears in the calendar.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export REPO_ROOT

source "$SCRIPT_DIR/lib/auth.sh"
source "$SCRIPT_DIR/lib/http.sh"

echo ""
echo "=================================================="
echo "  Scheduler Calendar Flow Gate"
echo "  BASE_URL: ${BASE_URL}"
echo "=================================================="

# Login
echo ""
echo "1. Login..."
if ! do_login; then
  echo "NO_GO — login failed"
  exit 1
fi
echo "   Token: ${TOKEN:0:20}..."

# Create business
echo ""
echo "2. Create business..."
api_call "POST" "/api/v1/webapps/" \
  '{"name":"Scheduler Flow Business","url":"https://example.com","description":"Local equine training business","category":"equine","target_audience":"Horse owners","key_features":["Training","Livery"]}'
if [[ "$_HTTP_STATUS" != 2* ]] || [[ -z "$_HTTP_BODY" ]]; then
  print_fail "create business" "$_HTTP_STATUS" "$_HTTP_BODY"
  echo "FAIL"; exit 1
fi
WEBAPP_ID="$(_safe_json_field "$_HTTP_BODY" "id")"
echo "   Webapp ID: $WEBAPP_ID"

# Generate content
echo ""
echo "3. Generate content..."
api_call "POST" "/api/v1/content/generate?webapp_id=${WEBAPP_ID}&platform=instagram"
if [[ "$_HTTP_STATUS" != 2* ]] || [[ -z "$_HTTP_BODY" ]]; then
  print_fail "generate content" "$_HTTP_STATUS" "$_HTTP_BODY"
  echo "FAIL"; exit 1
fi
CONTENT_ID="$(_safe_json_field "$_HTTP_BODY" "id")"
echo "   Content ID: $CONTENT_ID"

# Get planned_at (2 hours from now)
PLANNED_AT="$(python3 -c "
from datetime import datetime, timedelta, timezone
print((datetime.now(timezone.utc)+timedelta(hours=2)).isoformat())
")"

# Schedule item
echo ""
echo "4. Schedule content item..."
api_call "POST" "/api/v1/scheduler/items" \
  "{\"content_id\":\"${CONTENT_ID}\",\"planned_at\":\"${PLANNED_AT}\"}"
if [[ "$_HTTP_STATUS" != 2* ]] || [[ -z "$_HTTP_BODY" ]]; then
  print_fail "schedule item" "$_HTTP_STATUS" "$_HTTP_BODY"
  echo "FAIL"; exit 1
fi
if ! python3 -c "
import json, sys
data = json.loads(sys.argv[1])
assert data.get('status') == 'scheduled', f'expected scheduled, got {data.get(\"status\")}'
print(f'  PASS status=scheduled')
" "$_HTTP_BODY" 2>/dev/null; then
  echo "  FAIL scheduler item status unexpected"
  echo "  body: ${_HTTP_BODY:0:500}"
  echo "FAIL"; exit 1
fi
ITEM_ID="$(_safe_json_field "$_HTTP_BODY" "id")"
if [[ -z "$ITEM_ID" ]]; then
  echo "FAIL: no scheduler item id"; exit 1
fi
echo "   Item ID: $ITEM_ID"

# Get calendar bounds
CAL_START="$(python3 -c "
from datetime import datetime, timezone
print(datetime.now(timezone.utc).isoformat())
")"
CAL_END="$(python3 -c "
from datetime import datetime, timedelta, timezone
print((datetime.now(timezone.utc)+timedelta(days=3)).isoformat())
")"

# Verify in calendar
echo ""
echo "5. Verify item in calendar..."
api_call "GET" "/api/v1/scheduler/calendar?start=${CAL_START}&end=${CAL_END}"
if [[ "$_HTTP_STATUS" != 2* ]] || [[ -z "$_HTTP_BODY" ]]; then
  print_fail "scheduler calendar" "$_HTTP_STATUS" "$_HTTP_BODY"
  echo "FAIL"; exit 1
fi
if ! python3 -c "
import json, sys
items = json.loads(sys.argv[1]).get('items', [])
ids = {item.get('id') for item in items}
item_id = sys.argv[2]
assert item_id in ids, f'scheduler item {item_id} missing from calendar'
print(f'PASS: scheduler calendar flow')
" "$_HTTP_BODY" "$ITEM_ID" 2>/dev/null; then
  echo "FAIL: scheduler item missing from calendar"
  echo "  body: ${_HTTP_BODY:0:500}"
  exit 1
fi
