#!/usr/bin/env bash
# =============================================================================
# scripts/test_providers_debug_no_500.sh
#
# Gate: GET /api/v1/settings/providers/debug must return 200 JSON
# even when ALL provider keys are missing.
#
# Also checks that each provider block is present and structured correctly.
#
# Usage:
#   MARKETING_TEST_EMAIL=you@example.com MARKETING_TEST_PASSWORD=secret \
#     bash scripts/test_providers_debug_no_500.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export REPO_ROOT

source "$SCRIPT_DIR/lib/auth.sh"
source "$SCRIPT_DIR/lib/http.sh"

BASE_URL="${MARKETING_TEST_BASE_URL:-http://localhost:8010}"
PASS=0
FAIL=0
WARNS=()

log_pass() { echo "  ✅ PASS  $1"; PASS=$((PASS + 1)); }
log_fail() { echo "  ❌ FAIL  $1"; FAIL=$((FAIL + 1)); }
log_warn() { echo "  ⚠️  WARN  $1"; WARNS+=("$1"); }

echo ""
echo "==========================================================="
echo " providers/debug no-500 gate"
echo " Target: $BASE_URL"
echo "==========================================================="
echo ""

# ── Auth ──────────────────────────────────────────────────────────────────────
TOKEN="$(get_auth_token)"
if [[ -z "$TOKEN" ]]; then
  echo "❌ Could not obtain auth token — aborting."
  exit 1
fi
echo "  ✅ Auth token obtained"

# ── GET /api/v1/settings/providers/debug ─────────────────────────────────────
echo ""
echo "── GET /api/v1/settings/providers/debug ──────────────────"
HTTP_CODE=$(curl -s -o /tmp/providers_debug_resp.json -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/settings/providers/debug")

echo "  HTTP status: $HTTP_CODE"

if [[ "$HTTP_CODE" == "500" ]]; then
  log_fail "providers/debug returned 500 — BUG NOT FIXED"
  cat /tmp/providers_debug_resp.json 2>/dev/null || true
  exit 1
fi

if [[ "$HTTP_CODE" != "200" ]]; then
  log_fail "providers/debug returned unexpected status $HTTP_CODE"
  exit 1
fi

log_pass "providers/debug returned 200"

# Validate JSON
if ! python3 -c "import json,sys; json.load(open('/tmp/providers_debug_resp.json'))" 2>/dev/null; then
  log_fail "providers/debug response is not valid JSON"
  cat /tmp/providers_debug_resp.json
  exit 1
fi
log_pass "Response is valid JSON"

# ── Check each provider block ─────────────────────────────────────────────────
echo ""
echo "── Provider block checks ─────────────────────────────────"

PROVIDERS=("genx" "firecrawl" "qwen" "huggingface" "pixabay")

for provider in "${PROVIDERS[@]}"; do
  block=$(python3 -c "
import json, sys
data = json.load(open('/tmp/providers_debug_resp.json'))
block = data.get('$provider')
if block is None:
    print('MISSING')
elif not isinstance(block, dict):
    print('NOT_DICT')
else:
    status = block.get('status') or block.get('task_status') or block.get('test_status') or 'present'
    print(status)
" 2>/dev/null || echo "ERROR")

  if [[ "$block" == "MISSING" ]]; then
    log_fail "Provider block '$provider' is missing from response"
  elif [[ "$block" == "NOT_DICT" ]]; then
    log_fail "Provider block '$provider' is not a dict"
  elif [[ "$block" == "ERROR" ]]; then
    log_fail "Error reading provider block '$provider'"
  else
    # Any non-500 structured status is acceptable when keys are missing
    log_pass "Provider '$provider' block present, status: $block"
  fi
done

# ── Error status check (should not be raw Python exception) ─────────────────
echo ""
echo "── Error sanitization check ──────────────────────────────"
if grep -qi "NameError\|TypeError\|AttributeError\|traceback" /tmp/providers_debug_resp.json 2>/dev/null; then
  log_fail "Raw Python exception found in response — errors not sanitized"
else
  log_pass "No raw Python exceptions in response"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "==========================================================="
echo " RESULTS: $PASS passed, $FAIL failed"
if [[ ${#WARNS[@]} -gt 0 ]]; then
  echo " WARNINGS:"
  for w in "${WARNS[@]}"; do echo "   - $w"; done
fi
echo "==========================================================="
echo ""

if [[ $FAIL -gt 0 ]]; then
  echo "❌ providers/debug gate FAILED"
  exit 1
fi

echo "✅ providers/debug gate PASSED — no 500 errors"
exit 0
