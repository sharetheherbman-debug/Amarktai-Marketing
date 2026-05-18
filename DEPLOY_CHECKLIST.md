# Pre-Deployment Checklist — AmarktAI Marketing

Complete every item before going live. Items marked ✅ are hard requirements.

---

## Infrastructure

- [ ] Server running Ubuntu 22.04 LTS with 4 GB+ RAM
- [ ] PostgreSQL 15 installed and service running (`sudo systemctl status postgresql`)
- [ ] Redis 7 installed and service running (`redis-cli ping` → `PONG`)
- [ ] Nginx installed and enabled

---

## Database

- [ ] PostgreSQL database `amarktai` created
- [ ] PostgreSQL user created and granted full privileges on `amarktai` database
- [ ] `DATABASE_URL` set to `postgresql://amarktai_user:PASSWORD@localhost:5432/amarktai`
- [ ] Alembic migrations applied (`alembic upgrade head` exits with no errors)

---

## Security & Secrets

- [ ] `JWT_SECRET` set to a 64-character hex string (`openssl rand -hex 32`)
- [ ] `ENCRYPTION_KEY` set to a base64 key (`openssl rand -base64 32`)
- [ ] No secrets committed to source control (`.env` is in `.gitignore`)
- [ ] `.env` file has restricted permissions (`chmod 600 .env`)
- [ ] `ADMIN_EMAIL` overridden to your actual admin account email (default is the AmarktAI Network owner email — change this if you are deploying a separate instance)
- [ ] `STRIPE_WEBHOOK_SECRET` set — unsigned Stripe webhooks are **rejected in production**

---

## AI Providers

- [ ] `GENX_API_KEY` set (**required** — primary unified AI provider)
- [ ] `GENX_BASE_URL` set (default: `https://api.genxai.co/v1`)
- [ ] `GENX_DEFAULT_MODEL` set (default: `genx-chat-pro`)
- [ ] `FIRECRAWL_API_KEY` set (competitor intelligence scraping, strongly recommended)
- [ ] `QWEN_API_KEY` set if you want a secondary text-generation fallback (optional)
- [ ] `HUGGINGFACE_TOKEN` set if you want an additional fallback (optional)
- [ ] `OPENAI_API_KEY` set if OpenAI compatibility is desired (optional)
- [ ] `GEMINI_API_KEY` set if Gemini is desired (optional)

---

## Payments (Stripe — active and required for paid plans)

- [ ] `STRIPE_SECRET_KEY` set
- [ ] `STRIPE_WEBHOOK_SECRET` set (see Security section — **required** for production webhook security)
- [ ] `STRIPE_PRICE_ID_PRO` set to the Stripe price ID for the Pro plan
- [ ] `STRIPE_PRICE_ID_BUSINESS` set to the Stripe price ID for the Business plan
- [ ] `STRIPE_PRICE_ID_ENTERPRISE` set to the Stripe price ID for the Enterprise plan
- [ ] Stripe webhook endpoint registered at `https://yourdomain.com/api/v1/billing/webhook`

---

## Application Configuration

- [ ] `APP_ENVIRONMENT` set to `production`
- [ ] `ADMIN_EMAIL` set to the admin account email
- [ ] `CORS_ORIGINS` set to the production domain (e.g., `https://yourdomain.com`)
- [ ] `REDIS_URL` set to `redis://localhost:6379/0`
- [ ] `FRONTEND_URL` set to `https://yourdomain.com`

---

## Optional Integrations

- [ ] `RESEND_API_KEY` — transactional email (recommended for notifications)
- [ ] `SENTRY_DSN` — error monitoring (recommended for production observability)
- [ ] `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` + `AWS_S3_BUCKET` set (media storage, optional)

---

## Backend Deployment

- [ ] Python virtualenv created and `requirements.txt` installed
- [ ] `amarktai-api` systemd service enabled and running
- [ ] `amarktai-worker` systemd service (Celery worker) enabled and running
- [ ] `amarktai-beat` systemd service (Celery beat) enabled and running
- [ ] Backend health check passes: `curl https://yourdomain.com/api/health`

---

## Frontend Deployment

- [ ] Node 18+ installed
- [ ] `npm run build` completes without errors (output in `app/dist/`)
- [ ] `VITE_API_URL` set correctly (or Nginx proxy handles `/api` routing)
- [ ] Nginx serving `app/dist/` for frontend routes

---

## Nginx & SSL

> ⚠️ The repo ships with HTTP-only nginx config. SSL must be configured on the VPS before go-live.
> See the comments in `nginx.conf` for step-by-step SSL setup instructions.

- [ ] Copy `nginx.conf` to server and replace `YOUR_DOMAIN` with your actual domain
- [ ] Nginx config passes syntax check (`sudo nginx -t`)
- [ ] Nginx configured to proxy `/api/` to `127.0.0.1:8000`
- [ ] Nginx configured to serve `app/dist/` with SPA fallback (`try_files $uri /index.html`)
- [ ] SSL certificate issued via Certbot (`sudo certbot certonly --webroot -w /var/www/certbot -d YOUR_DOMAIN`)
- [ ] Uncomment HTTPS redirect and SSL lines in nginx.conf
- [ ] HTTPS redirect active (HTTP → HTTPS)
- [ ] `sudo certbot renew --dry-run` passes

---

## Final Smoke Tests

- [ ] Frontend loads at `https://yourdomain.com`
- [ ] Login page renders and authentication works end-to-end
- [ ] Dashboard loads without console errors
- [ ] At least one AI content generation request completes successfully via GenX
- [ ] Stripe checkout flow works end-to-end (test mode)
- [ ] Stripe webhook receives a test event and processes correctly
- [ ] Scheduled task appears in Celery worker logs

---

> See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for detailed instructions on each step.
