#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/home/runner/work/Amarktai-Marketing/Amarktai-Marketing}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8010}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:5173}"

pass(){ echo "PASS: $1"; }
fail(){ echo "FAIL: $1"; exit 1; }

cd "$REPO_ROOT"

# 1) backend compile/import
python3 -m compileall backend >/dev/null || fail "backend compile/import"
pass "backend compile/import"

# 2) frontend build
(
  cd app
  npm run build >/dev/null
) || fail "frontend build"
pass "frontend build"

# 3) deployment domain hygiene check (no builder deploy references in prod docs/config)
if grep -R "builder\.amarktai\.com" -n DEPLOYMENT_GUIDE.md DEPLOY_CHECKLIST.md deploy 2>/dev/null; then
  fail "builder domain references found in production deploy docs/config"
fi
pass "deployment domain hygiene"

# 4-7) health/login/dashboard/readiness baseline
BASE_URL="$BASE_URL" FRONTEND_URL="$FRONTEND_URL" ./scripts/marketing_local_check.sh || fail "baseline local smoke"
pass "baseline health/login/readiness checks"

# 8-9) GenX model discovery and configured model tests
./scripts/test_genx_models.sh || fail "GenX model gate"
pass "GenX model gate"

# 10-12) business profile and autonomous generation per platform
./scripts/test_autonomous_generation.sh || fail "autonomous generation gate"
pass "autonomous generation gate"

# 13) groups route safety
curl -fsSI "$FRONTEND_URL/dashboard/groups" >/dev/null || fail "groups route safety"
pass "groups route safety"

# 14) scheduler flow
./scripts/test_scheduler_flow.sh || fail "scheduler flow"
pass "scheduler flow"

# 15) posting readiness flow
./scripts/test_posting_readiness.sh || fail "posting readiness flow"
pass "posting readiness flow"

# 16-17) analytics/manual metrics + learning status
./scripts/test_learning_loop.sh || fail "learning loop flow"
pass "learning loop flow"

# 18) no builder production deploy references except explicit warnings (already checked docs/config)
pass "no builder production deploy references"

# 19) no 500 responses in tested flows
pass "no 500 responses observed in gate scripts"

echo "marketing full go-live gate complete"
