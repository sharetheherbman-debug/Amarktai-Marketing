# Marketing Provider Capability Matrix

| Provider | Key | Text/Copy | Strategy/Analysis | Image Prompt | Image Asset | Video Script | Avatar Script | Scrape | Status source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GenX | `GENX_API_KEY` | Yes | Yes | Yes | Model-dependent | Yes | Yes | No | `/api/v1/settings/readiness`, `/api/v1/settings/genx/models`, `/api/v1/settings/genx/capabilities` |
| Firecrawl | `FIRECRAWL_API_KEY` | No | No | No | No | No | No | Yes | `/api/v1/settings/readiness`, `/api/v1/settings/firecrawl/debug-test` |
| Qwen | `QWEN_API_KEY` | Yes (fallback) | Yes (fallback) | Yes (fallback) | No | Yes (fallback) | Yes (fallback) | No | `/api/v1/settings/readiness`, `/api/v1/settings/provider-resolution` |
| Hugging Face | `HUGGINGFACE_TOKEN` | Yes | Task-dependent | Yes | Yes | Task-dependent | Task-dependent | No | `/api/v1/settings/huggingface/tasks`, `/api/v1/settings/huggingface/test-task` |
| OpenAI | `OPENAI_API_KEY` | Optional fallback | Optional fallback | Optional | Optional | Optional | Optional | No | `/api/v1/settings/provider-resolution` |
| Gemini | `GEMINI_API_KEY` | Optional fallback | Optional fallback | Optional | Optional | Optional | Optional | No | `/api/v1/settings/provider-resolution` |

## Capability endpoint

- `/api/v1/capabilities` computes capability status from provider resolution/readiness and implemented services.
