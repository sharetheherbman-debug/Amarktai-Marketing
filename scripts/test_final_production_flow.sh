#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "== Backend compile =="
cd "$ROOT_DIR"
python3 -m compileall backend

echo "== Frontend build =="
cd "$ROOT_DIR/app"
npm run build

echo "== API flow scripts =="
cd "$ROOT_DIR"
bash scripts/test_12_platform_pack.sh
bash scripts/test_scheduler_calendar_flow.sh
bash scripts/test_provider_router_flow.sh
bash scripts/test_business_grounding_quality.sh
bash scripts/test_generated_content_visibility.sh
bash scripts/test_login_after_content_rejection.sh

echo "PRODUCTION_FLOW_OK"
