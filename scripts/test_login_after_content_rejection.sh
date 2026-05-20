#!/usr/bin/env bash
# =============================================================================
# scripts/test_login_after_content_rejection.sh
#
# Gate test: Verify login works before and after content rejection.
# No 500s on auth or dashboard boot endpoints after rejecting a content item.
#
# Usage:
#   BASE_URL=http://localhost:8000 EMAIL=test@example.com PASSWORD=testpass \
#     bash scripts/test_login_after_content_rejection.sh
# =============================================================================

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
API="$BASE_URL/api/v1"
EMAIL="${EMAIL:-rejection_test_$(date +%s)@amarktai.test}"
PASSWORD="${PASSWORD:-TestPass123!}"

PASS=0
FAIL=0

_ok() { echo "  ✅ $1"; ((PASS++)) || true; }
_fail() { echo "  ❌ $1"; ((FAIL++)) || true; }
_info() { echo "  ℹ️  $1"; }

assert_status() {
  local label="$1" expected="$2" actual="$3"
  if [ "$actual" -eq "$expected" ]; then
    _ok "$label (HTTP $actual)"
  else
    _fail "$label (expected $expected, got $actual)"
  fi
}

assert_not_500() {
  local label="$1" actual="$2"
  if [ "$actual" -lt 500 ]; then
    _ok "$label (HTTP $actual — no 500)"
  else
    _fail "$label (got HTTP $actual — server error)"
  fi
}

echo ""
echo "========================================="
echo "  Login-After-Rejection Gate Test"
echo "  $API"
echo "========================================="

# ── STEP 1: Register test user ────────────────────────────────────────────────
echo ""
echo "1. Register test user ($EMAIL)..."
REG_RESP=$(curl -s -o /tmp/reg_body.json -w "%{http_code}" \
  -X POST "$API/auth/register" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"name\":\"Rejection Tester\"}")

if [ "$REG_RESP" -eq 201 ] || [ "$REG_RESP" -eq 409 ]; then
  _ok "Register (HTTP $REG_RESP)"
else
  _fail "Register (HTTP $REG_RESP)"
fi

# ── STEP 2: Login ─────────────────────────────────────────────────────────────
echo ""
echo "2. Login..."
LOGIN_RESP=$(curl -s -o /tmp/login_body.json -w "%{http_code}" \
  -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

assert_status "Login" 200 "$LOGIN_RESP"
TOKEN=$(python3 -c "import json,sys; d=json.load(open('/tmp/login_body.json')); print(d.get('access_token',''))" 2>/dev/null || echo "")

if [ -z "$TOKEN" ]; then
  _fail "No token received — cannot continue"
  echo ""; echo "RESULT: FAIL (no token)"; exit 1
fi
_info "Got token: ${TOKEN:0:20}..."

AUTH="-H \"Authorization: Bearer $TOKEN\""

# ── STEP 3: Verify /users/me ──────────────────────────────────────────────────
echo ""
echo "3. Verify /users/me..."
ME_RESP=$(curl -s -o /tmp/me_body.json -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" "$API/users/me")
assert_status "/users/me after login" 200 "$ME_RESP"

# ── STEP 4: Create test business ──────────────────────────────────────────────
echo ""
echo "4. Create test business (Equine example)..."
BIZ_RESP=$(curl -s -o /tmp/biz_body.json -w "%{http_code}" \
  -X POST "$API/webapps/" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"Sunrise Equestrian Centre","url":"https://sunrise-equestrian.test","description":"Premium horse riding lessons, livery, and equine care in Surrey","category":"equine","target_audience":"Horse owners, riders, equestrian enthusiasts","key_features":["Horse riding lessons","Livery services","Equine health care","Show jumping training"]}')

if [ "$BIZ_RESP" -eq 200 ] || [ "$BIZ_RESP" -eq 201 ]; then
  _ok "Create business (HTTP $BIZ_RESP)"
else
  _fail "Create business (HTTP $BIZ_RESP)"
fi
WEBAPP_ID=$(python3 -c "import json; d=json.load(open('/tmp/biz_body.json')); print(d.get('id',''))" 2>/dev/null || echo "")
_info "Webapp ID: $WEBAPP_ID"

# ── STEP 5: Generate content ──────────────────────────────────────────────────
echo ""
echo "5. Generate content for instagram..."
if [ -n "$WEBAPP_ID" ]; then
  GEN_RESP=$(curl -s -o /tmp/gen_body.json -w "%{http_code}" \
    -X POST "$API/content/generate?webapp_id=$WEBAPP_ID&platform=instagram" \
    -H "Authorization: Bearer $TOKEN")
  assert_not_500 "Generate content" "$GEN_RESP"
  CONTENT_ID=$(python3 -c "import json; d=json.load(open('/tmp/gen_body.json')); print(d.get('id',''))" 2>/dev/null || echo "")
  _info "Content ID: $CONTENT_ID"

  # Check no Amarktai hashtags
  HASHTAGS=$(python3 -c "import json; d=json.load(open('/tmp/gen_body.json')); print(' '.join(d.get('hashtags',[])))" 2>/dev/null || echo "")
  _info "Hashtags: $HASHTAGS"
  if echo "$HASHTAGS" | grep -iq "amarktai"; then
    _fail "Amarktai hashtag found in equine content: $HASHTAGS"
  else
    _ok "No Amarktai hashtags in equine content"
  fi
else
  _fail "Cannot generate content — no webapp ID"
fi

# ── STEP 6: List content library ─────────────────────────────────────────────
echo ""
echo "6. List content library..."
LIB_RESP=$(curl -s -o /tmp/lib_body.json -w "%{http_code}" \
  -H "Authorization: Bearer $TOKEN" "$API/content/items?webapp_id=$WEBAPP_ID")
assert_not_500 "Content library" "$LIB_RESP"

# ── STEP 7: Reject content ────────────────────────────────────────────────────
echo ""
echo "7. Reject content item..."
if [ -n "${CONTENT_ID:-}" ]; then
  REJ_RESP=$(curl -s -o /tmp/rej_body.json -w "%{http_code}" \
    -X POST "$API/content/items/$CONTENT_ID/reject" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{"reason":"Wrong hashtags and unrelated imagery","feedback":"Please use horse and equine-specific imagery","regenerate":false}')
  assert_not_500 "Reject content item" "$REJ_RESP"
  STATUS_AFTER=$(python3 -c "import json; d=json.load(open('/tmp/rej_body.json')); print(d.get('status','?'))" 2>/dev/null || echo "?")
  if [ "$STATUS_AFTER" = "rejected" ]; then
    _ok "Content item status is 'rejected' after rejection"
  else
    _fail "Expected status=rejected, got '$STATUS_AFTER'"
  fi
else
  _fail "No content ID — skipping rejection test"
fi

# ── STEP 8: Login again after rejection ───────────────────────────────────────
echo ""
echo "8. Login AGAIN after content rejection..."
LOGIN2_RESP=$(curl -s -o /tmp/login2_body.json -w "%{http_code}" \
  -X POST "$API/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
assert_status "Login after rejection" 200 "$LOGIN2_RESP"
TOKEN2=$(python3 -c "import json,sys; d=json.load(open('/tmp/login2_body.json')); print(d.get('access_token',''))" 2>/dev/null || echo "")

if [ -z "$TOKEN2" ]; then
  _fail "No token on second login — login broken after rejection!"
else
  _ok "Second login successful"
fi

# ── STEP 9: Dashboard boot endpoints with new token ───────────────────────────
echo ""
echo "9. Dashboard boot endpoints (with token from 2nd login)..."
for ENDPOINT in "/users/me" "/webapps/" "/settings/readiness"; do
  BOOT_RESP=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bearer ${TOKEN2:-$TOKEN}" "$API$ENDPOINT")
  assert_not_500 "$ENDPOINT" "$BOOT_RESP"
done

# ── STEP 10: Content library still loads after rejection ──────────────────────
echo ""
echo "10. Content library after rejection..."
LIB2_RESP=$(curl -s -o /tmp/lib2_body.json -w "%{http_code}" \
  -H "Authorization: Bearer ${TOKEN2:-$TOKEN}" "$API/content/items?webapp_id=$WEBAPP_ID")
assert_not_500 "Content library after rejection" "$LIB2_RESP"

# ── STEP 11: Content provenance ───────────────────────────────────────────────
echo ""
echo "11. Content provenance endpoint..."
PROV_RESP=$(curl -s -o /tmp/prov_body.json -w "%{http_code}" \
  -H "Authorization: Bearer ${TOKEN2:-$TOKEN}" "$API/content/provenance?webapp_id=$WEBAPP_ID")
assert_not_500 "Content provenance" "$PROV_RESP"

# ── STEP 12: Cleanup test business ────────────────────────────────────────────
echo ""
echo "12. Cleanup test business..."
if [ -n "$WEBAPP_ID" ]; then
  DEL_RESP=$(curl -s -o /dev/null -w "%{http_code}" \
    -X DELETE "$API/webapps/$WEBAPP_ID" \
    -H "Authorization: Bearer ${TOKEN2:-$TOKEN}")
  _info "Delete webapp: HTTP $DEL_RESP"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "========================================="
echo "  Results: $PASS passed, $FAIL failed"
echo "========================================="

if [ "$FAIL" -gt 0 ]; then
  echo "  GATE: ❌ FAIL"
  exit 1
else
  echo "  GATE: ✅ PASS"
  exit 0
fi
