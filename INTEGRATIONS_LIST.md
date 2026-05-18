# Integrations — AmarktAI Marketing

Third-party integrations grouped by category. Configure each via environment variables in `backend/.env`.

**Legend:** ✅ Required &nbsp; ⭐ Recommended &nbsp; ⬜ Optional

---

## AI Providers

| Integration         | Env Variable          | Status        | Notes                                      |
|---------------------|-----------------------|---------------|--------------------------------------------|
| GenX                | `GENX_API_KEY`        | ✅ Required   | Primary unified provider for all AI tasks  |
| Qwen (DashScope)    | `QWEN_API_KEY`        | ⬜ Optional   | Legacy fallback provider                   |
| HuggingFace         | `HUGGINGFACE_TOKEN`   | ⬜ Optional   | Legacy fallback provider                   |
| Firecrawl           | `FIRECRAWL_API_KEY`   | ⭐ Recommended| Web scraping for competitor intelligence   |
| OpenAI              | `OPENAI_API_KEY`      | ⬜ Optional   | GPT-4 class enhancement                    |
| Gemini (Google)     | `GEMINI_API_KEY`      | ⬜ Optional   | Gemini class enhancement                   |

Provider fallback order: **GenX → Qwen → HuggingFace → OpenAI → Gemini**

---

## Social Platforms

All platforms use OAuth 2.0. Store tokens via the platform credentials settings in the dashboard.

| Platform   | Env Variable Prefix    | Status        | Notes                          |
|------------|------------------------|---------------|--------------------------------|
| YouTube    | `YOUTUBE_`             | ⭐ Recommended| Video upload and description   |
| TikTok     | `TIKTOK_`              | ⭐ Recommended| Short video publishing         |
| Instagram  | `INSTAGRAM_`           | ⭐ Recommended| Posts, Reels, Stories          |
| LinkedIn   | `LINKEDIN_`            | ⭐ Recommended| Professional content           |
| Twitter/X  | `TWITTER_`             | ⭐ Recommended| Tweets and threads             |
| Facebook   | `FACEBOOK_`            | ⭐ Recommended| Pages and Groups               |
| Pinterest  | `PINTEREST_`           | ⬜ Optional   | Pin publishing                 |
| Reddit     | `REDDIT_`              | ⬜ Optional   | Subreddit posting              |
| Bluesky    | `BLUESKY_`             | ⬜ Optional   | AT Protocol posting            |
| Telegram   | `TELEGRAM_BOT_TOKEN`   | ⬜ Optional   | Channel broadcasting           |
| Snapchat   | `SNAPCHAT_`            | ⬜ Optional   | Story publishing               |

---

## Media Generation

| Integration    | Env Variable              | Status      | Notes                              |
|----------------|---------------------------|-------------|------------------------------------|
| Leonardo.ai    | `LEONARDO_API_KEY`        | ⬜ Optional | AI image generation                |
| Stability AI   | `STABILITY_API_KEY`       | ⬜ Optional | Stable Diffusion image generation  |
| Replicate      | `REPLICATE_API_TOKEN`     | ⬜ Optional | Run open-source media models       |
| ElevenLabs     | `ELEVENLABS_API_KEY`      | ⬜ Optional | AI voice synthesis for video audio |

---

## Email

| Integration | Env Variable        | Status                  | Notes                                                             |
|-------------|---------------------|-------------------------|-------------------------------------------------------------------|
| SendGrid    | `SENDGRID_API_KEY`  | ⬜ Deferred (beta)      | Transactional email — will be configured post-beta                |
| Mailgun     | `MAILGUN_API_KEY`   | ⬜ Optional             | Alternative transactional email provider                          |

---

## Payments

| Integration | Env Variable                                                             | Status                  | Notes                                              |
|-------------|--------------------------------------------------------------------------|-------------------------|----------------------------------------------------|
| Stripe      | `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`  | ⬜ Deferred (beta)      | Subscription billing — not integrated in beta      |

---

## Storage

| Integration      | Env Variables                                                      | Status        | Notes                              |
|------------------|--------------------------------------------------------------------|---------------|------------------------------------|
| AWS S3           | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET`, `AWS_REGION` | ⭐ Recommended | Media and asset storage |
| Cloudflare R2    | `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_ENDPOINT` | ⬜ Optional | S3-compatible, no egress fees |

---

## Scraping & Data

| Integration | Env Variable        | Status        | Notes                                              |
|-------------|---------------------|---------------|----------------------------------------------------|
| Firecrawl   | `FIRECRAWL_API_KEY` | ⭐ Recommended| Structured web scraping for competitor research    |
| SerpAPI     | `SERPAPI_KEY`       | ⬜ Optional   | Google Trends and SERP data for keyword research   |

---

## Monitoring (Optional)

| Integration | Env Variable       | Status      | Notes                            |
|-------------|--------------------|-------------|----------------------------------|
| Sentry      | `SENTRY_DSN`       | ⬜ Optional | Error tracking and alerting      |

---

## Authentication

Authentication is handled **internally** using JWT HS256 with email/password. There are no external authentication providers. No Clerk. No Supabase Auth. No Auth0.

| Component   | Implementation                              |
|-------------|---------------------------------------------|
| Token type  | JWT, signed with HS256                      |
| Secret      | `JWT_SECRET` environment variable           |
| Storage     | `Authorization: Bearer <token>` header      |
| Credentials | Encrypted with `ENCRYPTION_KEY` before DB storage |
