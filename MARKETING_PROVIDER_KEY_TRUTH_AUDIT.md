# Marketing Provider Key Truth Audit

## Provider State Classification

| State | Meaning |
|-------|---------|
| `missing_key` | No key in DB or env |
| `decrypt_failed` | Row exists but decryption threw exception |
| `configured_not_tested` | Key present, no test run yet |
| `provider_rejected_key` | Provider returned 401/403 |
| `model_invalid` | Key works but configured model is not valid |
| `endpoint_unreachable` | Network/timeout error reaching provider |
| `test_passed` | Test call succeeded |
| `fallback_available` | Key present (budget/fallback provider) |
| `MODEL_MAPPING_REQUIRED` | No model configured despite key being present |

## Endpoints

### GET /api/v1/settings/provider-resolution

Returns per-key truth for `GENX_API_KEY`, `FIRECRAWL_API_KEY`, `QWEN_API_KEY`,
`HUGGINGFACE_TOKEN`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `PIXABAY_API_KEY`.

Each entry includes:
- `key_name` — the key name
- `effective_source` — `user` | `env` | `missing`
- `masked_value` — last 4 chars visible
- `decrypt_ok` — true/false/null (null if env-sourced)
- `configured` — true/false
- `last_test_status` — `test_passed` | `test_failed` | null
- `last_test_error` — sanitized error string | null
- `last_test_at` — last test timestamp if available
- `next_action` — actionable next step

### GET /api/v1/settings/providers/debug

Detailed per-provider snapshot for dashboard diagnostics. Fields:

**GenX:**
- `key_saved`, `key_source`, `decrypt_ok`
- `model_mapping_present`, `effective_model`, `task_models`
- `base_url`, `last_test_status`, `last_test_at`, `last_test_error`
- `note` — actionable guidance

**Qwen:**
- `key_saved`, `key_source`, `decrypt_ok`
- `catalog_available`, `budget_engine_available`

**Firecrawl:**
- `key_saved`, `key_source`, `decrypt_ok`
- `last_test_status`, `last_test_at`, `last_test_error`

**HuggingFace:**
- `token_saved`, `token_source`, `decrypt_ok`
- `required: false`

**Pixabay:**
- `key_saved`, `key_source`, `decrypt_ok`
- `image_api_status`, `video_api_status`

## Provider Test Endpoints

| Provider | Endpoint | Method |
|----------|----------|--------|
| GenX (full) | `/settings/genx/debug-test` | POST |
| GenX models | `/settings/genx/models` | GET |
| GenX capabilities | `/settings/genx/capabilities` | GET |
| GenX capability test | `/settings/genx/test-capability` | POST |
| Qwen models | `/settings/qwen/models` | GET |
| Qwen capabilities | `/settings/qwen/capabilities` | GET |
| Qwen test | `/settings/qwen/test-capability` | POST |
| Firecrawl | `/settings/firecrawl/debug-test` | POST |
| HuggingFace | `/settings/huggingface/tasks` | GET |
| HuggingFace test | `/settings/huggingface/test-task` | POST |

## GenX Specifics

- **No hardcoded `genx-chat-pro`** — effective model resolved from `GENX_DEFAULT_MODEL`,
  then task models (`copy`, `strategy`, `analysis`), then fallback list
- **Model invalid vs key missing** — `model_invalid` state is separate from `missing_key`
- **Model catalog** tested separately from generation via `/settings/genx/models`
- **`MODEL_MAPPING_REQUIRED`** reported when key present but no model configured

## Qwen Specifics

- If `QWEN_API_KEY` exists: `budget_engine_available=true` even if specific models untested
- Full catalog available at `/settings/qwen/models` (43 models, 6 categories)
- Cheap text/capability route available via `/settings/qwen/test-capability`

## Firecrawl Specifics

- If key exists and scrape of `example.com` succeeds: `test_passed`
- Test endpoint: `POST /settings/firecrawl/debug-test`

## HuggingFace Specifics

- `HUGGINGFACE_TOKEN` is optional
- Missing token is `missing_token` state, not an error
- Required only if user wants HF fallback generation

## Dashboard Integrations — What to Show

| Condition | Display |
|-----------|---------|
| `effective_source=missing` | ⚠️ Key not configured |
| `decrypt_ok=false` | ❌ Key saved but cannot be decrypted |
| `last_test_status=test_passed` | ✅ Test passed |
| `last_test_status=test_failed` | ❌ Test failed — see error |
| `status=model_invalid` | ⚠️ Key valid, model invalid — set GENX_DEFAULT_MODEL |
| `status=fallback_available` | 🔄 Fallback available (Qwen/HF) |
| `configured=true`, not tested | 🔵 Configured — run test to verify |

## What Is Configured (Env)

Check `.env` or systemd service for:
- `GENX_API_KEY` + `GENX_BASE_URL` + `GENX_DEFAULT_MODEL`
- `FIRECRAWL_API_KEY`
- `QWEN_API_KEY` (optional — budget fallback)
- `HUGGINGFACE_TOKEN` (optional)

## What Requires External Provider Setup

- **GenX generation** — requires valid `GENX_API_KEY` and a model on `GENX_BASE_URL`
- **Firecrawl scraping** — requires valid `FIRECRAWL_API_KEY`
- **Social posting** — requires OAuth per platform (YouTube, TikTok, Meta, Twitter, LinkedIn, Pinterest, Reddit)
- **Qwen budget fallback** — requires `QWEN_API_KEY` with Alibaba Cloud access

## Smoke Script

```bash
MARKETING_TEST_EMAIL=... MARKETING_TEST_PASSWORD=... \
  bash scripts/test_provider_key_truth.sh
```

Fails only on:
- Server errors (5xx)
- Non-JSON 2xx response
- Contradiction: key exists but response says `missing_key` or `decrypt_failed`
- Does NOT fail for `MODEL_MAPPING_REQUIRED` — reports it as info
