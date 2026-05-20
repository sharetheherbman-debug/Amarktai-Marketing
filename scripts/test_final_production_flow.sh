#!/usr/bin/env bash
# =============================================================================
# scripts/test_final_production_flow.sh
#
# Full production flow gate:
#   1. Backend compile check
#   2. Sub-gate scripts
#   3. Workers + Agents status
#   4. Agents run
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export REPO_ROOT

source "$SCRIPT_DIR/lib/auth.sh"
source "$SCRIPT_DIR/lib/http.sh"

echo ""
echo "=================================================="
echo "  Final Production Flow Gate"
echo "  REPO_ROOT: ${REPO_ROOT}"
echo "  BASE_URL: ${BASE_URL}"
echo "=================================================="

# Backend compile
echo ""
echo "== Backend compile =="
cd "$REPO_ROOT/backend"
./venv/bin/python -m compileall -q app
echo "  PASS backend compiled"

# Sub-gate scripts
echo ""
echo "== API flow scripts =="
bash "$SCRIPT_DIR/test_12_platform_pack.sh"
bash "$SCRIPT_DIR/test_scheduler_calendar_flow.sh"
bash "$SCRIPT_DIR/test_provider_router_flow.sh"
bash "$SCRIPT_DIR/test_business_grounding_quality.sh"
bash "$SCRIPT_DIR/test_generated_content_visibility.sh"
bash "$SCRIPT_DIR/test_login_after_content_rejection.sh"

# Login for remaining checks
echo ""
echo "== Login =="
if ! do_login; then
  echo "NO_GO — login failed"
  exit 1
fi
echo "  Token: ${TOKEN:0:20}..."

# Workers status
echo ""
echo "== Workers status =="
api_call "GET" "/api/v1/workers/status"
if [[ "$_HTTP_STATUS" != 2* ]] || [[ -z "$_HTTP_BODY" ]]; then
  print_fail "workers/status" "$_HTTP_STATUS" "$_HTTP_BODY"
  echo "FAIL"; exit 1
fi
python3 -c "
import json, sys
data = json.loads(sys.argv[1])
workers = data.get('workers', {})
required = {'scheduler_publisher','daily_learning','media_polling','retry_queue'}
missing = required - set(workers.keys())
assert not missing, f'missing worker keys: {missing}'
print(f'  PASS workers status includes all 4 worker keys')
" "$_HTTP_BODY"

# Agents status
echo ""
echo "== Agents status =="
api_call "GET" "/api/v1/agents/status"
if [[ "$_HTTP_STATUS" != 2* ]] || [[ -z "$_HTTP_BODY" ]]; then
  print_fail "agents/status" "$_HTTP_STATUS" "$_HTTP_BODY"
  echo "FAIL"; exit 1
fi
python3 -c "
import json, sys
data = json.loads(sys.argv[1])
assert data.get('agents'), 'no agents returned'
print(f'  PASS {len(data[\"agents\"])} agents registered')
" "$_HTTP_BODY"

# Agents run
echo ""
echo "== Agents run =="
api_call "POST" "/api/v1/agents/run" \
  '{"agent":"CopyAgent","inputs":{"platform":"instagram","objective":"drive leads"}}'
if [[ "$_HTTP_STATUS" != 2* ]] || [[ -z "$_HTTP_BODY" ]]; then
  print_fail "agents/run" "$_HTTP_STATUS" "$_HTTP_BODY"
  echo "FAIL"; exit 1
fi
python3 -c "
import json, sys
data = json.loads(sys.argv[1])
assert data.get('agent') == 'CopyAgent', str(data)
print('  PASS agents/run endpoint responds correctly')
" "$_HTTP_BODY"

echo ""
echo "PASS"
