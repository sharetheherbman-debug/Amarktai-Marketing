# MARKETING_GO_LIVE_AUDIT_REPORT

## What was fixed

1. **Domain and deployment corrections (PR #4 repair)**
   - Replaced marketing deployment guidance/config from wrong builder-domain assumptions to `marketing.amarktai.com`.
   - Removed builder Nginx site template and added `deploy/nginx/marketing.amarktai.com.conf` for host Nginx + systemd backend + static frontend.
   - Added `deploy/systemd/amarktai-marketing-api.service` for backend runtime on `127.0.0.1:8010`.
   - Updated deploy script and verification script to production truth.

2. **Systemd/static production path retained**
   - Deployment docs now target:
     - repo: `/var/www/amarktai-marketing/repo`
     - backend service: `amarktai-marketing-api.service`
     - static frontend root: `/var/www/amarktai-marketing/current/app/dist`
   - Docker Compose remains documented as local/future only with `COMPOSE_PROJECT_NAME=amarktai_marketing`.

3. **DB migration/live repair safety**
   - Alembic migration files updated to use explicit string lengths for MySQL/MariaDB compatibility.
   - Added idempotent live repair script: `scripts/repair_live_user_columns.py` to add missing `users` columns/index/fk only.
   - Deployment docs now explain when to run Alembic vs live repair script.

4. **Groups disabled for go-live stability**
   - Removed Groups from dashboard navigation.
   - Replaced `/dashboard/groups` with a safe “coming later” page.

5. **AI generation truthfulness + social rules**
   - Content generation now reports `generation_status` as `configured` or `not_configured` based on GenX availability.
   - Added explicit degraded messaging when `GENX_API_KEY` is missing.
   - Added data-driven social guardrails module `backend/app/services/social_rules.py` and wired guidance into prompt generation.

6. **Learning loop and metrics ingestion**
   - Added analytics endpoints for manual metrics and CSV import:
     - `POST /api/v1/analytics/manual-metrics`
     - `POST /api/v1/analytics/import-csv`
     - `GET /api/v1/analytics/learning-status`
   - Added content score calculation and learning status in analytics summary.
   - Dashboard and analytics UI now reflect learning active/inactive based on metric records.

7. **Readiness/integrations truthfulness**
   - Added `GET /api/v1/settings/readiness` returning configured/not_configured states for core providers and OAuth credentials.
   - Integrations UI now shows go-live readiness checklist and missing required items.

8. **Smoke scripts added**
   - `scripts/marketing_local_check.sh`
   - `scripts/marketing_go_live_smoke.sh`

## Files changed

- `DEPLOYMENT_GUIDE.md`
- `DEPLOY_CHECKLIST.md`
- `README.md`
- `MARKETING_GO_LIVE_AUDIT_REPORT.md`
- `docker-compose.yml`
- `deploy/docker-compose.env.example`
- `deploy/deploy.sh`
- `deploy/ecosystem.config.cjs`
- `deploy/app-registration.json`
- `deploy/nginx/marketing.amarktai.com.conf` (added)
- `deploy/nginx/builder.amarktai.com.conf` (removed)
- `deploy/systemd/amarktai-marketing-api.service` (added)
- `deploy/verify-marketing-go-live.sh` (added)
- `deploy/verify-builder-go-live.sh` (removed)
- `scripts/marketing_local_check.sh` (added)
- `scripts/marketing_go_live_smoke.sh` (added)
- `scripts/repair_live_user_columns.py` (added)
- `backend/.env.example`
- `backend/alembic/versions/0001_initial.py`
- `backend/alembic/versions/0002_power_tools.py`
- `backend/alembic/versions/0003_leads_new_platforms.py`
- `backend/alembic/versions/0004_blog_posts.py`
- `backend/alembic/versions/0005_business_groups.py`
- `backend/alembic/versions/0007_platform_ad_budget.py`
- `backend/alembic/versions/0008_jwt_auth.py`
- `backend/app/api/v1/endpoints/content.py`
- `backend/app/api/v1/endpoints/analytics.py`
- `backend/app/api/v1/endpoints/settings.py`
- `backend/app/schemas/analytics.py`
- `backend/app/services/hf_generator.py`
- `backend/app/services/social_rules.py` (added)
- `app/src/app/groups/page.tsx`
- `app/src/components/layout/DashboardLayout.tsx`
- `app/src/components/dashboard/ContentStudio.tsx`
- `app/src/app/integrations/page.tsx`
- `app/src/app/analytics/page.tsx`
- `app/src/app/dashboard/page.tsx`
- `app/src/lib/api.ts`
- `app/src/types/index.ts`

## Remaining blockers

1. **Frontend lint baseline is still failing due pre-existing repo-wide lint violations** (unrelated to this go-live repair; build passes).
2. **Live secrets are not stored in repository** — production keys must be present on VPS `.env`.
3. **Actual provider connectivity must be validated on VPS runtime** (GenX/social/email/Stripe) after env is set.

## Exact production deploy commands for this VPS

```bash
cd /var/www/amarktai-marketing/repo
git pull --ff-only

cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/alembic upgrade head
cd ..
python3 scripts/repair_live_user_columns.py

cd app
npm install
npm run build
sudo mkdir -p /var/www/amarktai-marketing/current/app/dist
sudo rsync -a --delete dist/ /var/www/amarktai-marketing/current/app/dist/
cd ..

sudo cp deploy/systemd/amarktai-marketing-api.service /etc/systemd/system/amarktai-marketing-api.service
sudo systemctl daemon-reload
sudo systemctl enable amarktai-marketing-api.service
sudo systemctl restart amarktai-marketing-api.service

sudo cp deploy/nginx/marketing.amarktai.com.conf /etc/nginx/sites-available/marketing.amarktai.com
sudo ln -sf /etc/nginx/sites-available/marketing.amarktai.com /etc/nginx/sites-enabled/marketing.amarktai.com
sudo nginx -t
sudo systemctl reload nginx

./deploy/verify-marketing-go-live.sh
./scripts/marketing_go_live_smoke.sh
```

## Key/integration status (configured vs still required)

Repository code now reports these truthfully at `/api/v1/settings/readiness`.
From repo alone (without VPS runtime env), these should be treated as **still required until confirmed on server**:

- **GENX_API_KEY**: required for full real AI generation.
- **Social OAuth credentials**: required per platform to mark configured.
- **Email provider (RESEND_API_KEY)**: optional for core posting, required for configured email workflows.
- **Stripe keys/webhook secret**: optional unless paid billing is enabled.
- **Firecrawl key**: optional but recommended for scraper intelligence.

## Go / No-Go verdict

**Conditional GO**

Go-live code-path repairs are in place for `marketing.amarktai.com`, groups are safely disabled, migrations/repair tooling is present, backend import check passes, frontend build passes, and readiness is now truthful.

Final go-live is **conditional** on VPS env/key configuration verification and successful smoke run in production.
