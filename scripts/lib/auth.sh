#!/usr/bin/env bash
# =============================================================================
# scripts/lib/auth.sh — shared auth helper for gate scripts
#
# Usage (source this file):
#   source "$(dirname "${BASH_SOURCE[0]}")/../lib/auth.sh"
#   do_login   # sets TOKEN and exports it
#
# Required env vars:
#   MARKETING_TEST_EMAIL     e.g. amarktainetwork@gmail.com
#   MARKETING_TEST_PASSWORD  e.g. ChangeMeNow2026!
#
# Optional env vars:
#   BASE_URL                 default: http://127.0.0.1:8010
#   ENABLE_TEST_REGISTRATION true — only if you want random-user registration
# =============================================================================

# Resolve REPO_ROOT once when sourced
if [[ -z "${REPO_ROOT:-}" ]]; then
  REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
  export REPO_ROOT
fi

BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"

# ── Validate required vars ────────────────────────────────────────────────────
_auth_check_env() {
  local missing=0
  if [[ -z "${MARKETING_TEST_EMAIL:-}" ]]; then
    echo "AUTH_ERROR: MARKETING_TEST_EMAIL is not set" >&2
    missing=1
  fi
  if [[ -z "${MARKETING_TEST_PASSWORD:-}" ]]; then
    echo "AUTH_ERROR: MARKETING_TEST_PASSWORD is not set" >&2
    missing=1
  fi
  return $missing
}

# ── Login with email/password — sets TOKEN ────────────────────────────────────
do_login() {
  _auth_check_env || return 1

  local tmp_body
  tmp_body="$(mktemp)"
  local http_status
  http_status="$(curl -sS \
    -o "$tmp_body" \
    -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${MARKETING_TEST_EMAIL}\",\"password\":\"${MARKETING_TEST_PASSWORD}\"}" \
    2>/dev/null || echo "000")"

  local body
  body="$(cat "$tmp_body")"
  rm -f "$tmp_body"

  if [[ "$http_status" != 2* ]]; then
    echo "AUTH_FAIL: login returned HTTP $http_status" >&2
    echo "  body: ${body:0:2000}" >&2
    return 1
  fi

  if [[ -z "$body" ]]; then
    echo "AUTH_FAIL: login returned empty body (HTTP $http_status)" >&2
    return 1
  fi

  # Extract token — use jq if available, else python3
  if command -v jq &>/dev/null; then
    TOKEN="$(printf '%s' "$body" | jq -r '.access_token // empty' 2>/dev/null || true)"
  else
    TOKEN="$(python3 - <<'PY' "$body" 2>/dev/null || true
import json, sys
d = {}
try:
    d = json.loads(sys.argv[1])
except Exception:
    pass
print(d.get("access_token") or "")
PY
)"
  fi

  if [[ -z "$TOKEN" ]]; then
    echo "AUTH_FAIL: no access_token in login response (HTTP $http_status)" >&2
    echo "  body: ${body:0:2000}" >&2
    return 1
  fi

  export TOKEN
  return 0
}

# ── Optional test registration (only when ENABLE_TEST_REGISTRATION=true) ──────
do_register_test_user() {
  if [[ "${ENABLE_TEST_REGISTRATION:-false}" != "true" ]]; then
    echo "AUTH_INFO: registration skipped (set ENABLE_TEST_REGISTRATION=true to enable)" >&2
    return 0
  fi

  local email="${1:-${MARKETING_TEST_EMAIL}}"
  local password="${2:-${MARKETING_TEST_PASSWORD}}"
  local name="${3:-Test User}"

  local tmp_body
  tmp_body="$(mktemp)"
  local http_status
  http_status="$(curl -sS \
    -o "$tmp_body" \
    -w "%{http_code}" \
    -X POST "${BASE_URL}/api/v1/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${email}\",\"password\":\"${password}\",\"name\":\"${name}\"}" \
    2>/dev/null || echo "000")"

  local body
  body="$(cat "$tmp_body")"
  rm -f "$tmp_body"

  if [[ "$http_status" == "201" || "$http_status" == "409" ]]; then
    return 0
  fi

  echo "AUTH_FAIL: registration returned HTTP $http_status" >&2
  echo "  body: ${body:0:2000}" >&2
  return 1
}
