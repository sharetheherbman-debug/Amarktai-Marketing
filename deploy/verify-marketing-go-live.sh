#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${DOMAIN:-marketing.amarktai.com}"
BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://127.0.0.1:8010}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://${DOMAIN}}"

check_status() {
  local label="$1"
  local expected="$2"
  shift 2
  local status
  status="$("$@" 2>/dev/null)"
  if [[ "${status}" == "${expected}" ]]; then
    printf 'PASS %-32s -> %s\n' "${label}" "${status}"
  else
    printf 'FAIL %-32s -> expected %s, got %s\n' "${label}" "${expected}" "${status:-<empty>}" >&2
    return 1
  fi
}

echo "Verifying marketing.amarktai.com go-live path..."

check_status "backend /health" "200" curl -fsS -o /dev/null -w "%{http_code}" -H "Host: ${DOMAIN}" "${BACKEND_BASE_URL}/health"
check_status "backend /api/v1/health" "200" curl -fsS -o /dev/null -w "%{http_code}" -H "Host: ${DOMAIN}" "${BACKEND_BASE_URL}/api/v1/health"
check_status "public /" "200" curl -fsS -o /dev/null -w "%{http_code}" "${PUBLIC_BASE_URL}/"
check_status "public /api/v1/health" "200" curl -fsS -o /dev/null -w "%{http_code}" "${PUBLIC_BASE_URL}/api/v1/health"
check_status "public /docs" "200" curl -fsS -o /dev/null -w "%{http_code}" "${PUBLIC_BASE_URL}/docs"
check_status "public /openapi.json" "200" curl -fsS -o /dev/null -w "%{http_code}" "${PUBLIC_BASE_URL}/openapi.json"

echo "All go-live checks passed."
