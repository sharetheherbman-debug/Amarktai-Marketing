# Pre-Deployment Checklist — builder.amarktai.com

Complete every item before calling the production path healthy.

## Shared VPS model

- [ ] Host Nginx is the only public listener on `:80` and `:443`
- [ ] Docker Compose exposes only `127.0.0.1:8000` and `127.0.0.1:3000`
- [ ] PostgreSQL and Redis have no host port bindings

## Secrets and env

- [ ] Repository root `.env` exists and is **not** committed
- [ ] Root `.env` contains `POSTGRES_PASSWORD`, `DOMAIN=builder.amarktai.com`, and `VITE_API_URL=/api/v1`
- [ ] `backend/.env` exists and is **not** committed
- [ ] `backend/.env` permissions are restricted (`chmod 600 backend/.env`)
- [ ] `APP_ENVIRONMENT=production`
- [ ] `FRONTEND_URL=https://builder.amarktai.com`
- [ ] `CORS_ORIGINS=["https://builder.amarktai.com"]`
- [ ] `DATABASE_URL=postgresql://amarktai:${POSTGRES_PASSWORD}@db:5432/amarktai`
- [ ] `REDIS_URL=redis://redis:6379/0`
- [ ] `JWT_SECRET` is set to a non-default `openssl rand -hex 32` value
- [ ] `ENCRYPTION_KEY` is set to a non-default `openssl rand -base64 32` value
- [ ] `STRIPE_WEBHOOK_SECRET` is set for production
- [ ] `GENX_API_KEY` is set for full AI generation

## Docker Compose

- [ ] `docker compose config` exits `0`
- [ ] `docker compose up -d --build` exits `0`
- [ ] `docker compose ps` shows `db` and `redis` healthy
- [ ] `docker compose ps` shows `backend`, `frontend`, `celery_worker`, and `celery_beat` running

## Host Nginx

- [ ] `deploy/nginx/builder.amarktai.com.conf` is copied to `/etc/nginx/sites-available/builder.amarktai.com`
- [ ] `/etc/nginx/sites-enabled/builder.amarktai.com` symlink points to that file
- [ ] `sudo nginx -t` prints `syntax is ok` and `test is successful`
- [ ] `sudo systemctl reload nginx` exits `0`
- [ ] Nginx routes `/api/v1/` to `127.0.0.1:8000`
- [ ] Nginx routes `/health`, `/docs`, and `/openapi.json` to `127.0.0.1:8000`
- [ ] Nginx routes all frontend paths to `127.0.0.1:3000`
- [ ] Nginx forwards `Host`, `X-Real-IP`, `X-Forwarded-For`, and `X-Forwarded-Proto`

## Smoke tests

- [ ] `curl -H "Host: builder.amarktai.com" http://127.0.0.1:8000/health` returns `200`
- [ ] `curl -H "Host: builder.amarktai.com" http://127.0.0.1:8000/api/v1/health` returns `200`
- [ ] `curl -I http://127.0.0.1:3000/` returns `200`
- [ ] `curl -I https://builder.amarktai.com/` returns `200`
- [ ] `curl -I https://builder.amarktai.com/api/v1/health` returns `200`
- [ ] `curl -I https://builder.amarktai.com/docs` returns `200`
- [ ] `curl -I https://builder.amarktai.com/openapi.json` returns `200`
- [ ] `curl -I https://builder.amarktai.com/api/health` returns `404` (expected)

## Repeatable verification

- [ ] `chmod +x deploy/verify-builder-go-live.sh`
- [ ] `DOMAIN=builder.amarktai.com ./deploy/verify-builder-go-live.sh` prints only `PASS` lines and finishes with `All go-live checks passed.`
