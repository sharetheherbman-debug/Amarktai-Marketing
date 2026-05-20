#!/usr/bin/env bash
# =============================================================================
# scripts/test_core_endpoint_smoke.sh
#
# Core endpoint smoke test — verifies all critical API endpoints return 2xx JSON.
#
# Usage:
#   MARKETING_TEST_EMAIL=you@example.com MARKETING_TEST_PASSWORD=secret \
#     bash scripts/test_core_endpoint_smoke.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export REPO_ROOT

# shellcheck source=lib/auth.sh
source "$SCRIPT_DIR/lib/auth.sh"
# shellcheck source=lib/http.sh
source "$SCRIPT_DIR/lib/http.sh"

PASS=0
FAIL=0

_ok()   { echo "  PASS $1"; ((PASS++)) || true; }
_fail() { echo "  FAIL $1"; ((FAIL++)) || true; }

echo ""
echo "=================================================="
echo "  Core Endpoint Smoke Test"
echo "  BASE_URL: ${BASE_URL}"
echo "=================================================="

# ── Login ─────────────────────────────────────────────────────────────────────
echo ""
echo "1. Login..."
if ! do_login; then
  echo ""
  echo "NO_GO — login failed, cannot continue"
  exit 1
fi
echo "   Token: ${TOKEN:0:20}..."

# ── Endpoints to smoke ────────────────────────────────────────────────────────
ENDPOINTS=(
  "/api/v1/integrations/platforms"
  "/api/v1/platform-intelligence"
  "/api/v1/capabilities"
  "/api/v1/workers/status"
  "/api/v1/agents/status"
  "/api/v1/learning/status"
  "/api/v1/media/jobs"
  "/api/v1/media/assets"
  "/api/v1/scheduler/items"
  "/api/v1/settings/provider-resolution"
  "/api/v1/settings/readiness"
)

echo ""
echo "2. Checking ${#ENDPOINTS[@]} endpoints..."
for ep in "${ENDPOINTS[@]}"; do
  api_call "GET" "$ep" ""
  if [[ "$_HTTP_STATUS" == 2* ]] && [[ -n "$_HTTP_BODY" ]]; then
    _ok "$ep (HTTP ${_HTTP_STATUS})"
  else
    _fail "$ep (HTTP ${_HTTP_STATUS})"
    if [[ "$_HTTP_STATUS" != 2* ]]; then
      echo "     body: ${_HTTP_BODY:0:500}" >&2
    fi
  fi
done

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "=================================================="
echo "  Results: ${PASS} passed, ${FAIL} failed"
echo "=================================================="

if [[ "$FAIL" -gt 0 ]]; then
  echo "FAIL"
  exit 1
else
  echo "PASS"
  exit 0
fi
