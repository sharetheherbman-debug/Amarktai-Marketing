# Pre-Deployment Checklist — marketing.amarktai.com

## Domain and environment

- [ ] Deploy target is `marketing.amarktai.com`
- [ ] No deployment step from this repo references the Builder app domain
- [ ] Repo path is `/var/www/amarktai-marketing/repo`

## Backend (systemd)

- [ ] `backend/.env` exists and is production-ready
- [ ] `FRONTEND_URL=https://marketing.amarktai.com`
- [ ] `CORS_ORIGINS=["https://marketing.amarktai.com"]`
- [ ] `GENX_API_KEY` set (required for full AI generation)
- [ ] `amarktai-marketing-api.service` installed from `deploy/systemd/amarktai-marketing-api.service`
- [ ] service runs on `127.0.0.1:8010`

## Frontend (static)

- [ ] frontend built with `npm run build`
- [ ] static files synced to `/var/www/amarktai-marketing/current/app/dist`

## Database and migrations

- [ ] `alembic upgrade head` completed for clean DB path
- [ ] `python3 scripts/repair_live_user_columns.py` run for existing live MariaDB if needed
- [ ] user auth/referral/billing columns present in `users` table

## Nginx

- [ ] `deploy/nginx/marketing.amarktai.com.conf` installed to host Nginx
- [ ] `/api/v1/` proxies to `127.0.0.1:8010`
- [ ] `/health`, `/docs`, `/openapi.json` proxy to backend `127.0.0.1:8010`
- [ ] SPA fallback serves `/index.html` from `/var/www/amarktai-marketing/current/app/dist`
- [ ] `sudo nginx -t` succeeds

## Functional checks

- [ ] login works
- [ ] `/health` returns 200
- [ ] `/api/v1/health` returns 200
- [ ] `/dashboard/groups` is disabled safely (coming later / redirect)
- [ ] settings/integrations readiness truthfully shows configured vs not_configured providers

## Repeatable verification

- [ ] `./deploy/verify-marketing-go-live.sh` passes
- [ ] `./scripts/marketing_local_check.sh` passes in local/staging
- [ ] `./scripts/marketing_go_live_smoke.sh` passes with production domain settings
