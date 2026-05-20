#!/usr/bin/env bash
# =============================================================================
# scripts/test_12_platform_pack.sh
#
# Gate: Generate a content pack for all 12 launch platforms and verify each
#       platform appears at least once in the response.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export REPO_ROOT

source "$SCRIPT_DIR/lib/auth.sh"
source "$SCRIPT_DIR/lib/http.sh"

echo ""
echo "=================================================="
echo "  12-Platform Pack Gate"
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
  '{"name":"12 Platform Pack Business","url":"https://example.com","description":"Cyber security services for SMBs","category":"cyber security","target_audience":"SMB owners","key_features":["SOC support","Risk reduction","Compliance help"]}'
if [[ "$_HTTP_STATUS" != 2* ]] || [[ -z "$_HTTP_BODY" ]]; then
  print_fail "create business" "$_HTTP_STATUS" "$_HTTP_BODY"
  echo "FAIL"; exit 1
fi
WEBAPP_ID="$(_safe_json_field "$_HTTP_BODY" "id")"
if [[ -z "$WEBAPP_ID" ]]; then
  echo "FAIL: no webapp id"; exit 1
fi
echo "   Webapp ID: $WEBAPP_ID"

# Generate 12-platform pack
echo ""
echo "3. Generate 12-platform pack..."
api_call "POST" "/api/v1/content/generate-pack" \
  "{\"webapp_id\":\"${WEBAPP_ID}\",\"platforms\":[\"instagram\",\"facebook\",\"linkedin\",\"twitter\",\"tiktok\",\"youtube\",\"reddit\",\"pinterest\",\"threads\",\"bluesky\",\"telegram\",\"snapchat\"],\"auto_select_formats\":true}"
if [[ "$_HTTP_STATUS" != 2* ]] || [[ -z "$_HTTP_BODY" ]]; then
  print_fail "generate-pack" "$_HTTP_STATUS" "$_HTTP_BODY"
  echo "FAIL"; exit 1
fi

if ! python3 -c "
import json, sys
data = json.loads(sys.argv[1])
assert data.get('count', 0) >= 12, f'expected >=12 items, got {data.get(\"count\")}'
platforms = {item.get('platform') for item in data.get('items', []) if isinstance(item, dict)}
required = {'instagram','facebook','linkedin','twitter','tiktok','youtube','reddit','pinterest','threads','bluesky','telegram','snapchat'}
missing = sorted(required - platforms)
assert not missing, f'missing platforms: {missing}'
print(f'PASS: 12-platform pack generated ({data[\"count\"]} items)')
" "$_HTTP_BODY" 2>&1; then
  echo "FAIL: 12-platform pack assertion failed"
  echo "  body: ${_HTTP_BODY:0:1000}"
  exit 1
fi
