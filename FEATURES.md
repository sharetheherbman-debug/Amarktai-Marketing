# Features — AmarktAI Marketing

All features listed below are implemented and available in the current release unless otherwise noted.

---

## Business & App Management

### Multi-Business Setup ✅
Add and manage up to 20 businesses or apps per user account. Each business stores its own name, website URL, description, category, target audience, key features, brand voice, market/location, and content goals. All content generation and scheduling runs in the context of the selected business.

Route: **Dashboard → Businesses** (`/dashboard/webapps`)

### Brand Media Upload ✅
Upload brand assets (logos, product images, marketing media) directly to a business profile. Accepted formats: JPEG, PNG, GIF, WebP, SVG, MP4, WebM, QuickTime, PDF — up to 50 MB per file. Assets are stored server-side and referenced by AI workflows during content generation.

Route: **Dashboard → Businesses → Edit Business → Brand Media Assets**

### Scraper Source URLs ✅
Beyond the main website URL, users can specify additional pages to scrape (e.g. product pages, pricing pages, blog). The AI uses all scraped content as context for content generation. Scraping is powered by Firecrawl (primary) with httpx + BeautifulSoup as fallback.

Route: **Dashboard → Businesses → Add / Edit Business → Additional Scraper Source URLs**

---

## Core AI Features

### AI Content Generation ✅
Generate platform-optimised content for 10+ social networks. Supports long-form, short-form, threads, captions, and hashtag packs. Uses GenX as the primary provider with fallback to Qwen/HuggingFace and optional OpenAI/Gemini compatibility.

### Viral Predictor ✅
Analyses content before publishing and assigns a viral probability score. Factors in trending topics, audience engagement patterns, and historical platform data.

### Performance Predictor ✅
Forecasts expected reach, impressions, and engagement rate for a piece of content before it goes live. Compares predictions against post-publish actuals over time.

### Content Repurposer ✅
Automatically transforms a single piece of content into formats suited for multiple platforms (e.g., LinkedIn article → Twitter thread → Instagram caption → YouTube description).

---

## Publishing & Scheduling

### Smart Scheduler ✅
AI-powered scheduling engine that determines the optimal publish time per platform based on audience activity data. Supports bulk scheduling and calendar drag-and-drop.

### Autonomous Posting ✅
Queue content once and let the system publish autonomously across all connected platforms. Handles rate limits, retries, and failure alerts without manual intervention.

### Content Calendar ✅
Visual monthly/weekly calendar view showing all scheduled, published, and draft content across every connected account. Filter by platform, campaign, or tag.

---

## Optimisation & Testing

### A/B Testing ✅
Create variant versions of any post and run split tests across audiences. Automatically promotes the winning variant based on configurable engagement thresholds.

### Engagement Queue ✅
Prioritised inbox for incoming comments, messages, and mentions. AI suggests reply drafts ranked by urgency and sentiment. Supports bulk actions.

---

## Intelligence & Research

### Competitor Intelligence ✅
Powered by Firecrawl web scraping. Tracks competitor content calendars, posting frequency, engagement rates, and trending topics. Surfaces actionable insights via the dashboard.

### 10 Power Tools ✅
A suite of specialised AI writing tools including:
- Hook generator
- CTA optimiser
- Hashtag researcher
- Bio writer
- Caption rewriter
- Tone adjuster
- Trend spotter
- Keyword extractor
- Audience persona builder
- Content gap analyser

---

## Content Creation

### Blog Generator ✅
Produces full SEO-optimised blog posts from a keyword or topic. Includes headline, meta description, structured headings, and internal link suggestions.

### Lead Management ✅
Capture, score, and nurture leads generated from social content. Tracks lead source, engagement history, and pipeline stage. Integrates with email sequences.

---

## Platform Integrations

### Platform OAuth ✅ Ready
OAuth flows implemented and ready for the following platforms:

| Platform   | Status         |
|------------|----------------|
| YouTube    | ✅ Ready       |
| TikTok     | ✅ Ready       |
| Instagram  | ✅ Ready       |
| LinkedIn   | ✅ Ready       |
| Twitter/X  | ✅ Ready       |
| Facebook   | ✅ Ready       |
| Pinterest  | ✅ Ready       |
| Reddit     | ✅ Ready       |
| Bluesky    | ✅ Ready       |
| Telegram   | ✅ Ready       |
| Snapchat   | ✅ Ready       |

---

## AI Provider Strategy

The platform uses a tiered provider approach to maximise uptime and cost efficiency:

| Priority | Provider       | Role                                  |
|----------|----------------|---------------------------------------|
| 1        | Firecrawl      | Web scraping and competitive research |
| 2        | GenX           | Primary unified LLM router            |
| 3        | Qwen (DashScope) | Legacy fallback LLM                 |
| 4        | HuggingFace    | Legacy fallback LLM                   |
| 5        | OpenAI         | Optional enhancement (GPT-4 class)    |
| 6        | Gemini         | Optional enhancement (Gemini class)   |

If a higher-priority provider fails or returns an error, the system automatically falls back to the next available provider. Only Qwen and HuggingFace keys are required for the platform to be fully operational.

---

## Beta Status

The following limitations apply to the current beta release:

| Area                       | Status                  | Detail                                                                                    |
|----------------------------|-------------------------|-------------------------------------------------------------------------------------------|
| Stripe payments            | ⬜ Deferred (beta)      | Subscription billing is not integrated. No payment flows exist in this release.           |
| SMTP / transactional email | ⬜ Deferred (beta)      | Email delivery (SendGrid, Mailgun, etc.) is not configured. Will be added post-beta.       |
| AmarktAI Network brain     | 🔮 Future               | The internal AmarktAI super brain is under development. Current generation stack is Firecrawl + Qwen + HuggingFace (+ optional OpenAI/Gemini). |
| Platform OAuth             | ⚙️ Requires credentials | OAuth flows are wired. Each platform requires its own API credentials in `backend/.env`.  |
