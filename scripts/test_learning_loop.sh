#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
API="$BASE_URL/api/v1"
EMAIL="${MARKETING_TEST_EMAIL:-}"
PASSWORD="${MARKETING_TEST_PASSWORD:-}"

pass(){ echo "PASS: $1"; }
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

MANUAL=$(curl -fsS -X POST "$API/analytics/manual-metrics" "${AUTH[@]}" -H 'Content-Type: application/json' -d '{"platform":"instagram","impressions":1000,"reach":700,"clicks":34,"likes":80,"comments":8,"shares":6,"saves":4,"conversions":2}') || fail "manual metrics failed"
echo "$MANUAL" | python3 -m json.tool >/dev/null || fail "manual metrics invalid json"
pass "manual metrics ingestion"

CSV_FILE="/tmp/marketing-learning-metrics.csv"
cat > "$CSV_FILE" <<'CSV'
platform,metric_date,impressions,reach,clicks,likes,comments,shares,saves,conversions
linkedin,2026-05-19,1200,900,41,65,12,7,3,5
CSV

IMPORT=$(curl -fsS -X POST "$API/analytics/import-csv" "${AUTH[@]}" -F "file=@$CSV_FILE;type=text/csv") || fail "csv import failed"
echo "$IMPORT" | python3 -m json.tool >/dev/null || fail "csv import invalid json"
pass "csv metrics import"

STATUS=$(curl -fsS "$API/analytics/learning-status" "${AUTH[@]}") || fail "learning status failed"
python3 - <<'PY' "$STATUS"
import json,sys
data=json.loads(sys.argv[1])
required=["learning_active","metrics_records","last_learning_run","next_learning_run","mode","blockers"]
missing=[k for k in required if k not in data]
if missing:
    raise SystemExit(f"Missing fields: {missing}")
if data.get("metrics_records",0) <= 0:
    raise SystemExit("metrics_records did not increase")
print("ok")
PY
pass "learning-status fields and records"
