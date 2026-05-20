#!/usr/bin/env bash
# =============================================================================
# scripts/test_generated_content_visibility.sh
#
# Gate: Generated content persists and is visible in content library and
#       webapp content listing; deletion removes it.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export REPO_ROOT

source "$SCRIPT_DIR/lib/auth.sh"
source "$SCRIPT_DIR/lib/http.sh"

echo ""
echo "=================================================="
echo "  Generated Content Visibility Gate"
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
api_call "POST" "/api/v1/webapps/" '{"name":"Visibility Gate Business","url":"https://example.com"}'
if [[ "$_HTTP_STATUS" != 2* ]] || [[ -z "$_HTTP_BODY" ]]; then
  print_fail "create business" "$_HTTP_STATUS" "$_HTTP_BODY"
  echo "FAIL"; exit 1
fi
WEBAPP_ID="$(_safe_json_field "$_HTTP_BODY" "id")"
if [[ -z "$WEBAPP_ID" ]]; then
  echo "FAIL: business id missing"; exit 1
fi
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
if [[ -z "$CONTENT_ID" ]]; then
  echo "FAIL: generate content did not return id"; exit 1
fi
echo "   Content ID: $CONTENT_ID"

# Get single item
echo ""
echo "4. Get content item by id..."
assert_json_2xx "GET" "/api/v1/content/items/${CONTENT_ID}" "" "get content item" || { echo "FAIL"; exit 1; }

# Verify appears in webapp content listing
echo ""
echo "5. Verify in webapp content listing..."
api_call "GET" "/api/v1/content/webapp/${WEBAPP_ID}"
if [[ "$_HTTP_STATUS" != 2* ]] || [[ -z "$_HTTP_BODY" ]]; then
  print_fail "get content for webapp" "$_HTTP_STATUS" "$_HTTP_BODY"
  echo "FAIL"; exit 1
fi
if ! echo "$_HTTP_BODY" | python3 -c "
import json, sys
items = json.load(sys.stdin)
ids = {item.get('id') for item in items if isinstance(item, dict)}
import sys as _sys
cid = _sys.argv[1] if len(_sys.argv) > 1 else ''
assert cid in ids, f'generated content {cid} missing from webapp listing'
print('  PASS content visible in webapp listing')
" "$CONTENT_ID" 2>/dev/null; then
  echo "  FAIL generated content missing from webapp listing"
  echo "FAIL"; exit 1
fi

# Generate pack
echo ""
echo "6. Generate pack..."
api_call "POST" "/api/v1/content/generate-pack" \
  "{\"webapp_id\":\"${WEBAPP_ID}\",\"platforms\":[\"instagram\"],\"auto_select_formats\":true}"
if [[ "$_HTTP_STATUS" != 2* ]] || [[ -z "$_HTTP_BODY" ]]; then
  print_fail "generate-pack" "$_HTTP_STATUS" "$_HTTP_BODY"
  echo "FAIL"; exit 1
fi
if ! python3 -c "
import json, sys
data = json.loads(sys.argv[1])
assert data.get('count', 0) >= 1, f'pack generation returned no items'
print('  PASS pack generated')
" "$_HTTP_BODY" 2>/dev/null; then
  echo "  FAIL pack assertion failed"
  echo "FAIL"; exit 1
fi

# Library has 2+ items
echo ""
echo "7. Check content library has generated+pack items..."
api_call "GET" "/api/v1/content/items?webapp_id=${WEBAPP_ID}"
if [[ "$_HTTP_STATUS" != 2* ]] || [[ -z "$_HTTP_BODY" ]]; then
  print_fail "content library" "$_HTTP_STATUS" "$_HTTP_BODY"
  echo "FAIL"; exit 1
fi
if ! python3 -c "
import json, sys
items = json.loads(sys.argv[1])
assert isinstance(items, list), 'library did not return list'
assert len(items) >= 2, f'expected generated+pack items, got {len(items)}'
print(f'  PASS library has {len(items)} items')
" "$_HTTP_BODY" 2>/dev/null; then
  echo "  FAIL library count assertion failed"
  echo "FAIL"; exit 1
fi

# Delete content item
echo ""
echo "8. Delete content item..."
api_call "DELETE" "/api/v1/content/items/${CONTENT_ID}?confirm=true"
if [[ "$_HTTP_STATUS" -ge 500 ]]; then
  print_fail "delete content item" "$_HTTP_STATUS" "$_HTTP_BODY"
  echo "FAIL"; exit 1
fi
echo "   HTTP ${_HTTP_STATUS}"

# Verify deleted
echo ""
echo "9. Verify content deleted from webapp listing..."
api_call "GET" "/api/v1/content/webapp/${WEBAPP_ID}"
if [[ "$_HTTP_STATUS" != 2* ]] || [[ -z "$_HTTP_BODY" ]]; then
  print_fail "verify delete" "$_HTTP_STATUS" "$_HTTP_BODY"
  echo "FAIL"; exit 1
fi
if ! python3 -c "
import json, sys
items = json.loads(sys.argv[1])
ids = {item.get('id') for item in items if isinstance(item, dict)}
cid = sys.argv[2] if len(sys.argv) > 2 else ''
assert cid not in ids, 'deleted content still present'
print('  PASS deleted content absent')
" "$_HTTP_BODY" "$CONTENT_ID" 2>/dev/null; then
  echo "  FAIL deleted content still present"
  echo "FAIL"; exit 1
fi

# Cleanup
echo ""
echo "10. Cleanup business..."
api_call "DELETE" "/api/v1/webapps/${WEBAPP_ID}?confirm=true"
echo "   HTTP ${_HTTP_STATUS}"

echo ""
echo "PASS: generated content visibility gate completed"
