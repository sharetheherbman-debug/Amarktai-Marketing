#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== Backend compile =="
cd "$ROOT_DIR"
python3 -m compileall backend

echo "== API flow scripts =="
cd "$ROOT_DIR"
bash scripts/test_12_platform_pack.sh
bash scripts/test_scheduler_calendar_flow.sh
bash scripts/test_provider_router_flow.sh
bash scripts/test_business_grounding_quality.sh
bash scripts/test_generated_content_visibility.sh
bash scripts/test_login_after_content_rejection.sh

BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
EMAIL="${MARKETING_TEST_EMAIL:-amarktainetwork@gmail.com}"
PASSWORD="${MARKETING_TEST_PASSWORD:-ChangeMeNow2026!}"
API="$BASE_URL/api/v1"

TOKEN="$(curl -sS -X POST "$API/auth/login" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" | python3 - <<'PY'
import json,sys
print(json.load(sys.stdin).get("access_token",""))
PY
)"
[ -n "$TOKEN" ] || { echo "FAIL: no token"; exit 1; }
AUTH=(-H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")

echo "== Workers status =="
WORKERS="$(curl -sS "$API/workers/status" "${AUTH[@]}")"
python3 - <<'PY' "$WORKERS"
import json,sys
data=json.loads(sys.argv[1])
workers=data.get("workers",{})
required={"scheduler_publisher","daily_learning","media_polling","retry_queue"}
missing=required-set(workers.keys())
assert not missing, f"missing worker keys: {missing}"
print("PASS: workers status includes all 4 worker keys")
PY

echo "== Agents status =="
AGENTS="$(curl -sS "$API/agents/status" "${AUTH[@]}")"
python3 - <<'PY' "$AGENTS"
import json,sys
data=json.loads(sys.argv[1])
assert data.get("agents"), "no agents returned"
print(f"PASS: {len(data['agents'])} agents registered")
PY

echo "== Agents run =="
RUN="$(curl -sS -X POST "$API/agents/run" "${AUTH[@]}" \
  -d '{"agent":"CopyAgent","inputs":{"platform":"instagram","objective":"drive leads"}}')"
python3 - <<'PY' "$RUN"
import json,sys
data=json.loads(sys.argv[1])
assert data.get("agent")=="CopyAgent", data
print("PASS: agents/run endpoint responds correctly")
PY

echo "PRODUCTION_FLOW_OK"

