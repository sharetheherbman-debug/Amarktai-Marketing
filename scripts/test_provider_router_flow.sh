#!/usr/bin/env bash
# =============================================================================
# scripts/test_provider_router_flow.sh
#
# Gate: Provider router returns a selected provider and fallback chain.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export REPO_ROOT

source "$SCRIPT_DIR/lib/auth.sh"
source "$SCRIPT_DIR/lib/http.sh"

echo ""
echo "=================================================="
echo "  Provider Router Flow Gate"
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

# Test provider router
echo ""
echo "2. Test capabilities/route..."
api_call "POST" "/api/v1/capabilities/route" \
  '{"capability":"platform_copy","platform":"instagram","format":"text_post","budget_mode":"budget","business":{"name":"Budget Test Business","category":"cyber security"}}'

if [[ "$_HTTP_STATUS" != 2* ]] || [[ -z "$_HTTP_BODY" ]]; then
  print_fail "capabilities/route" "$_HTTP_STATUS" "$_HTTP_BODY"
  echo "FAIL"; exit 1
fi

if ! python3 -c "
import json, sys
data = json.loads(sys.argv[1])
assert data.get('selected_provider'), f'no selected_provider: {data}'
assert isinstance(data.get('fallback_chain'), list) and data['fallback_chain'], f'no fallback_chain: {data}'
print(f'PASS: provider router flow — provider={data[\"selected_provider\"]}')
" "$_HTTP_BODY" 2>/dev/null; then
  echo "FAIL: provider router assertion failed"
  echo "  body: ${_HTTP_BODY:0:500}"
  exit 1
fi
