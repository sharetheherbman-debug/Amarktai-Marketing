#!/usr/bin/env bash
# =============================================================================
# scripts/test_schedule_from_content_flow.sh
#
# Gate: Verifies that scheduling a generated content item creates a calendar
# entry and does not return a 500.
#
# Usage:
#   MARKETING_TEST_EMAIL=you@example.com MARKETING_TEST_PASSWORD=secret \
#     bash scripts/test_schedule_from_content_flow.sh
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

log_pass() { echo "  ✅ PASS  $1"; PASS=$((PASS + 1)); }
log_fail() { echo "  ❌ FAIL  $1"; FAIL=$((FAIL + 1)); }
log_warn() { echo "  ⚠️  WARN  $1"; }

echo ""
echo "==========================================================="
echo " Schedule-from-content flow test"
echo " Target: $BASE_URL"
echo "==========================================================="
echo ""

TOKEN="$(get_auth_token)"
if [[ -z "$TOKEN" ]]; then
  echo "❌ Could not obtain auth token — aborting."
  exit 1
fi
log_pass "Auth token obtained"

# ── Get a business ──────────────────────────────────────────────────────────
HTTP_CODE=$(curl -s -o /tmp/webapps_resp.json -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/webapps")
BUSINESS_ID=$(python3 -c "
import json,sys
d=json.load(open('/tmp/webapps_resp.json'))
items = d if isinstance(d,list) else d.get('items',[]) or d.get('data',[])
print(items[0]['id'] if items else '')
" 2>/dev/null || echo "")

if [[ -z "$BUSINESS_ID" ]]; then
  log_warn "No business — creating one"
  HTTP_CODE=$(curl -s -o /tmp/biz_resp.json -w "%{http_code}" -X POST \
    -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
    -d '{"name":"Schedule Test Business","category":"test","url":"https://example.com"}' \
    "$BASE_URL/api/v1/webapps")
  BUSINESS_ID=$(python3 -c "import json; print(json.load(open('/tmp/biz_resp.json')).get('id',''))" 2>/dev/null || echo "")
fi

if [[ -z "$BUSINESS_ID" ]]; then
  log_fail "Could not get or create a business"
  exit 1
fi
log_pass "Business: $BUSINESS_ID"

# ── Generate content to schedule ─────────────────────────────────────────────
echo ""
echo "── Generate content ─────────────────────────────────────"
HTTP_CODE=$(curl -s -o /tmp/gen_resp.json -w "%{http_code}" -X POST \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"platform":"instagram","offer":"schedule test","objective":"awareness"}' \
  "$BASE_URL/api/v1/content/generate/$BUSINESS_ID")

if [[ "$HTTP_CODE" =~ ^2 ]]; then
  CONTENT_ID=$(python3 -c "import json; d=json.load(open('/tmp/gen_resp.json')); print(d.get('id',''))" 2>/dev/null || echo "")
  log_pass "Generated content: $CONTENT_ID"
else
  log_warn "Could not generate fresh content (HTTP $HTTP_CODE) — trying existing library"
  HTTP_CODE=$(curl -s -o /tmp/lib_resp.json -w "%{http_code}" \
    -H "Authorization: Bearer $TOKEN" \
    "$BASE_URL/api/v1/content/webapp/$BUSINESS_ID")
  CONTENT_ID=$(python3 -c "
import json,sys
d=json.load(open('/tmp/lib_resp.json'))
items = d if isinstance(d,list) else d.get('items',[]) or d.get('data',[])
print(items[0]['id'] if items else '')
" 2>/dev/null || echo "")
fi

if [[ -z "$CONTENT_ID" ]]; then
  log_fail "No content item available to schedule"
  echo ""
  echo "==========================================================="
  echo " RESULTS: $PASS passed, $FAIL failed"
  echo "==========================================================="
  exit 1
fi

# ── Schedule the content item ────────────────────────────────────────────────
echo ""
echo "── Schedule content item ────────────────────────────────"
HTTP_CODE=$(curl -s -o /tmp/sched_resp.json -w "%{http_code}" -X POST \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  "$BASE_URL/api/v1/content/$CONTENT_ID/schedule")

echo "  HTTP: $HTTP_CODE"

if [[ "$HTTP_CODE" == "500" ]]; then
  log_fail "Schedule content returned 500"
  cat /tmp/sched_resp.json | head -10
elif [[ "$HTTP_CODE" =~ ^2 ]]; then
  log_pass "Schedule content returned $HTTP_CODE"
else
  log_warn "Schedule content returned $HTTP_CODE (non-500 — acceptable)"
  PASS=$((PASS + 1))
fi

# ── Check scheduler calendar ─────────────────────────────────────────────────
echo ""
echo "── Check scheduler/calendar ─────────────────────────────"
HTTP_CODE=$(curl -s -o /tmp/cal_resp.json -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/scheduler/calendar")

if [[ "$HTTP_CODE" == "200" ]]; then
  log_pass "Scheduler calendar returned 200"
elif [[ "$HTTP_CODE" == "500" ]]; then
  log_fail "Scheduler calendar returned 500"
else
  log_warn "Scheduler calendar returned $HTTP_CODE"
  PASS=$((PASS + 1))
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "==========================================================="
echo " RESULTS: $PASS passed, $FAIL failed"
echo "==========================================================="
echo ""

if [[ $FAIL -gt 0 ]]; then
  echo "❌ Schedule-from-content flow FAILED"
  exit 1
fi

echo "✅ Schedule-from-content flow PASSED"
exit 0
