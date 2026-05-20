#!/usr/bin/env bash
# =============================================================================
# scripts/lib/http.sh — robust curl/json helper for gate scripts
#
# Usage (source this file):
#   source "$(dirname "${BASH_SOURCE[0]}")/../lib/http.sh"
#
# Functions provided:
#   api_call METHOD PATH [BODY]       — runs curl, sets _HTTP_STATUS / _HTTP_BODY
#   assert_json_2xx METHOD PATH [BODY] — fails (exit 1) if not 2xx or not JSON
#   print_fail ENDPOINT STATUS BODY   — prints structured failure
#
# Requires TOKEN to be set (by auth.sh:do_login).
# Requires BASE_URL to be set (default http://127.0.0.1:8010).
# =============================================================================

BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"

_HTTP_STATUS=""
_HTTP_BODY=""

# ── api_call ──────────────────────────────────────────────────────────────────
# api_call METHOD PATH [BODY]
# Captures status into _HTTP_STATUS and body into _HTTP_BODY.
# Returns 0 always; caller checks _HTTP_STATUS.
api_call() {
  local method="${1:?api_call: METHOD required}"
  local path="${2:?api_call: PATH required}"
  local body="${3:-}"

  local tmp_body
  tmp_body="$(mktemp)"
  local curl_args=(-sS -X "$method" "${BASE_URL}${path}" -o "$tmp_body" -w "%{http_code}")

  curl_args+=(-H "Content-Type: application/json")
  if [[ -n "${TOKEN:-}" ]]; then
    curl_args+=(-H "Authorization: Bearer ${TOKEN}")
  fi
  if [[ -n "$body" ]]; then
    curl_args+=(-d "$body")
  fi

  _HTTP_STATUS="$(curl "${curl_args[@]}" 2>/dev/null || echo "000")"
  _HTTP_BODY="$(cat "$tmp_body")"
  rm -f "$tmp_body"
}

# ── assert_json_2xx ───────────────────────────────────────────────────────────
# assert_json_2xx METHOD PATH [BODY] [LABEL]
# Calls api_call, then verifies:
#   1. HTTP status is 2xx
#   2. Body is non-empty
# Prints PASS/FAIL and exits 1 on failure.
assert_json_2xx() {
  local method="${1:?assert_json_2xx: METHOD required}"
  local path="${2:?assert_json_2xx: PATH required}"
  local body="${3:-}"
  local label="${4:-${method} ${path}}"

  api_call "$method" "$path" "$body"

  if [[ "$_HTTP_STATUS" != 2* ]]; then
    print_fail "$label" "$_HTTP_STATUS" "$_HTTP_BODY"
    return 1
  fi

  if [[ -z "$_HTTP_BODY" ]]; then
    echo "FAIL [$label] HTTP ${_HTTP_STATUS} but body is empty" >&2
    return 1
  fi

  echo "PASS [$label] HTTP ${_HTTP_STATUS}"
  return 0
}

# ── print_fail ────────────────────────────────────────────────────────────────
print_fail() {
  local endpoint="${1:-unknown}"
  local status="${2:-000}"
  local body="${3:-}"
  echo "FAIL [$endpoint] HTTP ${status}" >&2
  if [[ -n "$body" ]]; then
    echo "  body: ${body:0:2000}" >&2
  else
    echo "  body: (empty)" >&2
  fi
}

# ── _safe_json_field ─────────────────────────────────────────────────────────
# _safe_json_field BODY FIELD — extracts string field from JSON, or empty
_safe_json_field() {
  local body="${1:-}"
  local field="${2:?_safe_json_field: FIELD required}"
  if [[ -z "$body" ]]; then echo ""; return 0; fi
  if command -v jq &>/dev/null; then
    printf '%s' "$body" | jq -r --arg f "$field" '.[$f] // empty' 2>/dev/null || true
  else
    python3 - <<'PY' "$body" "$field" 2>/dev/null || true
import json, sys
d = {}
try:
    d = json.loads(sys.argv[1])
except Exception:
    pass
print(d.get(sys.argv[2]) or "")
PY
  fi
}
