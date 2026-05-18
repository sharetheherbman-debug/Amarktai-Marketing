# AmarktAI Marketing

> **Autonomous AI Marketing at Scale**

AmarktAI Marketing is a full-stack SaaS platform that automates content creation, scheduling, competitor intelligence, and cross-platform publishing using a tiered AI provider strategy.

---

## Tech Stack

| Layer        | Technology                                                              |
|--------------|-------------------------------------------------------------------------|
| Frontend     | React 19 + Vite + TypeScript + Tailwind CSS + shadcn/ui + framer-motion |
| Backend      | FastAPI + SQLAlchemy + Alembic + Celery                                 |
| Database     | PostgreSQL 15 — `psycopg2-binary` driver — hosted on Webdock VPS        |
| Cache/Queue  | Redis 7                                                                 |
| Auth         | JWT HS256 — email/password only                                         |
| AI Primary   | GenX (unified provider, 59-model routing)                               |
| AI Fallback  | Qwen (DashScope), HuggingFace                                           |
| AI Optional  | OpenAI, Gemini (Google)                                                 |
| Scraping     | Firecrawl                                                               |

---

## AI Provider Strategy

Requests flow through providers in priority order:

```
Firecrawl (web scraping) → GenX (primary LLM router) → Qwen (fallback) → HuggingFace (fallback) → OpenAI (optional) → Gemini (optional)
```

Only **GenX** is required for AI generation. Firecrawl is strongly recommended for competitor intelligence. Legacy provider keys remain optional compatibility fallbacks.

---

## Project Structure

```
Amarktai-Marketing/
├── app/                  # React frontend (Vite)
│   ├── src/
│   │   ├── app/          # Page-level route components
│   │   ├── components/   # ui, layout, dashboard, auth components
│   │   ├── hooks/        # Custom React hooks
│   │   ├── lib/          # API client, auth utilities
│   │   └── types/        # TypeScript type definitions
│   └── package.json
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/          # Route handlers
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── schemas/      # Pydantic request/response schemas
│   │   ├── services/     # Business logic and AI integrations
│   │   └── core/         # Config, security, database session
│   ├── alembic/          # Database migration scripts
│   └── requirements.txt
├── deploy/               # Deployment configs and scripts
├── docs/                 # Additional documentation
├── docker-compose.yml
├── nginx.conf
└── README.md
```

---

## Quick Start

See [QUICK_START.md](./QUICK_START.md) for full setup instructions.

**TL;DR:**

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # edit DATABASE_URL, JWT_SECRET, QWEN_API_KEY
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd app
npm install
npm run dev                 # http://localhost:5173
```

---

## Environment Variables

| Variable            | Required | Description                                                  |
|---------------------|----------|--------------------------------------------------------------|
| `DATABASE_URL`      | ✅       | `postgresql://user:pass@localhost:5432/amarktai`             |
| `JWT_SECRET`        | ✅       | Random secret for JWT signing (`openssl rand -hex 32`)       |
| `ENCRYPTION_KEY`    | ✅       | Base64 key for credential encryption (`openssl rand -base64 32`) |
| `REDIS_URL`         | ✅       | `redis://localhost:6379/0`                                   |
| `GENX_API_KEY`      | ✅       | GenX unified AI API key (primary provider)                    |
| `GENX_BASE_URL`     | ✅       | GenX API base URL                                              |
| `GENX_DEFAULT_MODEL`| ✅       | Default GenX model for generation                              |
| `QWEN_API_KEY`      | ⬜       | DashScope API key (legacy fallback provider)                  |
| `HUGGINGFACE_TOKEN` | ⬜       | HuggingFace access token (legacy fallback provider)           |
| `FIRECRAWL_API_KEY` | ⭐       | Recommended for competitor scraping and web data             |
| `OPENAI_API_KEY`    | ⬜       | Optional AI enhancement                                      |
| `GEMINI_API_KEY`    | ⬜       | Optional AI enhancement                                      |
| `SENDGRID_API_KEY`  | ⬜       | Deferred — SMTP email not required for beta                  |
| `STRIPE_SECRET_KEY` | ⬜       | Deferred — Payments not integrated in beta                   |
| `ADMIN_EMAIL`       | ✅       | Default admin account email address                          |
| `CORS_ORIGINS`      | ✅       | Comma-separated allowed frontend origins                     |
| `MEDIA_UPLOAD_DIR`  | ⬜       | Directory for uploaded media assets (default: `/tmp/amarktai_media`). Use a persistent volume in production. |

---

## Deployment

Deployed on a **Webdock VPS** running Ubuntu 22.04. The PostgreSQL connection string format used throughout is:

```
postgresql://amarktai_user:yourpassword@localhost:5432/amarktai
```

See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for the full guide and [DEPLOY_CHECKLIST.md](./DEPLOY_CHECKLIST.md) for the pre-launch checklist.

---

## One-Source-of-Truth Map

This table tells you exactly where each critical workflow lives in the product. There is exactly one place for each.

| Workflow                       | Where in the UI                                              | Backend Route                                      |
|--------------------------------|--------------------------------------------------------------|----------------------------------------------------|
| **Add / manage businesses**    | Dashboard → Businesses (`/dashboard/webapps`)                | `GET/POST /api/v1/webapps/`                        |
| **Edit business details**      | Dashboard → Businesses → Edit (`/dashboard/webapps/:id/edit`) | `PUT /api/v1/webapps/{id}`                        |
| **Scraper source URLs**        | Edit Business form → Additional Scraper Source URLs          | `PUT /api/v1/webapps/{id}` (`scraper_source_urls`) |
| **Trigger website rescrape**   | Businesses list → Re-scan button                             | `POST /api/v1/webapps/{id}/scrape`                |
| **Upload brand media**         | Edit Business → Brand Media Assets card                      | `POST /api/v1/webapps/{id}/media`                 |
| **Delete media asset**         | Edit Business → Brand Media Assets → hover delete            | `DELETE /api/v1/webapps/{id}/media/{asset_id}`    |
| **Connect social platforms**   | Dashboard → Platforms (`/dashboard/platforms`)               | `POST /api/v1/platforms/{platform}/connect`        |
| **Disconnect social platform** | Dashboard → Platforms → Disconnect                           | `POST /api/v1/platforms/{platform}/disconnect`     |
| **Add / update API keys**      | Dashboard → Integrations (`/dashboard/integrations`)         | `POST /api/v1/integrations/api-keys`               |
| **View API key status**        | Dashboard → Integrations                                     | `GET /api/v1/integrations/api-keys`                |
| **Provider key setup (alt)**   | Dashboard → Settings → API Keys                              | `PUT /api/v1/settings/api-keys`                    |

> **Note on API keys:** Two key-management surfaces exist because they serve different purposes.
> - **Integrations page** → stores per-user keys for AI providers (Firecrawl, Qwen, HuggingFace, OpenAI, Gemini). These override the system environment keys for that user's requests.
> - **Settings page** → shortcut that links directly to Integrations. Not a separate storage system.

---

## Features

See [FEATURES.md](./FEATURES.md) for the complete feature list with status markers.

Highlights:
- AI content generation across 10+ social platforms
- Autonomous scheduling and publishing
- Viral score and performance prediction
- Competitor intelligence via Firecrawl
- A/B testing and content repurposing
- Lead management and blog generation

---

## Integrations

See [INTEGRATIONS_LIST.md](./INTEGRATIONS_LIST.md) for all supported third-party integrations.
