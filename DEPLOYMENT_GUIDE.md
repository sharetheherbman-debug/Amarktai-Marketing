# Deployment Guide — marketing.amarktai.com

This is the production deployment path for `sharetheherbman-debug/Amarktai-Marketing`.

## Production truth (current)

- Builder domain/app is separate and **must not be deployed from this repository**.
- Marketing production domain: `marketing.amarktai.com`
- Marketing repo path: `/var/www/amarktai-marketing/repo`
- Marketing backend runtime: `amarktai-marketing-api.service` on `127.0.0.1:8010`
- Marketing frontend runtime: static files from `/var/www/amarktai-marketing/current/app/dist`
- Host Nginx owns public `:80/:443`

## 1) Update code

```bash
cd /var/www/amarktai-marketing/repo
git pull --ff-only
```

## 2) Backend environment and dependencies

```bash
cd /var/www/amarktai-marketing/repo/backend
cp .env.example .env   # first deploy only
python3 -m venv venv   # first deploy only
./venv/bin/pip install -r requirements.txt
```

Set production values in `backend/.env`:

```env
APP_ENVIRONMENT=production
FRONTEND_URL=https://marketing.amarktai.com
CORS_ORIGINS=["https://marketing.amarktai.com"]
DATABASE_URL=<production mysql or postgres url>
REDIS_URL=<production redis url>
JWT_SECRET=<openssl rand -hex 32>
ENCRYPTION_KEY=<openssl rand -base64 32>
GENX_API_KEY=<required for real AI generation>
```

## 3) Migrations and live MariaDB repair

For clean DBs:

```bash
cd /var/www/amarktai-marketing/repo/backend
./venv/bin/alembic upgrade head
```

For existing live MariaDB where legacy `users` table may miss columns, run the repair script before/after migration as needed:

```bash
cd /var/www/amarktai-marketing/repo
python3 scripts/repair_live_user_columns.py
```

The repair script is idempotent and only adds missing `users` columns/index/foreign key metadata.

## 4) Build frontend static assets

```bash
cd /var/www/amarktai-marketing/repo/app
npm install
npm run build
sudo mkdir -p /var/www/amarktai-marketing/current/app
sudo rsync -a --delete dist/ /var/www/amarktai-marketing/current/app/dist/
```

## 5) Install/refresh systemd backend service

```bash
cd /var/www/amarktai-marketing/repo
sudo cp deploy/systemd/amarktai-marketing-api.service /etc/systemd/system/amarktai-marketing-api.service
sudo systemctl daemon-reload
sudo systemctl enable amarktai-marketing-api.service
sudo systemctl restart amarktai-marketing-api.service
sudo systemctl status amarktai-marketing-api.service --no-pager
```

## 6) Install/refresh host Nginx site

```bash
cd /var/www/amarktai-marketing/repo
sudo cp deploy/nginx/marketing.amarktai.com.conf /etc/nginx/sites-available/marketing.amarktai.com
sudo ln -sf /etc/nginx/sites-available/marketing.amarktai.com /etc/nginx/sites-enabled/marketing.amarktai.com
sudo nginx -t
sudo systemctl reload nginx
```

Routing in this template:

- `/api/v1/` → `http://127.0.0.1:8010/api/v1/`
- `/health` → `http://127.0.0.1:8010/health`
- `/docs` → `http://127.0.0.1:8010/docs`
- `/openapi.json` → `http://127.0.0.1:8010/openapi.json`
- frontend SPA static root → `/var/www/amarktai-marketing/current/app/dist` with `/index.html` fallback

## 7) Smoke checks

```bash
cd /var/www/amarktai-marketing/repo
./deploy/verify-marketing-go-live.sh
```

Expected:

- `/health` => `200`
- `/api/v1/health` => `200`
- public homepage/API/docs/openapi => `200`

## Optional: Docker Compose for local/future testing only

Docker Compose is not the current production runtime for marketing.

```bash
cd /var/www/amarktai-marketing/repo
cp deploy/docker-compose.env.example .env
COMPOSE_PROJECT_NAME=amarktai_marketing docker compose up -d --build
```

Notes:

- Keep DB/Redis internal-only (no public host port binds).
- Do not bind Docker services to public `80/443`.
