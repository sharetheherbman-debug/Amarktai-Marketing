#!/usr/bin/env bash

set -euo pipefail

DOMAIN="${DOMAIN:-builder.amarktai.com}"
BACKEND_BASE_URL="${BACKEND_BASE_URL:-http://127.0.0.1:8000}"
FRONTEND_BASE_URL="${FRONTEND_BASE_URL:-http://127.0.0.1:3000}"
PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://${DOMAIN}}"

check_status() {
    local label="$1"
    local expected="$2"
    shift 2

    local status
    status="$("$@" 2>/dev/null)"

    if [[ "${status}" == "${expected}" ]]; then
        printf 'PASS %-28s -> %s\n' "${label}" "${status}"
    else
        printf 'FAIL %-28s -> expected %s, got %s\n' "${label}" "${expected}" "${status:-<empty>}" >&2
        return 1
    fi
}

echo "Verifying builder.amarktai.com go-live path..."

check_status \
    "backend /health" \
    "200" \
    curl -fsS -o /dev/null -w "%{http_code}" -H "Host: ${DOMAIN}" "${BACKEND_BASE_URL}/health"

check_status \
    "backend /api/v1/health" \
    "200" \
    curl -fsS -o /dev/null -w "%{http_code}" -H "Host: ${DOMAIN}" "${BACKEND_BASE_URL}/api/v1/health"

check_status \
    "backend /docs" \
    "200" \
    curl -fsS -o /dev/null -w "%{http_code}" -H "Host: ${DOMAIN}" "${BACKEND_BASE_URL}/docs"

check_status \
    "frontend localhost:3000" \
    "200" \
    curl -fsS -o /dev/null -w "%{http_code}" "${FRONTEND_BASE_URL}/"

check_status \
    "public /" \
    "200" \
    curl -fsS -o /dev/null -w "%{http_code}" "${PUBLIC_BASE_URL}/"

check_status \
    "public /api/v1/health" \
    "200" \
    curl -fsS -o /dev/null -w "%{http_code}" "${PUBLIC_BASE_URL}/api/v1/health"

check_status \
    "public /api/health" \
    "404" \
    curl -sS -o /dev/null -w "%{http_code}" "${PUBLIC_BASE_URL}/api/health"

echo "All go-live checks passed."
