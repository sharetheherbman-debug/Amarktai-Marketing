# Marketing Multimodal Autonomy Audit

## Providers and key truth

- GenX (`GENX_API_KEY`) — primary multimodal router; model validity required.
- Firecrawl (`FIRECRAWL_API_KEY`) — website scrape/analyze.
- Qwen (`QWEN_API_KEY`) — text/script fallback.
- Hugging Face (`HUGGINGFACE_TOKEN`) — task-based multimodal fallback.
- OpenAI (`OPENAI_API_KEY`) and Gemini (`GEMINI_API_KEY`) — optional.

## Multimodal outputs currently exposed

- Text/caption/body
- Image prompt
- Video script
- Shot list
- Voiceover script
- Avatar script
- Thumbnail prompt
- Carousel slides
- YouTube kit fields
- TikTok/Reels kit fields

Asset URLs are only returned when actually generated; otherwise status is `prompt_or_script_only`.

## Endpoints

- `/api/v1/content/generate`
- `/api/v1/content/generate-all`
- `/api/v1/content/generate-creative`
- `/api/v1/content/generate-pack`

## Remaining gap vs full autonomy

- Live media asset generation depends on configured provider tasks/models.
- Automatic posting remains blocked until OAuth scopes + worker runtime are verified.
