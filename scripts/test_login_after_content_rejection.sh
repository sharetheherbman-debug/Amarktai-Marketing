#!/usr/bin/env bash
# =============================================================================
# scripts/test_login_after_content_rejection.sh
#
# Gate test: Verify login works before and after content rejection.
# No 500s on auth or dashboard boot endpoints after rejecting a content item.
#
# Usage:
#   MARKETING_TEST_EMAIL=you@example.com MARKETING_TEST_PASSWORD=secret \
#     bash scripts/test_login_after_content_rejection.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export REPO_ROOT

source "$SCRIPT_DIR/lib/auth.sh"
source "$SCRIPT_DIR/lib/http.sh"

PASS=0
FAIL=0

_ok()   { echo "  PASS $1"; ((PASS++)) || true; }
_fail() { echo "  FAIL $1"; ((FAIL++)) || true; }
_info() { echo "  INFO $1"; }

echo ""
echo "========================================="
echo "  Login-After-Rejection Gate Test"
echo "  BASE_URL: ${BASE_URL}"
echo "========================================="

# STEP 1: Login
echo ""
echo "1. Login (${MARKETING_TEST_EMAIL:-<MARKETING_TEST_EMAIL not set>})..."
if ! do_login; then
  echo "NO_GO — login failed"
  exit 1
fi
_ok "Login (HTTP 200, token received)"
_info "Token: ${TOKEN:0:20}..."

# STEP 2: Verify /users/me
echo ""
echo "2. Verify /users/me..."
api_call "GET" "/api/v1/users/me"
if [[ "$_HTTP_STATUS" == 2* ]]; then
  _ok "/users/me (HTTP ${_HTTP_STATUS})"
else
  _fail "/users/me (HTTP ${_HTTP_STATUS})"
fi

# STEP 3: Create test business
echo ""
echo "3. Create test business..."
api_call "POST" "/api/v1/webapps/" '{"name":"Sunrise Equestrian Centre","url":"https://sunrise-equestrian.test","description":"Premium horse riding lessons and equine care","category":"equine","target_audience":"Horse owners and riders","key_features":["Horse riding lessons","Livery services","Equine health care"]}'
WEBAPP_ID=""
if [[ "$_HTTP_STATUS" == 2* ]] && [[ -n "$_HTTP_BODY" ]]; then
  _ok "Create business (HTTP ${_HTTP_STATUS})"
  WEBAPP_ID="$(_safe_json_field "$_HTTP_BODY" "id")"
  _info "Webapp ID: $WEBAPP_ID"
else
  _fail "Create business (HTTP ${_HTTP_STATUS})"
  _info "body: ${_HTTP_BODY:0:500}"
fi

# STEP 4: Generate content
echo ""
echo "4. Generate content for instagram..."
CONTENT_ID=""
if [[ -n "$WEBAPP_ID" ]]; then
  api_call "POST" "/api/v1/content/generate?webapp_id=${WEBAPP_ID}&platform=instagram"
  if [[ "${_HTTP_STATUS:-0}" -lt 500 ]] 2>/dev/null; then
    _ok "Generate content (HTTP ${_HTTP_STATUS} — no 500)"
    if [[ "$_HTTP_STATUS" == 2* ]] && [[ -n "$_HTTP_BODY" ]]; then
      CONTENT_ID="$(_safe_json_field "$_HTTP_BODY" "id")"
    fi
    _info "Content ID: $CONTENT_ID"
  else
    _fail "Generate content (HTTP ${_HTTP_STATUS} — server error)"
  fi
else
  _fail "Cannot generate content — no webapp ID"
fi

# STEP 5: List content library
echo ""
echo "5. List content library..."
if [[ -n "$WEBAPP_ID" ]]; then
  api_call "GET" "/api/v1/content/items?webapp_id=${WEBAPP_ID}"
  if [[ "${_HTTP_STATUS:-0}" -lt 500 ]] 2>/dev/null; then
    _ok "Content library (HTTP ${_HTTP_STATUS})"
  else
    _fail "Content library (HTTP ${_HTTP_STATUS})"
  fi
fi

# STEP 6: Reject content
echo ""
echo "6. Reject content item..."
if [[ -n "$CONTENT_ID" ]]; then
  api_call "POST" "/api/v1/content/items/${CONTENT_ID}/reject" \
    '{"reason":"Wrong hashtags","feedback":"Use horse-specific imagery","regenerate":false}'
  if [[ "${_HTTP_STATUS:-0}" -lt 500 ]] 2>/dev/null; then
    _ok "Reject content (HTTP ${_HTTP_STATUS})"
    if [[ "$_HTTP_STATUS" == 2* ]] && [[ -n "$_HTTP_BODY" ]]; then
      STATUS_AFTER="$(_safe_json_field "$_HTTP_BODY" "status")"
      if [[ "$STATUS_AFTER" == "rejected" ]]; then
        _ok "Content status is 'rejected' after rejection"
      else
        _fail "Expected status=rejected, got '${STATUS_AFTER}'"
      fi
    fi
  else
    _fail "Reject content (HTTP ${_HTTP_STATUS})"
  fi
else
  _fail "No content ID — skipping rejection test"
fi

# STEP 7: Login AGAIN after rejection
echo ""
echo "7. Login AGAIN after content rejection..."
if ! do_login; then
  _fail "Second login failed after rejection"
else
  _ok "Second login successful"
fi
_info "Token: ${TOKEN:0:20}..."

# STEP 8: Dashboard boot endpoints
echo ""
echo "8. Dashboard boot endpoints (with new token)..."
for ENDPOINT in "/api/v1/users/me" "/api/v1/webapps/" "/api/v1/settings/readiness"; do
  api_call "GET" "$ENDPOINT"
  if [[ "${_HTTP_STATUS:-0}" -lt 500 ]] 2>/dev/null; then
    _ok "${ENDPOINT} (HTTP ${_HTTP_STATUS})"
  else
    _fail "${ENDPOINT} (HTTP ${_HTTP_STATUS})"
  fi
done

# STEP 9: Content library after rejection
echo ""
echo "9. Content library after rejection..."
if [[ -n "$WEBAPP_ID" ]]; then
  api_call "GET" "/api/v1/content/items?webapp_id=${WEBAPP_ID}"
  if [[ "${_HTTP_STATUS:-0}" -lt 500 ]] 2>/dev/null; then
    _ok "Content library after rejection (HTTP ${_HTTP_STATUS})"
  else
    _fail "Content library after rejection (HTTP ${_HTTP_STATUS})"
  fi
fi

# STEP 10: Content provenance
echo ""
echo "10. Content provenance endpoint..."
if [[ -n "$WEBAPP_ID" ]]; then
  api_call "GET" "/api/v1/content/provenance?webapp_id=${WEBAPP_ID}"
  if [[ "${_HTTP_STATUS:-0}" -lt 500 ]] 2>/dev/null; then
    _ok "Content provenance (HTTP ${_HTTP_STATUS})"
  else
    _fail "Content provenance (HTTP ${_HTTP_STATUS})"
  fi
fi

# STEP 11: Cleanup
echo ""
echo "11. Cleanup test business..."
if [[ -n "$WEBAPP_ID" ]]; then
  api_call "DELETE" "/api/v1/webapps/${WEBAPP_ID}?confirm=true"
  _info "Delete webapp: HTTP ${_HTTP_STATUS}"
fi

# Summary
echo ""
echo "========================================="
echo "  Results: ${PASS} passed, ${FAIL} failed"
echo "========================================="

if [[ "$FAIL" -gt 0 ]]; then
  echo "FAIL"
  exit 1
else
  echo "PASS"
  exit 0
fi
