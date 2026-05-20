#!/usr/bin/env bash
# =============================================================================
# scripts/test_business_grounding_quality.sh
#
# Gate: Generated content has high business grounding score, contains
#       industry-relevant terms, and has no Amarktai hashtags.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export REPO_ROOT

source "$SCRIPT_DIR/lib/auth.sh"
source "$SCRIPT_DIR/lib/http.sh"

echo ""
echo "=================================================="
echo "  Business Grounding Quality Gate"
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

# Create equine business
echo ""
echo "2. Create equine business..."
api_call "POST" "/api/v1/webapps/" \
  '{"name":"Horse Care Pro","url":"https://example.com","description":"Horse care and riding support","category":"equine","target_audience":"Horse owners","key_features":["Horse care","Riding support","Stable advice"]}'
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

# Assert grounding quality
if ! python3 -c "
import json, sys
data = json.loads(sys.argv[1])
metadata = data.get('generation_metadata') or {}
caption = (data.get('caption') or '').lower()
hashtags = ' '.join(data.get('hashtags') or []).lower()
assert 'amarktai' not in hashtags, f'amarktai hashtag found: {hashtags}'
score = metadata.get('business_grounding_score', 0)
assert score >= 70, f'grounding score too low: {score}'
assert any(term in caption for term in ['horse','equine','stable','riding']), f'no equine terms in caption: {caption}'
print(f'PASS: business grounding quality (score={score})')
" "$_HTTP_BODY" 2>/dev/null; then
  echo "FAIL: business grounding quality assertion failed"
  echo "  body: ${_HTTP_BODY:0:500}"
  exit 1
fi
