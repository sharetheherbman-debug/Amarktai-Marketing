#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/amarktai-marketing/repo}"
STATIC_DIR="${STATIC_DIR:-/var/www/amarktai-marketing/current/app/dist}"
SERVICE_NAME="${SERVICE_NAME:-amarktai-marketing-api.service}"
DOMAIN="${DOMAIN:-marketing.amarktai.com}"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

log "Updating repository..."
cd "${APP_DIR}"
git pull --ff-only

log "Installing backend dependencies..."
cd backend
[ -d venv ] || python3 -m venv venv
./venv/bin/pip install -r requirements.txt

log "Running migrations..."
./venv/bin/alembic upgrade head || true

log "Running live MariaDB user-column repair (idempotent)..."
cd ..
python3 scripts/repair_live_user_columns.py || true

log "Building frontend..."
cd app
npm install
npm run build

log "Syncing static frontend..."
sudo mkdir -p "${STATIC_DIR}"
sudo rsync -a --delete dist/ "${STATIC_DIR}/"

log "Installing systemd service file..."
cd ..
sudo cp deploy/systemd/amarktai-marketing-api.service /etc/systemd/system/amarktai-marketing-api.service
sudo systemctl daemon-reload
sudo systemctl restart "${SERVICE_NAME}"

log "Installing nginx site..."
sudo cp deploy/nginx/marketing.amarktai.com.conf /etc/nginx/sites-available/marketing.amarktai.com
sudo ln -sf /etc/nginx/sites-available/marketing.amarktai.com /etc/nginx/sites-enabled/marketing.amarktai.com
sudo nginx -t
sudo systemctl reload nginx

log "Running go-live verification..."
./deploy/verify-marketing-go-live.sh

log "Deploy complete: https://${DOMAIN}"
