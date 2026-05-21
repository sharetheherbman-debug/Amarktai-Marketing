# PROVIDER_SETUP_GUIDE
## Required for launch
- Set `GENX_API_KEY`.
- Set `GENX_MODEL_COPY` or `GENX_DEFAULT_MODEL` for premium text.
- Set `GENX_MODEL_IMAGE`, `GENX_MODEL_VIDEO`, `GENX_MODEL_AUDIO`, and `GENX_MODEL_AVATAR` for premium multimodal readiness.
- Set `FIRECRAWL_API_KEY` for business intelligence enrichment.

## Optional fallbacks
- Set `QWEN_API_KEY` for budget/high-volume creative text fallback.
- Set `HUGGINGFACE_TOKEN` only for truthful fallback tasks.
- Set `PIXABAY_API_KEY` for real stock image/video asset search.

## Launch flags
- Leave `ENABLE_BILLING=false` until billing work is resumed.
- Leave `ENABLE_DEMO_MEDIA=false` in production.
- Set `ADMIN_EMAIL` and optional `ADMIN_USER_IDS` for owner access.
- Set `MEDIA_UPLOAD_DIR` to the persistent deployment mount before go-live.

## Validation
- `GET /api/v1/settings/readiness`
- `GET /api/v1/settings/provider-resolution`
- `GET /api/v1/settings/providers/debug`
