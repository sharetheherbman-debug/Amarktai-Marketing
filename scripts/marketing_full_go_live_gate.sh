#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
FRONTEND_URL="${FRONTEND_URL:-https://marketing.amarktai.com}"
ALLOW_UNAUTHENTICATED_SMOKE="${ALLOW_UNAUTHENTICATED_SMOKE:-false}"
REQUIRE_FULL_POSTING="${REQUIRE_FULL_POSTING:-false}"
REQUIRE_ALL_PLATFORMS_POSTING="${REQUIRE_ALL_PLATFORMS_POSTING:-false}"
EMAIL="${MARKETING_TEST_EMAIL:-}"
PASSWORD="${MARKETING_TEST_PASSWORD:-}"

pass(){ echo "PASS: $1"; }
warn(){ echo "WARN: $1"; }

BLOCKERS=()
CONDITIONS=()

add_blocker() {
  BLOCKERS+=("$1")
  echo "BLOCKER: $1"
}

add_condition() {
  CONDITIONS+=("$1")
  echo "CONDITION: $1"
}

run_check() {
  local label="$1"
  shift
  if "$@"; then
    pass "$label"
  else
    add_blocker "$label"
  fi
}

finish() {
  local verdict exit_code
  if ((${#BLOCKERS[@]} > 0)); then
    verdict="NO_GO"
    exit_code=1
  elif [[ "${FULL_AUTONOMY_READY_FLAG:-0}" == "1" ]]; then
    verdict="FULL_AUTONOMY_READY"
    exit_code=0
  elif [[ "${MULTIMODAL_LIMITED_FLAG:-0}" == "1" ]]; then
    verdict="FULL_AUTONOMY_BLOCKED"
    exit_code=0
  else
    verdict="MULTIMODAL_LIMITED_OK"
    exit_code=0
  fi

  echo
  [[ "${PRODUCTION_FLOW_FLAG:-0}" == "1" ]] && echo "PRODUCTION_FLOW_OK"
  [[ "${MULTIMODAL_LIMITED_FLAG:-0}" == "1" ]] && echo "MULTIMODAL_LIMITED_OK"
  echo "Final verdict: $verdict"
  if ((${#BLOCKERS[@]} > 0)); then
    echo "Blockers:"
    printf ' - %s\n' "${BLOCKERS[@]}"
  fi
  if ((${#CONDITIONS[@]} > 0)); then
    echo "Conditions:"
    printf ' - %s\n' "${CONDITIONS[@]}"
  fi

  exit "$exit_code"
}

echo "Resolved REPO_ROOT: $REPO_ROOT"
echo "Using BASE_URL: $BASE_URL"
echo "Using FRONTEND_URL: $FRONTEND_URL"

if [[ ! -d "$REPO_ROOT/backend/app" || ! -f "$REPO_ROOT/app/package.json" ]]; then
  add_blocker "REPO_ROOT must contain backend/app and app/package.json"
  finish
fi

cd "$REPO_ROOT"

run_check "backend compile/import" bash -lc "cd '$REPO_ROOT' && python3 -m compileall backend >/dev/null"
run_check "frontend build" bash -lc "cd '$REPO_ROOT/app' && npm run build >/dev/null"

if BASE_URL="$BASE_URL" FRONTEND_URL="$FRONTEND_URL" REPO_ROOT="$REPO_ROOT" "$REPO_ROOT/scripts/marketing_local_check.sh"; then
  pass "baseline health/login/readiness checks"
  PRODUCTION_FLOW_FLAG=1
else
  add_blocker "baseline health/login/readiness checks"
fi

if [[ -n "$EMAIL" || -n "$PASSWORD" ]]; then
  if [[ -z "$EMAIL" || -z "$PASSWORD" ]]; then
    add_blocker "MARKETING_TEST_EMAIL and MARKETING_TEST_PASSWORD must both be set for the authenticated gate"
  fi
elif [[ "$ALLOW_UNAUTHENTICATED_SMOKE" == "true" ]]; then
  add_condition "Authenticated smoke skipped because ALLOW_UNAUTHENTICATED_SMOKE=true and no test credentials were provided"
  finish
else
  add_blocker "MARKETING_TEST_EMAIL and MARKETING_TEST_PASSWORD are required unless ALLOW_UNAUTHENTICATED_SMOKE=true"
  finish
fi

LOGIN_JSON=""
TOKEN=""
if [[ -n "$EMAIL" && -n "$PASSWORD" ]]; then
  LOGIN_JSON=$(curl -fsS -X POST "$BASE_URL/api/v1/auth/login" -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}") || add_blocker "authenticated login"
  if [[ -n "$LOGIN_JSON" ]]; then
    TOKEN=$(python3 - <<'PY' "$LOGIN_JSON"
import json,sys
print(json.loads(sys.argv[1]).get("access_token",""))
PY
)
    if [[ -n "$TOKEN" ]]; then
      pass "authenticated login"
    else
      add_blocker "authenticated login access token"
    fi
  fi
fi

if [[ -z "$TOKEN" ]]; then
  finish
fi

AUTH_HEADER=(-H "Authorization: Bearer $TOKEN")

if PUBLIC_BASE_URL="$FRONTEND_URL" API_BASE_URL="${API_BASE_URL:-$FRONTEND_URL/api/v1}" REPO_ROOT="$REPO_ROOT" MARKETING_TEST_EMAIL="$EMAIL" MARKETING_TEST_PASSWORD="$PASSWORD" "$REPO_ROOT/scripts/marketing_go_live_smoke.sh"; then
  pass "public go-live smoke"
else
  add_blocker "public go-live smoke"
fi

for script_name in test_genx_models.sh test_autonomous_generation.sh test_scheduler_flow.sh test_posting_readiness.sh test_learning_loop.sh; do
  if BASE_URL="$BASE_URL" MARKETING_TEST_EMAIL="$EMAIL" MARKETING_TEST_PASSWORD="$PASSWORD" "$REPO_ROOT/scripts/$script_name"; then
    pass "$script_name"
  else
    add_blocker "$script_name"
  fi
done
if BASE_URL="$BASE_URL" MARKETING_TEST_EMAIL="$EMAIL" MARKETING_TEST_PASSWORD="$PASSWORD" "$REPO_ROOT/scripts/test_webapps_live.sh"; then
  pass "test_webapps_live.sh"
  MULTIMODAL_LIMITED_FLAG=1
else
  add_blocker "test_webapps_live.sh"
fi

READINESS_JSON=$(curl -fsS "$BASE_URL/api/v1/settings/readiness" "${AUTH_HEADER[@]}") || {
  add_blocker "settings readiness endpoint"
  finish
}
PUBLISHING_JSON=$(curl -fsS "$BASE_URL/api/v1/publishing/readiness" "${AUTH_HEADER[@]}") || {
  add_blocker "publishing readiness endpoint"
  finish
}
CAPABILITIES_JSON=$(curl -fsS "$BASE_URL/api/v1/capabilities" "${AUTH_HEADER[@]}") || {
  add_blocker "capabilities endpoint"
  finish
}
AGENTS_JSON=$(curl -fsS "$BASE_URL/api/v1/agents/status" "${AUTH_HEADER[@]}") || {
  add_blocker "agents status endpoint"
  finish
}
HF_TASKS_JSON=$(curl -fsS "$BASE_URL/api/v1/settings/huggingface/tasks" "${AUTH_HEADER[@]}") || {
  add_blocker "huggingface tasks endpoint"
  finish
}
PLATFORM_INTELLIGENCE_JSON=$(curl -fsS "$BASE_URL/api/v1/platform-intelligence" "${AUTH_HEADER[@]}") || {
  add_blocker "platform intelligence endpoint"
  finish
}
LEARNING_STATUS_JSON=$(curl -fsS "$BASE_URL/api/v1/learning/status" "${AUTH_HEADER[@]}") || {
  add_blocker "learning status endpoint"
  finish
}

while IFS='=' read -r key value; do
  case "$key" in
    GENX_CONFIGURED) GENX_CONFIGURED="$value" ;;
    GENX_HEALTH_OK) GENX_HEALTH_OK="$value" ;;
    GENX_MODELS_OK) GENX_MODELS_OK="$value" ;;
    READY_SUPPORTED) READY_SUPPORTED="$value" ;;
    BLOCKED_SUPPORTED) BLOCKED_SUPPORTED="$value" ;;
    BLOCKED_ALL) BLOCKED_ALL="$value" ;;
    UNSUPPORTED) UNSUPPORTED="$value" ;;
    CAPS_OK) CAPS_OK="$value" ;;
    AGENTS_OK) AGENTS_OK="$value" ;;
    HF_TASKS_OK) HF_TASKS_OK="$value" ;;
    LEARNING_OK) LEARNING_OK="$value" ;;
  esac
done < <(python3 - <<'PY' "$READINESS_JSON" "$PUBLISHING_JSON" "$CAPABILITIES_JSON" "$AGENTS_JSON" "$HF_TASKS_JSON" "$LEARNING_STATUS_JSON"
import json,sys
readiness=json.loads(sys.argv[1])
publishing=json.loads(sys.argv[2])
capabilities=json.loads(sys.argv[3])
agents=json.loads(sys.argv[4])
hf_tasks=json.loads(sys.argv[5])
learning=json.loads(sys.argv[6])
platforms=publishing.get("platforms") or {}
ready_supported=[name for name,state in platforms.items() if state.get("posting_supported") and state.get("can_post_now")]
blocked_supported=[name for name,state in platforms.items() if state.get("posting_supported") and not state.get("can_post_now")]
blocked_all=[name for name,state in platforms.items() if not state.get("can_post_now")]
unsupported=[name for name,state in platforms.items() if not state.get("posting_supported")]
genx=readiness.get("genx") or {}
print(f"GENX_CONFIGURED={1 if genx.get('configured') else 0}")
print(f"GENX_HEALTH_OK={1 if genx.get('health_ok') else 0}")
print(f"GENX_MODELS_OK={1 if genx.get('required_models_ok') else 0}")
print(f"READY_SUPPORTED={','.join(ready_supported)}")
print(f"BLOCKED_SUPPORTED={','.join(blocked_supported)}")
print(f"BLOCKED_ALL={','.join(blocked_all)}")
print(f"UNSUPPORTED={','.join(unsupported)}")
print(f"CAPS_OK={1 if isinstance(capabilities.get('capabilities'), list) else 0}")
print(f"AGENTS_OK={1 if isinstance(agents.get('agents'), list) else 0}")
print(f"HF_TASKS_OK={1 if isinstance(hf_tasks.get('tasks'), list) else 0}")
print(f"LEARNING_OK={1 if 'learning_active' in learning else 0}")
PY
)

[[ "${GENX_CONFIGURED:-0}" == "1" ]] || add_blocker "GenX is not configured with either GENX_API_KEY or an active per-user GENX key"
[[ "${GENX_HEALTH_OK:-0}" == "1" ]] || add_blocker "GenX health check is not passing"
[[ "${GENX_MODELS_OK:-0}" == "1" ]] || add_blocker "GenX required models are not all healthy"

if [[ -z "${READY_SUPPORTED:-}" ]]; then
  if [[ "$REQUIRE_FULL_POSTING" == "true" ]]; then
    add_blocker "REQUIRE_FULL_POSTING=true but no supported platform can_post_now=true"
  else
    add_condition "No supported live-posting platform currently reports can_post_now=true"
  fi
else
  pass "supported live-posting readiness: ${READY_SUPPORTED}"
fi

if [[ "$REQUIRE_ALL_PLATFORMS_POSTING" == "true" && -n "${BLOCKED_ALL:-}" ]]; then
  add_blocker "REQUIRE_ALL_PLATFORMS_POSTING=true but these platforms cannot post now: ${BLOCKED_ALL}"
elif [[ -n "${UNSUPPORTED:-}" ]]; then
  warn "Posting not implemented for: ${UNSUPPORTED}"
fi

if [[ "${GENX_CONFIGURED:-0}" == "1" && "${GENX_MODELS_OK:-0}" == "1" && "${CAPS_OK:-0}" == "1" && "${AGENTS_OK:-0}" == "1" && "${HF_TASKS_OK:-0}" == "1" && "${LEARNING_OK:-0}" == "1" ]]; then
  FULL_AUTONOMY_READY_FLAG=1
fi

finish
