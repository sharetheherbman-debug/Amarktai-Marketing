#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
API="$BASE_URL/api/v1"
EMAIL="${MARKETING_TEST_EMAIL:-}"
PASSWORD="${MARKETING_TEST_PASSWORD:-}"

pass(){ echo "PASS: $1"; }
warn(){ echo "WARN: $1"; }
fail(){ echo "FAIL: $1"; exit 1; }

[[ -n "$EMAIL" && -n "$PASSWORD" ]] || fail "MARKETING_TEST_EMAIL and MARKETING_TEST_PASSWORD are required"

LOGIN_JSON=$(curl -fsS -X POST "$API/auth/login" -H 'Content-Type: application/json' -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}") || fail "login failed"
TOKEN=$(python3 - <<'PY' "$LOGIN_JSON"
import json,sys
print(json.loads(sys.argv[1]).get("access_token",""))
PY
)
[[ -n "$TOKEN" ]] || fail "missing access token"
AUTH=(-H "Authorization: Bearer $TOKEN")

MODELS=$(curl -fsS "$API/settings/genx/models" "${AUTH[@]}") || fail "GET /settings/genx/models failed"
echo "$MODELS" | python3 -m json.tool >/dev/null || fail "invalid JSON from /settings/genx/models"
pass "GenX model discovery endpoint"

TESTS=$(curl -fsS -X POST "$API/settings/genx/test-models" "${AUTH[@]}") || fail "POST /settings/genx/test-models failed"
echo "$TESTS" | python3 -m json.tool >/dev/null || fail "invalid JSON from /settings/genx/test-models"

python3 - <<'PY' "$TESTS"
import json,sys
data=json.loads(sys.argv[1])
required={"default","copy","strategy","analysis"}
ok_by_task={}
for r in data.get("results",[]):
    ok_by_task[r.get("task")]=bool(r.get("ok"))
missing=[t for t in required if not ok_by_task.get(t)]
if missing:
    print("FAIL_REQUIRED=" + ",".join(missing))
    raise SystemExit(1)
optional=["image","video","audio"]
for t in optional:
    if t in ok_by_task and not ok_by_task[t]:
        print("WARN_OPTIONAL=" + t)
print("OK")
PY

if [[ $? -ne 0 ]]; then
  fail "required GenX models failed"
fi

while IFS= read -r line; do
  [[ "$line" == WARN_OPTIONAL=* ]] && warn "optional model failed: ${line#WARN_OPTIONAL=}"
done < <(python3 - <<'PY' "$TESTS"
import json,sys
data=json.loads(sys.argv[1])
for r in data.get("results",[]):
    if r.get("task") in {"image","video","audio"} and not r.get("ok"):
        print("WARN_OPTIONAL="+r.get("task"))
PY
)

pass "required GenX models healthy"
