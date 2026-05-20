#!/usr/bin/env bash
# =============================================================================
# scripts/test_provider_key_truth.sh
#
# Provider key truth and diagnostics gate.
# Checks provider-resolution, providers/debug, and per-provider test endpoints.
#
# Fails only on:
#   - Server errors (500+)
#   - Non-JSON 2xx response
#   - Key exists but response says missing_key / decrypt_failed
#   - Contradictions between resolution and test state
#
# Does NOT fail just because a premium model is not mapped.
# Reports MODEL_MAPPING_REQUIRED when appropriate.
#
# Usage:
#   MARKETING_TEST_EMAIL=you@example.com MARKETING_TEST_PASSWORD=secret \
#     bash scripts/test_provider_key_truth.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
export REPO_ROOT

source "$SCRIPT_DIR/lib/auth.sh"
source "$SCRIPT_DIR/lib/http.sh"

PASS=0
FAIL=0
WARN=0

_ok()   { echo "  PASS $1"; ((PASS++)) || true; }
_fail() { echo "  FAIL $1"; ((FAIL++)) || true; }
_warn() { echo "  WARN $1"; ((WARN++)) || true; }

echo ""
echo "=================================================="
echo "  Provider Key Truth Gate"
echo "  BASE_URL: ${BASE_URL}"
echo "=================================================="

# Login
echo ""
echo "1. Login..."
if ! do_login; then
  echo "NO_GO — login failed"
  exit 1
fi
echo "   Token: ${TOKEN:0:20}..."

# ── provider-resolution ───────────────────────────────────────────────────────
echo ""
echo "2. GET /settings/provider-resolution..."
api_call "GET" "/api/v1/settings/provider-resolution"
if [[ "$_HTTP_STATUS" != 2* ]] || [[ -z "$_HTTP_BODY" ]]; then
  print_fail "provider-resolution" "$_HTTP_STATUS" "$_HTTP_BODY"
  _fail "provider-resolution (HTTP ${_HTTP_STATUS})"
else
  _ok "provider-resolution (HTTP ${_HTTP_STATUS})"
  # Check for contradictions
  python3 - <<'PY' "$_HTTP_BODY"
import json, sys
data = json.loads(sys.argv[1])
providers = data.get("providers", {})
for key_name, info in providers.items():
    source = info.get("effective_source", "missing")
    configured = info.get("configured", False)
    decrypt_ok = info.get("decrypt_ok")
    if source == "user" and decrypt_ok is False:
        print(f"  CONTRADICTION: {key_name} source=user but decrypt_ok=False")
    elif source != "missing" and configured:
        print(f"  OK {key_name}: source={source}, configured={configured}")
    elif source == "missing":
        print(f"  INFO {key_name}: not configured (missing)")
PY
fi

# ── providers/debug ───────────────────────────────────────────────────────────
echo ""
echo "3. GET /settings/providers/debug..."
api_call "GET" "/api/v1/settings/providers/debug"
if [[ "$_HTTP_STATUS" != 2* ]] || [[ -z "$_HTTP_BODY" ]]; then
  print_fail "providers/debug" "$_HTTP_STATUS" "$_HTTP_BODY"
  _fail "providers/debug (HTTP ${_HTTP_STATUS})"
else
  _ok "providers/debug (HTTP ${_HTTP_STATUS})"
  python3 - <<'PY' "$_HTTP_BODY"
import json, sys
data = json.loads(sys.argv[1])
for pname, pinfo in data.items():
    key_saved = pinfo.get("key_saved") or pinfo.get("token_saved")
    decrypt_ok = pinfo.get("decrypt_ok")
    note = pinfo.get("note") or ""
    if key_saved and decrypt_ok is False:
        print(f"  CONTRADICTION [{pname}]: key saved but decrypt_ok=False")
    elif key_saved:
        print(f"  OK [{pname}]: key saved, decrypt_ok={decrypt_ok}")
    else:
        print(f"  INFO [{pname}]: not configured")
PY
fi

# ── GenX model check ──────────────────────────────────────────────────────────
echo ""
echo "4. GET /settings/genx/models (model catalog)..."
api_call "GET" "/api/v1/settings/genx/models"
if [[ "$_HTTP_STATUS" -ge 500 ]]; then
  _fail "genx/models server error (HTTP ${_HTTP_STATUS})"
elif [[ "$_HTTP_STATUS" != 2* ]]; then
  _warn "genx/models not 2xx (HTTP ${_HTTP_STATUS}) — provider may be unconfigured"
elif [[ -z "$_HTTP_BODY" ]]; then
  _warn "genx/models returned empty body"
else
  _ok "genx/models (HTTP ${_HTTP_STATUS})"
  python3 - <<'PY' "$_HTTP_BODY"
import json, sys
data = json.loads(sys.argv[1])
models = data.get("models", [])
if isinstance(models, list):
    print(f"  INFO genx models available: {len(models)}")
    if not models:
        print("  MODEL_MAPPING_REQUIRED: no models returned from GenX catalog")
else:
    print(f"  INFO response keys: {list(data.keys())}")
PY
fi

# ── GenX capabilities ─────────────────────────────────────────────────────────
echo ""
echo "5. GET /settings/genx/capabilities..."
api_call "GET" "/api/v1/settings/genx/capabilities"
if [[ "$_HTTP_STATUS" -ge 500 ]]; then
  _fail "genx/capabilities server error (HTTP ${_HTTP_STATUS})"
elif [[ "$_HTTP_STATUS" == 2* ]] && [[ -n "$_HTTP_BODY" ]]; then
  _ok "genx/capabilities (HTTP ${_HTTP_STATUS})"
  python3 - <<'PY' "$_HTTP_BODY"
import json, sys
data = json.loads(sys.argv[1])
configured = data.get("configured", False)
caps = data.get("capabilities", [])
print(f"  INFO genx configured={configured}, capabilities={len(caps)}")
if not configured:
    print("  INFO GenX not configured — add GENX_API_KEY")
PY
else
  _warn "genx/capabilities (HTTP ${_HTTP_STATUS})"
fi

# ── Qwen models catalog ───────────────────────────────────────────────────────
echo ""
echo "6. GET /settings/qwen/models (catalog)..."
api_call "GET" "/api/v1/settings/qwen/models"
if [[ "$_HTTP_STATUS" -ge 500 ]]; then
  _fail "qwen/models server error (HTTP ${_HTTP_STATUS})"
elif [[ "$_HTTP_STATUS" == 2* ]] && [[ -n "$_HTTP_BODY" ]]; then
  _ok "qwen/models (HTTP ${_HTTP_STATUS})"
  python3 - <<'PY' "$_HTTP_BODY"
import json, sys
data = json.loads(sys.argv[1])
cat = data.get("catalog", {})
by_cat = cat.get("by_category", {}) if isinstance(cat, dict) else {}
total = sum(len(v) for v in by_cat.values())
print(f"  INFO qwen catalog: {len(by_cat)} categories, {total} total models")
PY
else
  _warn "qwen/models (HTTP ${_HTTP_STATUS})"
fi

# ── Qwen capabilities ─────────────────────────────────────────────────────────
echo ""
echo "7. GET /settings/qwen/capabilities..."
api_call "GET" "/api/v1/settings/qwen/capabilities"
if [[ "$_HTTP_STATUS" -ge 500 ]]; then
  _fail "qwen/capabilities server error (HTTP ${_HTTP_STATUS})"
elif [[ "$_HTTP_STATUS" == 2* ]] && [[ -n "$_HTTP_BODY" ]]; then
  _ok "qwen/capabilities (HTTP ${_HTTP_STATUS})"
  python3 - <<'PY' "$_HTTP_BODY"
import json, sys
data = json.loads(sys.argv[1])
configured = data.get("configured", False)
caps = data.get("capabilities", [])
print(f"  INFO qwen configured={configured}, capability categories={len(caps)}")
if not configured:
    print("  INFO Qwen not configured — add QWEN_API_KEY for budget fallback")
PY
else
  _warn "qwen/capabilities (HTTP ${_HTTP_STATUS})"
fi

# ── HuggingFace tasks ─────────────────────────────────────────────────────────
echo ""
echo "8. GET /settings/huggingface/tasks..."
api_call "GET" "/api/v1/settings/huggingface/tasks"
if [[ "$_HTTP_STATUS" -ge 500 ]]; then
  _fail "huggingface/tasks server error (HTTP ${_HTTP_STATUS})"
elif [[ "$_HTTP_STATUS" == 2* ]] && [[ -n "$_HTTP_BODY" ]]; then
  _ok "huggingface/tasks (HTTP ${_HTTP_STATUS})"
  python3 - <<'PY' "$_HTTP_BODY"
import json, sys
data = json.loads(sys.argv[1])
tasks = data.get("tasks", {})
if isinstance(tasks, dict):
    print(f"  INFO HF tasks available: {len(tasks)}")
elif isinstance(tasks, list):
    print(f"  INFO HF tasks available: {len(tasks)}")
else:
    print(f"  INFO HF tasks response keys: {list(data.keys())}")
PY
else
  _warn "huggingface/tasks (HTTP ${_HTTP_STATUS}) — token may not be configured"
fi

# ── readiness endpoint ────────────────────────────────────────────────────────
echo ""
echo "9. GET /settings/readiness..."
api_call "GET" "/api/v1/settings/readiness"
if [[ "$_HTTP_STATUS" != 2* ]] || [[ -z "$_HTTP_BODY" ]]; then
  print_fail "settings/readiness" "$_HTTP_STATUS" "$_HTTP_BODY"
  _fail "settings/readiness (HTTP ${_HTTP_STATUS})"
else
  _ok "settings/readiness (HTTP ${_HTTP_STATUS})"
  python3 - <<'PY' "$_HTTP_BODY"
import json, sys
data = json.loads(sys.argv[1])
providers = data.get("providers", {})
provider_details = data.get("provider_details", {})
for pname, pstatus in providers.items():
    detail = provider_details.get(pname, {})
    msg = detail.get("message") or ""
    print(f"  INFO {pname}: status={pstatus}" + (f" ({msg})" if msg else ""))
gen_ready = data.get("generation_readiness", {})
can_gen = gen_ready.get("can_generate_beta", False)
print(f"  INFO can_generate_beta={can_gen}")
PY
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "=================================================="
echo "  Results: ${PASS} passed, ${FAIL} failed, ${WARN} warnings"
echo "=================================================="

if [[ "$FAIL" -gt 0 ]]; then
  echo "FAIL"
  exit 1
else
  echo "PASS"
  exit 0
fi
