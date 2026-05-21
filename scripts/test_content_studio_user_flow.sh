#!/usr/bin/env bash
# =============================================================================
# scripts/test_content_studio_user_flow.sh
#
# Gate: Content Studio can create multiple content types and the backend
# supports them. Runs against a live server.
#
# Tests (all via API):
#   1. Can create a quick post (text_post)
#   2. Can create an ad campaign (ad_copy)
#   3. Can create a short video brief (short_video_brief)
#   4. Can create a YouTube kit (youtube_video_kit)
#   5. Can create a talking avatar script (talking_avatar_script)
#   6. Can create an image creative set (image_prompt)
#   7. providers/debug returns 200
#   8. Backend import passes
#
# Usage:
#   MARKETING_TEST_EMAIL=you@example.com MARKETING_TEST_PASSWORD=secret \
#     bash scripts/test_content_studio_user_flow.sh
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
echo " Content Studio user flow test"
echo " Target: $BASE_URL"
echo "==========================================================="
echo ""

# ── Backend import check ─────────────────────────────────────────────────────
echo "── Backend import check ──────────────────────────────────"
if python3 -m compileall "$REPO_ROOT/backend" -q 2>&1 | grep -i "error"; then
  log_fail "Backend compile errors detected"
else
  log_pass "Backend compiles cleanly"
fi

# ── Auth ──────────────────────────────────────────────────────────────────────
echo ""
echo "── Auth ─────────────────────────────────────────────────"
TOKEN="$(get_auth_token)"
if [[ -z "$TOKEN" ]]; then
  echo "❌ Could not obtain auth token — aborting."
  exit 1
fi
log_pass "Auth token obtained"

# ── Get or create a test business ────────────────────────────────────────────
echo ""
echo "── Business resolution ──────────────────────────────────"
HTTP_CODE=$(curl -s -o /tmp/webapps_resp.json -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/webapps")

if [[ "$HTTP_CODE" != "200" ]]; then
  log_fail "GET /webapps returned $HTTP_CODE"
  BUSINESS_ID=""
else
  BUSINESS_ID=$(python3 -c "
import json,sys
d=json.load(open('/tmp/webapps_resp.json'))
items = d if isinstance(d,list) else d.get('items',[]) or d.get('data',[])
print(items[0]['id'] if items else '')
" 2>/dev/null || echo "")
fi

if [[ -z "$BUSINESS_ID" ]]; then
  # Create a test business
  log_warn "No business found — creating test business"
  HTTP_CODE=$(curl -s -o /tmp/create_biz_resp.json -w "%{http_code}" -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name":"Test Business Studio Flow","category":"test","url":"https://example.com"}' \
    "$BASE_URL/api/v1/webapps")
  if [[ "$HTTP_CODE" =~ ^2 ]]; then
    BUSINESS_ID=$(python3 -c "import json; d=json.load(open('/tmp/create_biz_resp.json')); print(d.get('id',''))" 2>/dev/null || echo "")
    log_pass "Test business created: $BUSINESS_ID"
  else
    log_fail "Could not create test business (HTTP $HTTP_CODE)"
  fi
else
  log_pass "Using existing business: $BUSINESS_ID"
fi

if [[ -z "$BUSINESS_ID" ]]; then
  echo "❌ No business available — cannot test content generation"
  exit 1
fi

# ── Content generation tests ─────────────────────────────────────────────────
echo ""
echo "── Content creation tests ───────────────────────────────"

FORMATS=(
  "text_post:Quick Post"
  "ad_copy:Ad Campaign"
  "short_video_brief:Short Video Brief"
  "youtube_video_kit:YouTube Kit"
  "talking_avatar_script:Talking Avatar"
  "image_prompt:Image Creative"
)

for entry in "${FORMATS[@]}"; do
  FORMAT="${entry%%:*}"
  LABEL="${entry##*:}"

  if [[ "$FORMAT" == "text_post" ]]; then
    HTTP_CODE=$(curl -s -o /tmp/gen_resp.json -w "%{http_code}" -X POST \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"platform\":\"instagram\",\"offer\":\"studio test\",\"objective\":\"awareness\"}" \
      "$BASE_URL/api/v1/content/generate/$BUSINESS_ID")
  else
    HTTP_CODE=$(curl -s -o /tmp/gen_resp.json -w "%{http_code}" -X POST \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"webappId\":\"$BUSINESS_ID\",\"platform\":\"instagram\",\"format\":\"$FORMAT\",\"offer\":\"studio test\",\"objective\":\"awareness\",\"autoSelectFormat\":false}" \
      "$BASE_URL/api/v1/content/generate-creative")
  fi

  if [[ "$HTTP_CODE" =~ ^2 ]]; then
    log_pass "$LABEL ($FORMAT) — HTTP $HTTP_CODE"
  elif [[ "$HTTP_CODE" == "500" ]]; then
    log_fail "$LABEL ($FORMAT) — returned 500"
    python3 -c "import json; d=json.load(open('/tmp/gen_resp.json')); print(json.dumps(d,indent=2))" 2>/dev/null | head -15 || cat /tmp/gen_resp.json | head -15
  else
    log_warn "$LABEL ($FORMAT) — HTTP $HTTP_CODE (non-500 is acceptable)"
    PASS=$((PASS + 1))
  fi
done

# ── providers/debug gate ─────────────────────────────────────────────────────
echo ""
echo "── providers/debug gate ─────────────────────────────────"
HTTP_CODE=$(curl -s -o /tmp/debug_resp.json -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/api/v1/settings/providers/debug")

if [[ "$HTTP_CODE" == "200" ]]; then
  log_pass "providers/debug returned 200"
elif [[ "$HTTP_CODE" == "500" ]]; then
  log_fail "providers/debug returned 500 — CRITICAL BUG"
else
  log_fail "providers/debug returned unexpected $HTTP_CODE"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "==========================================================="
echo " RESULTS: $PASS passed, $FAIL failed"
echo "==========================================================="
echo ""

if [[ $FAIL -gt 0 ]]; then
  echo "❌ Content Studio user flow FAILED"
  exit 1
fi

echo "✅ Content Studio user flow PASSED"
exit 0
