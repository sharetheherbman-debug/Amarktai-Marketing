#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/var/www/amarktai-marketing/repo}"
APP_DIR="$REPO_ROOT/app"
BACKEND_DIR="$REPO_ROOT/backend"

if [[ ! -d "$REPO_ROOT" ]]; then
  echo "ERROR: repo path not found: $REPO_ROOT" >&2
  exit 1
fi

echo "Fixing ownership (admin:www-data) for $REPO_ROOT"
sudo chown -R admin:www-data "$REPO_ROOT"

echo "Applying safe file/dir permissions"
sudo chmod -R u+rwX,g+rX "$REPO_ROOT"

if [[ -d "$APP_DIR/node_modules/.bin" ]]; then
  echo "Ensuring frontend build tools are executable"
  sudo chmod +x "$APP_DIR"/node_modules/.bin/* || true
fi

if ls "$REPO_ROOT"/scripts/*.sh >/dev/null 2>&1; then
  echo "Ensuring script files are executable"
  sudo chmod +x "$REPO_ROOT"/scripts/*.sh || true
fi

echo "Removing backend __pycache__ folders"
find "$BACKEND_DIR/app" -type d -name "__pycache__" -prune -exec sudo rm -rf {} +

if [[ -f "$BACKEND_DIR/.env" ]]; then
  echo "Securing backend/.env"
  sudo chown admin:www-data "$BACKEND_DIR/.env"
  sudo chmod 640 "$BACKEND_DIR/.env"
fi

echo "Permission fix completed."
