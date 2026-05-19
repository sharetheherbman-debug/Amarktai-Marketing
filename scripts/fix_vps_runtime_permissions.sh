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
chown -R admin:www-data "$REPO_ROOT"

echo "Applying safe file/dir permissions"
find "$REPO_ROOT" -type d -exec chmod 750 {} \;
find "$REPO_ROOT" -type f -exec chmod 640 {} \;

if [[ -d "$APP_DIR/node_modules/.bin" ]]; then
  echo "Ensuring frontend build tools are executable"
  chmod +x "$APP_DIR"/node_modules/.bin/* || true
fi

echo "Removing backend __pycache__ folders"
find "$BACKEND_DIR/app" -type d -name "__pycache__" -prune -exec rm -rf {} +

if [[ -f "$BACKEND_DIR/.env" ]]; then
  echo "Securing backend/.env"
  chown admin:www-data "$BACKEND_DIR/.env"
  chmod 640 "$BACKEND_DIR/.env"
fi

echo "Permission fix completed."
