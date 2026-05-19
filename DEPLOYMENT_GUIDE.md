# Deployment Guide — builder.amarktai.com

This is the production deployment path for `sharetheherbman-debug/Amarktai-Marketing` on a shared VPS.

## Deployment model

- Host Nginx owns public `:80` and `:443` for every app on the VPS.
- Docker Compose runs this app privately on:
  - `127.0.0.1:8000` → FastAPI backend
  - `127.0.0.1:3000` → frontend container
- PostgreSQL and Redis stay internal to the Compose network.
- Public routing for `https://builder.amarktai.com` is handled by the host Nginx site config in `deploy/nginx/builder.amarktai.com.conf`.

## 1. Server prerequisites

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin nginx certbot python3-certbot-nginx curl
sudo systemctl enable --now docker nginx
```

## 2. Repository path

```bash
cd /var/www/amarktai-marketing/repo
git pull --ff-only
```

## 3. Docker Compose interpolation env

Docker Compose reads the repository root `.env` file for `${...}` interpolation.

```bash
cd /var/www/amarktai-marketing/repo
cp deploy/docker-compose.env.example .env
nano .env
```

Required production values in the root `.env`:

```env
POSTGRES_PASSWORD=<strong-password>
DOMAIN=builder.amarktai.com
VITE_API_URL=/api/v1
```

## 4. Backend runtime env

The backend container, Celery worker, and Celery beat all load `backend/.env`.

```bash
cd /var/www/amarktai-marketing/repo
cp backend/.env.example backend/.env
nano backend/.env
chmod 600 backend/.env
```

Required production values in `backend/.env`:

```env
APP_ENVIRONMENT=production
FRONTEND_URL=https://builder.amarktai.com
CORS_ORIGINS=["https://builder.amarktai.com"]
DATABASE_URL=postgresql://amarktai:${POSTGRES_PASSWORD}@db:5432/amarktai
REDIS_URL=redis://redis:6379/0
ADMIN_EMAIL=
JWT_SECRET=<output of: openssl rand -hex 32>
ENCRYPTION_KEY=<output of: openssl rand -base64 32>
STRIPE_WEBHOOK_SECRET=<required in production>
GENX_API_KEY=<required for full AI generation>
```

Notes:

- `DATABASE_URL` must stay on PostgreSQL.
- `POSTGRES_PASSWORD` is supplied by the root `.env` or deployment environment.
- Do not commit either `.env` file.
- `/api/health` is **not** a valid endpoint in this app. Use `/health` or `/api/v1/health`.

## 5. Validate Compose before restart

```bash
cd /var/www/amarktai-marketing/repo
docker compose config
```

Expected result:

- Command exits `0`
- No `version is obsolete` warning
- Backend port shows `127.0.0.1:8000:8000`
- Frontend port shows `127.0.0.1:3000:3000`
- No host port mappings for PostgreSQL, Redis, or public `80/443`

## 6. Start or refresh the stack

```bash
cd /var/www/amarktai-marketing/repo
docker compose up -d --build
docker compose ps
```

Expected result:

- `db` and `redis` show healthy
- `backend`, `frontend`, `celery_worker`, and `celery_beat` show running

## 7. Install the host Nginx site

```bash
cd /var/www/amarktai-marketing/repo
sudo cp deploy/nginx/builder.amarktai.com.conf /etc/nginx/sites-available/builder.amarktai.com
sudo ln -sf /etc/nginx/sites-available/builder.amarktai.com /etc/nginx/sites-enabled/builder.amarktai.com
sudo nginx -t
sudo systemctl reload nginx
```

Expected result:

- `sudo nginx -t` prints `syntax is ok` and `test is successful`
- `systemctl reload nginx` exits `0`

The site template routes:

- `/api/v1/` → `http://127.0.0.1:8000/api/v1/`
- `/health` → `http://127.0.0.1:8000/health`
- `/docs` → `http://127.0.0.1:8000/docs`
- `/openapi.json` → `http://127.0.0.1:8000/openapi.json`
- everything else → `http://127.0.0.1:3000/`

It also preserves:

- `Host: builder.amarktai.com`
- `X-Real-IP`
- `X-Forwarded-For`
- `X-Forwarded-Proto`
- WebSocket upgrade headers
- `client_max_body_size 50M`

## 8. TLS / Certbot

If certificates already exist for `builder.amarktai.com`, keep the `ssl_certificate` paths in the site config as-is.

If certificates do not exist yet:

```bash
sudo certbot --nginx -d builder.amarktai.com
sudo nginx -t
sudo systemctl reload nginx
```

## 9. Smoke-test commands

Direct container paths:

```bash
curl -H "Host: builder.amarktai.com" http://127.0.0.1:8000/health
curl -H "Host: builder.amarktai.com" http://127.0.0.1:8000/api/v1/health
curl -I http://127.0.0.1:3000/
```

Expected result:

- `/health` → `200`
- `/api/v1/health` → `200`
- frontend localhost `:3000` → `200`

Public paths:

```bash
curl -I https://builder.amarktai.com/
curl -I https://builder.amarktai.com/api/v1/health
curl -I https://builder.amarktai.com/docs
curl -I https://builder.amarktai.com/openapi.json
curl -I https://builder.amarktai.com/api/health
```

Expected result:

- `/` → `200`
- `/api/v1/health` → `200`
- `/docs` → `200`
- `/openapi.json` → `200`
- `/api/health` → `404` (expected)

## 10. Repeatable verification script

```bash
cd /var/www/amarktai-marketing/repo
chmod +x deploy/verify-builder-go-live.sh
DOMAIN=builder.amarktai.com ./deploy/verify-builder-go-live.sh
```

Expected result:

- Each line prints `PASS`
- Final line prints `All go-live checks passed.`

## 11. Useful diagnostics

```bash
cd /var/www/amarktai-marketing/repo
docker compose logs backend --tail=100
docker compose logs frontend --tail=100
docker compose logs celery_worker --tail=100
docker compose logs celery_beat --tail=100
sudo tail -n 100 /var/log/nginx/builder.amarktai.com.error.log
```
